import simpy
import networkx as nx
import matplotlib.pyplot as plt
import random
import ipaddress
import os

SIM_TIME = 100
PACKET_LOSS_RATE = 0.03
RIP_MAX_HOPS = 15
LOAD_DECAY_INTERVAL = 0.5
LOAD_DECAY_FACTOR = 0.85

LINK_BW = {
    "core": 10000,
    "dist": 3000,
    "access": 1000,
    "edge": 100,
}

class CampusNetwork:
    def __init__(self, env):
        self.env = env
        self.G = nx.Graph()

        self.delivered = 0
        self.lost = 0
        self.acl_blocked = 0
        self.congestion_drops = 0
        self.delay_log = []
        self.hop_log = []

        self.dhcp_pools = {}
        self.dhcp_leases = {}

        self.create_topology()

    def _add_profiled_link(self, a, b, bandwidth, delay_range):
        self.G.add_edge(
            a,
            b,
            bandwidth=bandwidth,
            base_delay=random.uniform(*delay_range),
            load=0.0,
        )

    def _pool_key(self, campus_id, vlan):
        return f"C{campus_id}_V{vlan}"

    def make_dhcp_pool(self, campus_id, vlan):
        third_octet = vlan % 256
        if third_octet == 0:
            third_octet = 1
        cidr = f"10.{campus_id}.{third_octet}.0/24"
        net = ipaddress.ip_network(cidr)
        return [str(ip) for ip in list(net.hosts())[20:]]

    def allocate_ip(self, campus_id, vlan, node_name):
        key = self._pool_key(campus_id, vlan)
        if key not in self.dhcp_pools:
            self.dhcp_pools[key] = self.make_dhcp_pool(campus_id, vlan)

        pool = self.dhcp_pools[key]
        if not pool:
            return "0.0.0.0"

        ip = pool.pop(0)
        self.dhcp_leases[node_name] = ip
        return ip

    def create_topology(self):
        # --- CORE ---
        self.G.add_node("CORE_ROUTER", layer=0)
        self.G.add_node("FIREWALL", layer=0)
        self.G.add_node("INTERNET", layer=0)

        self._add_profiled_link("CORE_ROUTER", "FIREWALL", LINK_BW["core"], (0.5, 1.2))
        self._add_profiled_link("FIREWALL", "INTERNET", LINK_BW["core"], (0.8, 1.5))

        # --- SERVERS ---
        servers = ["EXAM_SERVER", "EMAIL_SERVER", "CLOUD_SERVER"]
        for s in servers:
            self.G.add_node(s, layer=1, type="server", vlan=900)
            self._add_profiled_link("CORE_ROUTER", s, LINK_BW["dist"], (0.8, 1.6))

        # --- DISTRIBUTION ---
        campus_ids = {"MAIN": 10, "CAMPUS2": 20}
        for campus in ["MAIN", "CAMPUS2"]:
            campus_id = campus_ids[campus]
            dist = f"DIST_{campus}"
            self.G.add_node(dist, layer=1)
            self._add_profiled_link("CORE_ROUTER", dist, LINK_BW["core"], (0.6, 1.4))

            floors = 8 if campus == "MAIN" else 4

            # --- FLOORS ---
            for f in range(1, floors + 1):
                access = f"{campus}_F{f}_SW"
                floor_vlan = f if campus == "MAIN" else 100 + f
                wireless_vlan = 300 if campus == "MAIN" else 400

                self.G.add_node(access, layer=2, vlan=floor_vlan)
                self._add_profiled_link(dist, access, LINK_BW["dist"], (1.0, 2.0))

                # --- DEVICES PER FLOOR ---
                for i in range(1, 9):
                    pc = f"{access}_PC{i}"
                    self.G.add_node(
                        pc,
                        layer=3,
                        type="pc",
                        vlan=floor_vlan,
                        ip=self.allocate_ip(campus_id, floor_vlan, pc),
                    )
                    self._add_profiled_link(access, pc, LINK_BW["edge"], (1.0, 3.0))

                laptop = f"{access}_LAPTOP"
                phone = f"{access}_PHONE"
                printer = f"{access}_PRINTER"
                ap = f"{access}_AP"

                self.G.add_node(
                    laptop,
                    layer=3,
                    type="wireless",
                    vlan=wireless_vlan,
                    ip=self.allocate_ip(campus_id, wireless_vlan, laptop),
                )
                self.G.add_node(
                    phone,
                    layer=3,
                    type="wireless",
                    vlan=wireless_vlan,
                    ip=self.allocate_ip(campus_id, wireless_vlan, phone),
                )
                self.G.add_node(
                    printer,
                    layer=3,
                    type="printer",
                    vlan=floor_vlan,
                    ip=self.allocate_ip(campus_id, floor_vlan, printer),
                )
                self.G.add_node(ap, layer=2, vlan=wireless_vlan)

                self._add_profiled_link(access, printer, LINK_BW["edge"], (1.0, 2.8))
                self._add_profiled_link(access, ap, LINK_BW["access"], (0.8, 1.8))
                self._add_profiled_link(ap, laptop, LINK_BW["edge"], (1.2, 2.4))
                self._add_profiled_link(ap, phone, LINK_BW["edge"], (1.2, 2.4))

    # --- EXAM ACL BLOCK ---
    def exam_block_active(self, src, dest):
        if "PC" in src and dest == "INTERNET":
            return True
        return False

    # --- VLAN ISOLATION POLICY ---
    def vlan_isolation_block(self, src, dest):
        if dest not in self.G or src not in self.G:
            return False

        src_data = self.G.nodes[src]
        dest_data = self.G.nodes[dest]

        # Shared services are reachable across VLANs.
        if dest_data.get("type") == "server":
            return False

        src_vlan = src_data.get("vlan")
        dest_vlan = dest_data.get("vlan")
        if src_vlan is not None and dest_vlan is not None and src_vlan != dest_vlan:
            return True
        return False

    # --- LINK FAILURE ---
    def break_link(self):
        yield self.env.timeout(SIM_TIME / 2)
        print(f"\n[!] TIME {self.env.now}: CORE → MAIN DIST FAILURE\n")
        if self.G.has_edge("CORE_ROUTER", "DIST_MAIN"):
            self.G.remove_edge("CORE_ROUTER", "DIST_MAIN")

    # --- BACKGROUND LOAD DECAY ---
    def decay_link_load(self):
        while True:
            yield self.env.timeout(LOAD_DECAY_INTERVAL)
            for _, _, edge_data in self.G.edges(data=True):
                edge_data["load"] = edge_data.get("load", 0.0) * LOAD_DECAY_FACTOR

    # --- PACKET ---
    def send_packet(self, src, dest):
        try:
            if self.exam_block_active(src, dest):
                self.acl_blocked += 1
                return

            if self.vlan_isolation_block(src, dest):
                self.acl_blocked += 1
                return

            path = nx.shortest_path(self.G, src, dest)
            hops = len(path) - 1

            if hops > RIP_MAX_HOPS:
                self.lost += 1
                return

            delay = 0.0
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge = self.G[u][v]
                bandwidth = max(1.0, float(edge.get("bandwidth", LINK_BW["access"])))
                load = float(edge.get("load", 0.0))

                congestion = max(1.0, load / bandwidth)
                drop_prob = min(0.35, PACKET_LOSS_RATE * congestion)
                if random.random() < drop_prob:
                    self.lost += 1
                    self.congestion_drops += 1
                    return

                link_delay = edge.get("base_delay", 1.0) * congestion + random.uniform(0.2, 1.1)
                delay += link_delay

                edge["load"] = load + random.uniform(10, 35)

            yield self.env.timeout(0.1 + hops * 0.02)

            self.delay_log.append(delay)
            self.hop_log.append(hops)
            self.delivered += 1

            if self.delivered % 200 == 0:
                print(f"[{self.env.now:.1f}s] {src} → {dest} | hops={hops}")

        except nx.NetworkXNoPath:
            self.lost += 1

    # --- TRAFFIC ---
    def generate_traffic(self):
        hosts = [n for n, d in self.G.nodes(data=True) if d.get("type") in ["pc", "wireless"]]

        while True:
            yield self.env.timeout(random.uniform(0.01, 0.05))
            src = random.choice(hosts)
            flow_pick = random.random()

            if flow_pick < 0.65:
                dest = "EXAM_SERVER"
            elif flow_pick < 0.90:
                dest = random.choice([h for h in hosts if h != src])
            else:
                dest = "INTERNET"

            self.env.process(self.send_packet(src, dest))

# --- RUN ---
env = simpy.Environment()
net = CampusNetwork(env)

env.process(net.generate_traffic())
env.process(net.break_link())
env.process(net.decay_link_load())

print("Running campus simulation...\n")
env.run(until=SIM_TIME)

def _campus_summary(graph, prefix):
    hosts = [n for n in graph.nodes if n.startswith(prefix)]
    return {
        "access_switches": sum(1 for n in hosts if n.endswith("_SW")),
        "aps": sum(1 for n in hosts if n.endswith("_AP")),
        "pcs": sum(1 for n in hosts if "_PC" in n),
        "wireless": sum(1 for n in hosts if n.endswith("_LAPTOP") or n.endswith("_PHONE")),
        "printers": sum(1 for n in hosts if n.endswith("_PRINTER")),
    }


def export_compartmentalized_svg(graph, output_path="report/compartmentalized_topology.svg"):
    main = _campus_summary(graph, "MAIN_")
    campus2 = _campus_summary(graph, "CAMPUS2_")
    server_count = sum(1 for _, d in graph.nodes(data=True) if d.get("type") == "server")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    width, height = 1500, 980
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">',
        '    <stop offset="0%" stop-color="#f8fbff"/>',
        '    <stop offset="100%" stop-color="#eef3fa"/>',
        "  </linearGradient>",
        "</defs>",
        '  <rect x="0" y="0" width="100%" height="100%" fill="url(#bg)"/>',
    ]

    def add_text(x, y, text, size=16, weight="600", fill="#1f2937", anchor="middle"):
        svg.append(
            f'  <text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{text}</text>'
        )

    def add_compartment(x, y, w, h, title, color):
        svg.append(
            f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{color}" fill-opacity="0.2" '
            'stroke="#7b8794" stroke-width="1.2" stroke-dasharray="6 6"/>'
        )
        add_text(x + 16, y + 28, title, size=17, weight="700", fill="#334155", anchor="start")

    def add_symbol_node(x, y, title, line1, line2, color, shape="circle"):
        if shape == "diamond":
            points = f"{x},{y-42} {x+42},{y} {x},{y+42} {x-42},{y}"
            svg.append(f'  <polygon points="{points}" fill="{color}" stroke="#0f172a" stroke-width="1.2"/>')
        elif shape == "square":
            svg.append(
                f'  <rect x="{x-42}" y="{y-42}" width="84" height="84" rx="14" fill="{color}" '
                'stroke="#0f172a" stroke-width="1.2"/>'
            )
        else:
            svg.append(f'  <circle cx="{x}" cy="{y}" r="42" fill="{color}" stroke="#0f172a" stroke-width="1.2"/>')

        add_text(x, y + 4, title, size=14, weight="700", fill="#0f172a")
        add_text(x, y + 66, line1, size=13, weight="600", fill="#1f2937")
        add_text(x, y + 84, line2, size=13, weight="500", fill="#475569")

    def add_edge(x1, y1, x2, y2):
        svg.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#6b7280" stroke-width="2"/>')

    add_compartment(40, 40, 1420, 165, "External + Security", "#ffd8cc")
    add_compartment(40, 225, 1420, 210, "Core + Services", "#d1fae5")
    add_compartment(40, 455, 1420, 165, "Distribution", "#dbeafe")
    add_compartment(40, 640, 1420, 300, "Campus Access + Endpoints (Symbolic Aggregates)", "#ede9fe")

    internet = (750, 115)
    firewall = (630, 315)
    core = (870, 315)
    servers = (1110, 315)
    dist_main = (520, 535)
    dist_c2 = (980, 535)
    main_access = (420, 760)
    main_end = (620, 760)
    c2_access = (880, 760)
    c2_end = (1080, 760)

    add_edge(*internet, *firewall)
    add_edge(*firewall, *core)
    add_edge(*core, *servers)
    add_edge(*core, *dist_main)
    add_edge(*core, *dist_c2)
    add_edge(*dist_main, *main_access)
    add_edge(*main_access, *main_end)
    add_edge(*dist_c2, *c2_access)
    add_edge(*c2_access, *c2_end)

    add_symbol_node(*internet, "NET", "Internet", "external uplink", "#fb7185", shape="circle")
    add_symbol_node(*firewall, "FW", "Firewall", "policy and ACL", "#f97316", shape="diamond")
    add_symbol_node(*core, "CR", "Core Router", "backbone switch", "#38bdf8", shape="circle")
    add_symbol_node(*servers, "SVR", f"Services: {server_count}", "exam, email, cloud", "#22c55e", shape="square")

    add_symbol_node(*dist_main, "D1", "DIST_MAIN", "aggregation point", "#3b82f6", shape="circle")
    add_symbol_node(*dist_c2, "D2", "DIST_CAMPUS2", "aggregation point", "#2563eb", shape="circle")

    add_symbol_node(
        *main_access,
        "A-M",
        f"Main Access: {main['access_switches']}",
        f"APs: {main['aps']}",
        "#8b5cf6",
        shape="square",
    )
    add_symbol_node(
        *main_end,
        "E-M",
        f"PCs:{main['pcs']}  Wireless:{main['wireless']}",
        f"Printers:{main['printers']}",
        "#a78bfa",
        shape="circle",
    )
    add_symbol_node(
        *c2_access,
        "A-C2",
        f"Campus2 Access: {campus2['access_switches']}",
        f"APs: {campus2['aps']}",
        "#7c3aed",
        shape="square",
    )
    add_symbol_node(
        *c2_end,
        "E-C2",
        f"PCs:{campus2['pcs']}  Wireless:{campus2['wireless']}",
        f"Printers:{campus2['printers']}",
        "#c4b5fd",
        shape="circle",
    )

    add_text(750, 30, "Campus Network - Compartmentalized Symbolic Topology", size=24, weight="700", fill="#0f172a")
    svg.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

    return output_path


svg_path = export_compartmentalized_svg(net.G)
print(f"\nSymbolic topology SVG saved to: {svg_path}")

# --- VISUALIZATION DASHBOARD ---
fig = plt.figure(figsize=(15, 4.8))

# 2. DELIVERY VS LOSS
ax1 = plt.subplot2grid((2, 3), (1, 0))
ax1.bar(
    ["Delivered", "Lost", "ACL Blocked"],
    [net.delivered, net.lost, net.acl_blocked],
    color=["#1E88E5", "#E53935", "#8E24AA"],
)
ax1.set_title("Packet Delivery Status")
ax1.set_ylabel("Packet Count")

# 3. HOP COUNT DISTRIBUTION
ax2 = plt.subplot2grid((2, 3), (1, 1))
if net.hop_log:
    max_hops = max(net.hop_log)
    ax2.hist(
        net.hop_log,
        bins=range(1, max_hops + 2),
        align="left",
        rwidth=0.75,
        color="#2E7D32",
    )
ax2.set_title("Hop Count Distribution (RIP Metric)")
ax2.set_xlabel("Number of Hops")
ax2.set_ylabel("Frequency")

# 4. DELAY DISTRIBUTION
ax3 = plt.subplot2grid((2, 3), (1, 2))
if net.delay_log:
    ax3.hist(net.delay_log, bins=12, color="#F9A825", edgecolor="black")
ax3.set_title("End-to-End Delay")
ax3.set_xlabel("Delay (ms)")
ax3.set_ylabel("Frequency")

plt.tight_layout()
plt.show()

# --- STATS ---
print("\n===== RESULTS =====")
print("Delivered:", net.delivered)
print("Lost:", net.lost)
print("ACL Blocked:", net.acl_blocked)
print("Congestion Drops:", net.congestion_drops)
print("DHCP Leases:", len(net.dhcp_leases))