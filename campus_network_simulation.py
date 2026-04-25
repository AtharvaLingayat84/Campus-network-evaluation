"""
=============================================================================
  Multi-Campus Network Simulation
  ─────────────────────────────────
  Models a realistic Cisco Packet Tracer topology with:
    - ISR4331 Router, ASA Firewall, Core Router, Core Switch
    - Distribution and Floor switches per campus
    - 8-floor Main Campus (VLANs 101-108) and 4-floor Campus 2 (VLANs 201-204)
    - Per-floor devices: 8 PCs, 1 Printer, 1 AP, 1 Laptop, 1 Smartphone
    - Servers (Exam, Email, Cloud) on VLAN 128
    - VLAN segmentation, router-on-a-stick, DHCP, wireless bridging
    - ACL-based exam mode (restrict traffic to Exam + Email only)

  Libraries:
    - NetworkX  : topology graph (nodes + edges with attributes)
    - SimPy     : discrete-event packet flow simulation
    - Matplotlib: topology visualization with color-coded device types
    - Logging   : timestamped network event log

  Usage:
    python campus_network_simulation.py
=============================================================================
"""

import simpy
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import random
import ipaddress
import math
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

# =========================================================================
#  LOGGING CONFIGURATION
# =========================================================================
LOG_FILE = "network_simulation.log"

logger = logging.getLogger("CampusNet")
logger.setLevel(logging.DEBUG)

# File handler - full debug trace
_fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(message)s"))

# Console handler - info and above
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(message)s"))

logger.addHandler(_fh)
logger.addHandler(_ch)

# =========================================================================
#  SIMULATION PARAMETERS
# =========================================================================
SIM_TIME          = 60          # seconds of SimPy time to run
PACKET_LOSS_RATE  = 0.02        # baseline per-link loss probability
MAX_TTL           = 64          # IP TTL / hop limit

# Link bandwidth tiers (Mbps)
LINK_BW = {
    "wan":        10000,   # Internet uplink
    "core":        8000,   # core infrastructure
    "distribution": 4000,  # distribution layer
    "access":      1000,   # floor switches
    "end_device":   100,   # PCs, printers, wireless
}

# =========================================================================
#  DATA CLASSES
# =========================================================================
@dataclass
class Packet:
    """Represents an IP packet traversing the network."""
    src_name: str
    src_ip:   str
    dst_name: str
    dst_ip:   str
    vlan:     int
    protocol: str = "TCP"
    ttl:      int = MAX_TTL
    size:     int = 1500       # bytes

    def __repr__(self):
        return (f"Packet({self.src_ip} -> {self.dst_ip} "
                f"[VLAN {self.vlan}] TTL={self.ttl})")


# =========================================================================
#  NETWORK CLASS
# =========================================================================
class CampusNetwork:
    """
    Builds and manages the full multi-campus topology.
    Handles DHCP, ACL policies, and packet forwarding.
    """

    # --- campus layout config ---
    CAMPUSES = {
        "MAIN": {
            "id":         1,
            "num_floors": 8,
            "vlans":      list(range(101, 109)),    # 101-108
        },
        "CAMPUS2": {
            "id":         2,
            "num_floors": 4,
            "vlans":      list(range(201, 205)),    # 201-204
        },
    }

    SERVER_VLAN  = 128
    SERVERS_INFO = {
        "EXAM_SERVER":   {"ip": "10.128.0.10", "role": "exam"},
        "EMAIL_SERVER":  {"ip": "10.128.0.20", "role": "email"},
        "CLOUD_SERVER":  {"ip": "10.128.0.30", "role": "cloud"},
    }

    # ACL exam-mode allowed destination IPs
    EXAM_ALLOWED_IPS = {
        "10.128.0.10",   # Exam Server
        "10.128.0.20",   # Email Server
    }

    # --- constructor ---
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.G   = nx.Graph()

        # DHCP state
        self.dhcp_pools:  dict[str, list[str]] = {}
        self.dhcp_leases: dict[str, str]       = {}

        # ACL mode
        self.exam_mode: bool = False

        # Statistics
        self.stats = {
            "delivered":      0,
            "dropped_ttl":    0,
            "dropped_loss":   0,
            "acl_blocked":    0,
            "dhcp_assigned":  0,
            "packets_sent":   0,
        }
        self.delay_log: list[float] = []
        self.hop_log:   list[int]   = []

        self._build_topology()

    # ================================================================
    #  TOPOLOGY BUILDER
    # ================================================================
    def _add_node(self, name: str, **attrs):
        """Add a node with default attributes."""
        defaults = {
            "type":    "unknown",
            "vlan":    None,
            "ip":      None,
            "campus":  None,
            "floor":   None,
        }
        defaults.update(attrs)
        self.G.add_node(name, **defaults)

    def _add_link(self, a: str, b: str, tier: str = "access"):
        """Add a weighted link with realistic delay."""
        bw = LINK_BW.get(tier, LINK_BW["access"])
        self.G.add_edge(
            a, b,
            bandwidth=bw,
            base_delay=random.uniform(0.3, 1.5),
            load=0.0,
            tier=tier,
        )

    def _make_dhcp_pool(self, subnet_cidr: str) -> list[str]:
        """Return usable host IPs from a /24 subnet (skip first 20)."""
        net = ipaddress.ip_network(subnet_cidr)
        hosts = list(net.hosts())
        # Reserve .1 for gateway, .2-.19 for infrastructure, .20+ for DHCP
        return [str(ip) for ip in hosts[20:]]

    def _allocate_ip(self, vlan: int, node_name: str) -> str:
        """Assign an IP from the DHCP pool for the given VLAN."""
        pool_key = f"VLAN{vlan}"
        if pool_key not in self.dhcp_pools:
            # Generate subnet: 10.{campus_id}.{vlan_last_octet}.0/24
            # For server VLAN 128: 10.128.0.0/24
            if vlan == self.SERVER_VLAN:
                cidr = "10.128.0.0/24"
            else:
                campus_id = vlan // 100
                cidr = f"10.{campus_id}.{vlan}.0/24"
            self.dhcp_pools[pool_key] = self._make_dhcp_pool(cidr)

        pool = self.dhcp_pools[pool_key]
        if not pool:
            logger.warning(f"DHCP pool exhausted for VLAN {vlan}")
            return "0.0.0.0"

        ip = pool.pop(0)
        self.dhcp_leases[node_name] = ip
        self.stats["dhcp_assigned"] += 1
        logger.debug(f"DHCP: {node_name} -> {ip} (VLAN {vlan})")
        return ip

    def _build_topology(self):
        """Construct the full network graph."""

        logger.info("=" * 60)
        logger.info("  BUILDING NETWORK TOPOLOGY")
        logger.info("=" * 60)

        # --- INTERNET ---
        self._add_node("INTERNET", type="internet")
        logger.debug("Node: INTERNET (external)")

        # --- ISR4331 ROUTER (edge) ---
        self._add_node("ISR4331", type="router", role="edge_router")
        self._add_link("INTERNET", "ISR4331", tier="wan")
        logger.debug("Node: ISR4331 (edge router)")

        # --- ASA FIREWALL ---
        self._add_node("ASA_FW", type="firewall", role="firewall")
        self._add_link("ISR4331", "ASA_FW", tier="core")
        logger.debug("Node: ASA_FW (ASA firewall)")

        # --- CORE ROUTER (router-on-a-stick) ---
        self._add_node("CORE_RTR", type="router", role="core_router")
        self._add_link("ASA_FW", "CORE_RTR", tier="core")
        logger.debug("Node: CORE_RTR (core router - router-on-a-stick)")

        # --- CORE SWITCH (L3) ---
        self._add_node("CORE_SW", type="switch", role="core_switch")
        self._add_link("CORE_RTR", "CORE_SW", tier="core")
        logger.debug("Node: CORE_SW (core L3 switch)")

        # --- SERVERS (VLAN 128) ---
        for srv_name, srv_info in self.SERVERS_INFO.items():
            ip = srv_info["ip"]
            self._add_node(srv_name, type="server",
                           vlan=self.SERVER_VLAN, ip=ip,
                           server_role=srv_info["role"])
            self._add_link("CORE_SW", srv_name, tier="distribution")
            logger.debug(f"Node: {srv_name}  IP: {ip}  VLAN: {self.SERVER_VLAN}")

        # --- PER-CAMPUS BUILD-OUT ---
        for campus_name, campus_cfg in self.CAMPUSES.items():
            cid        = campus_cfg["id"]
            num_floors = campus_cfg["num_floors"]
            vlans      = campus_cfg["vlans"]

            # Distribution switch
            dist_name = f"DSW_{campus_name}"
            self._add_node(dist_name, type="switch",
                           role="distribution", campus=campus_name)
            self._add_link("CORE_SW", dist_name, tier="core")
            logger.debug(f"Node: {dist_name} (distribution switch)")

            for floor_idx in range(num_floors):
                floor_num  = floor_idx + 1
                vlan       = vlans[floor_idx]
                floor_sw   = f"FSW_{campus_name}_F{floor_num}"

                # Floor access switch
                self._add_node(floor_sw, type="switch",
                               role="access", vlan=vlan,
                               campus=campus_name, floor=floor_num)
                self._add_link(dist_name, floor_sw, tier="distribution")
                logger.debug(f"  Floor switch: {floor_sw}  VLAN: {vlan}")

                # --- 8 PCs ---
                for pc_num in range(1, 9):
                    pc_name = f"PC_{campus_name}_F{floor_num}_{pc_num}"
                    ip = self._allocate_ip(vlan, pc_name)
                    self._add_node(pc_name, type="pc",
                                   vlan=vlan, ip=ip,
                                   campus=campus_name, floor=floor_num)
                    self._add_link(floor_sw, pc_name, tier="end_device")

                # --- Printer ---
                prt_name = f"PRT_{campus_name}_F{floor_num}"
                ip = self._allocate_ip(vlan, prt_name)
                self._add_node(prt_name, type="printer",
                               vlan=vlan, ip=ip,
                               campus=campus_name, floor=floor_num)
                self._add_link(floor_sw, prt_name, tier="end_device")

                # --- Access Point ---
                ap_name = f"AP_{campus_name}_F{floor_num}"
                self._add_node(ap_name, type="access_point",
                               vlan=vlan,
                               campus=campus_name, floor=floor_num)
                self._add_link(floor_sw, ap_name, tier="access")

                # --- Wireless devices (Laptop + Smartphone) ---
                laptop_name = f"LAPTOP_{campus_name}_F{floor_num}"
                ip = self._allocate_ip(vlan, laptop_name)
                self._add_node(laptop_name, type="wireless",
                               vlan=vlan, ip=ip,
                               campus=campus_name, floor=floor_num,
                               wireless_device="laptop")
                self._add_link(ap_name, laptop_name, tier="end_device")

                phone_name = f"PHONE_{campus_name}_F{floor_num}"
                ip = self._allocate_ip(vlan, phone_name)
                self._add_node(phone_name, type="wireless",
                               vlan=vlan, ip=ip,
                               campus=campus_name, floor=floor_num,
                               wireless_device="smartphone")
                self._add_link(ap_name, phone_name, tier="end_device")

        # --- Summary ---
        n_nodes = self.G.number_of_nodes()
        n_edges = self.G.number_of_edges()
        n_pcs   = sum(1 for _, d in self.G.nodes(data=True) if d["type"] == "pc")
        n_wire  = sum(1 for _, d in self.G.nodes(data=True) if d["type"] == "wireless")
        logger.info(f"  TOPOLOGY COMPLETE: {n_nodes} nodes, {n_edges} edges")
        logger.info(f"  PCs: {n_pcs}  Wireless: {n_wire}  "
                     f"DHCP leases: {self.stats['dhcp_assigned']}")
        logger.info("=" * 60)

    # ================================================================
    #  DHCP HELPER (post-build queries)
    # ================================================================
    def get_ip(self, node_name: str) -> Optional[str]:
        """Return the IP address assigned to a node."""
        if node_name == "INTERNET":
            return "8.8.8.8"
        if node_name in self.G.nodes:
            return self.G.nodes[node_name].get("ip")
        return None

    # ================================================================
    #  ACL / EXAM MODE
    # ================================================================
    def set_exam_mode(self, enabled: bool):
        """Toggle exam-mode ACL restrictions."""
        self.exam_mode = enabled
        state = "ENABLED" if enabled else "DISABLED"
        logger.info(f"{'='*60}")
        logger.info(f"  EXAM MODE {state}")
        if enabled:
            logger.info(f"  Allowed destinations: {self.EXAM_ALLOWED_IPS}")
            logger.info(f"  All other external/server traffic BLOCKED")
        logger.info(f"{'='*60}")

    def _acl_check(self, pkt: Packet) -> tuple[bool, str]:
        """
        Returns (allowed, reason) for ACL evaluation.

        Exam mode policy:
          - Client-to-client traffic within same VLAN: ALLOWED
          - Traffic to Exam Server or Email Server: ALLOWED
          - Traffic to Cloud Server, Internet, anything else: DENIED
        """
        if not self.exam_mode:
            return True, "normal-mode"

        dst_ip = pkt.dst_ip

        # Always allow same-VLAN intra-floor traffic (printers, etc.)
        src_vlan = self.G.nodes[pkt.src_name].get("vlan")
        dst_vlan = self.G.nodes[pkt.dst_name].get("vlan")
        if src_vlan is not None and dst_vlan is not None and src_vlan == dst_vlan:
            return True, "same-vlan"

        # Allow Exam and Email servers
        if dst_ip in self.EXAM_ALLOWED_IPS:
            return True, "exam-or-email-server"

        # Block everything else (Cloud Server, Internet, cross-VLAN)
        return False, "blocked-by-exam-acl"

    # ================================================================
    #  PACKET FORWARDING SIMULATION
    # ================================================================
    def _find_path(self, src: str, dst: str) -> Optional[list[str]]:
        """Shortest-path route lookup."""
        try:
            return nx.shortest_path(self.G, src, dst)
        except nx.NetworkXNoPath:
            return None

    def _decay_edge_load(self, edge: dict) -> None:
        """Decay edge load over simulated time to prevent buildup."""
        now = float(self.env.now)
        last = float(edge.get("last_decay_time", now))
        dt = max(0.0, now - last)

        if dt > 0:
            decay_rate = 0.15
            edge["load"] = float(edge.get("load", 0.0)) * math.exp(-decay_rate * dt)

        edge["last_decay_time"] = now

    def _build_routed_path(self, src_name: str, dst_name: str) -> Optional[list[str]]:
        """Compute a path that enforces VLAN routing rules."""
        if src_name == dst_name:
            return [src_name]

        src_vlan = self.G.nodes[src_name].get("vlan")
        dst_vlan = self.G.nodes[dst_name].get("vlan")

        # Infrastructure nodes or same-VLAN traffic use the shortest path.
        if src_vlan is None or dst_vlan is None or src_vlan == dst_vlan:
            return self._find_path(src_name, dst_name)

        # Cross-VLAN traffic must traverse CORE_RTR.
        if "CORE_RTR" not in self.G:
            return None

        path_to_router = self._find_path(src_name, "CORE_RTR")
        path_from_router = self._find_path("CORE_RTR", dst_name)
        if not path_to_router or not path_from_router:
            return None

        # Avoid duplicating CORE_RTR in the stitched path.
        return path_to_router[:-1] + path_from_router

    def _route_through_router(self, pkt: Packet) -> bool:
        """
        Simulates router-on-a-stick inter-VLAN routing.
        If source and destination are on different VLANs,
        the packet must traverse the CORE_RTR.
        """
        src_vlan = self.G.nodes[pkt.src_name].get("vlan")
        dst_vlan = self.G.nodes[pkt.dst_name].get("vlan")
        if src_vlan is None or dst_vlan is None:
            return True  # infrastructure nodes
        if src_vlan != dst_vlan:
            path_to_router = self._find_path(pkt.src_name, "CORE_RTR")
            path_from_router = self._find_path("CORE_RTR", pkt.dst_name)
            if path_to_router and path_from_router:
                logger.debug(f"  Router-on-a-stick: VLAN {src_vlan} -> VLAN {dst_vlan} via CORE_RTR")
                return True
            logger.warning(f"VLAN ISOLATION: blocked cross-VLAN route {pkt.src_name}({src_vlan}) -> {pkt.dst_name}({dst_vlan})")
            return False
        return True

    def simulate_packet_flow(self, src_name: str, dst_name: str):
        """
        End-to-end packet flow simulation as a SimPy process.

        Steps:
          1. Source creates packet
          2. ACL check (exam mode)
          3. Path computation
          4. Hop-by-hop forwarding with delay + loss
          5. Delivery or drop
        """
        self.stats["packets_sent"] += 1

        src_ip = self.get_ip(src_name)
        dst_ip = self.get_ip(dst_name)
        if not src_ip or not dst_ip:
            return

        src_vlan = self.G.nodes[src_name].get("vlan", 0)

        pkt = Packet(
            src_name=src_name, src_ip=src_ip,
            dst_name=dst_name, dst_ip=dst_ip,
            vlan=src_vlan,
        )

        logger.debug(f"{src_name} -> {dst_name}  sending packet {pkt}")

        # --- ACL check ---
        allowed, acl_reason = self._acl_check(pkt)
        if not allowed:
            self.stats["acl_blocked"] += 1
            logger.warning(f"ACL BLOCKED: {src_name}({src_ip}) -> {dst_name}({dst_ip}) reason={acl_reason}")
            return
        logger.debug(f"ACL: ALLOWED  {src_ip} -> {dst_ip} reason={acl_reason}")

        # --- Path computation ---
        path = self._build_routed_path(src_name, dst_name)
        if path is None:
            self.stats["dropped_ttl"] += 1
            logger.warning(f"ROUTE: No valid path  {src_name} -> {dst_name}")
            return

        hops = len(path) - 1
        if hops > MAX_TTL:
            self.stats["dropped_ttl"] += 1
            logger.warning(f"TTL EXCEEDED  {src_name} -> {dst_name}  hops={hops}")
            return

        # --- Hop-by-hop forwarding ---
        total_delay = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self.G[u][v]

            # Decay congestion before applying new traffic.
            self._decay_edge_load(edge)

            pkt.ttl -= 1
            if pkt.ttl <= 0:
                self.stats["dropped_ttl"] += 1
                logger.debug(f"TTL EXCEEDED at hop {i+1}  {u} -> {v}")
                return

            # Congestion factor
            bw   = max(1.0, float(edge.get("bandwidth", 100)))
            load = float(edge.get("load", 0.0))
            congestion = max(1.0, 1.0 + (load / bw))

            # Random loss
            drop_prob = min(0.30, PACKET_LOSS_RATE * congestion)
            if random.random() < drop_prob:
                self.stats["dropped_loss"] += 1
                logger.debug(f"PACKET LOSS at {u} -> {v}  (congestion={congestion:.2f})")
                return

            # Delay calculation
            link_delay = edge.get("base_delay", 1.0) * congestion
            link_delay += random.uniform(0.1, 0.5)

            # Firewall adds processing delay without topology changes.
            if u == "ASA_FW" or v == "ASA_FW":
                firewall_delay = random.uniform(1.0, 3.0)
                link_delay += firewall_delay
                logger.debug(f"  ASA processing delay added: {firewall_delay:.2f}ms")

            total_delay += link_delay

            # Update load
            edge["load"] = min(load + random.uniform(5, 20), bw * 10)
            edge["last_decay_time"] = float(self.env.now)

            # Log forwarding
            node_type = self.G.nodes[v].get("type", "unknown")
            logger.debug(f"  FWD hop {i+1}: {u} -> {v}  "
                         f"type={node_type}  delay={link_delay:.2f}ms")

            # SimPy delay
            yield self.env.timeout(link_delay / 1000.0)  # ms -> sim-seconds

        # --- Delivery ---
        self.stats["delivered"] += 1
        self.delay_log.append(total_delay)
        self.hop_log.append(hops)

        if self.stats["delivered"] % 50 == 0:
            logger.debug(f"DELIVERED #{self.stats['delivered']}:  "
                         f"{src_name} -> {dst_name}  "
                         f"hops={hops}  delay={total_delay:.2f}ms")

    # ================================================================
    #  TRAFFIC GENERATOR
    # ================================================================
    def generate_traffic(self, duration: float = SIM_TIME):
        """
        SimPy process: continuously generates random traffic
        between end devices and servers.
        """
        # Collect all client devices and servers
        clients = [
            n for n, d in self.G.nodes(data=True)
            if d["type"] in ("pc", "wireless")
        ]
        servers = list(self.SERVERS_INFO.keys())

        logger.debug(f"Traffic generator started: {len(clients)} clients, "
                     f"{len(servers)} servers")

        while True:
            yield self.env.timeout(random.uniform(0.05, 0.2))

            src = random.choice(clients)

            # Traffic pattern:
            #   40% -> Exam Server
            #   20% -> Email Server
            #   10% -> Cloud Server
            #   10% -> Internet
            #   20% -> another client
            roll = random.random()
            if roll < 0.40:
                dst = "EXAM_SERVER"
            elif roll < 0.60:
                dst = "EMAIL_SERVER"
            elif roll < 0.70:
                dst = "CLOUD_SERVER"
            elif roll < 0.80:
                dst = "INTERNET"
            else:
                dst = random.choice([c for c in clients if c != src])

            self.env.process(self.simulate_packet_flow(src, dst))


# =========================================================================
#  VISUALIZATION
# =========================================================================

# Color map for device types
DEVICE_COLORS = {
    "internet":      "#E53935",   # red
    "router":        "#D32F2F",   # dark red
    "firewall":      "#FF9800",   # orange
    "switch":        "#1E88E5",   # blue
    "server":        "#8E24AA",   # purple
    "pc":            "#43A047",   # green
    "printer":       "#795548",   # brown
    "access_point":  "#00ACC1",   # cyan
    "wireless":      "#00BCD4",   # light cyan
    "unknown":       "#9E9E9E",   # grey
}

DEVICE_SHAPES = {
    "internet":      "H",     # hexagon
    "router":        "s",     # square
    "firewall":      "D",     # diamond
    "switch":        "p",     # pentagon
    "server":        "8",     # octagon
    "pc":            "o",     # circle
    "printer":       "v",     # triangle-down
    "access_point":  "^",     # triangle-up
    "wireless":      "*",     # star
}


def visualize_stats(network: CampusNetwork,
                    title_suffix: str = "",
                    save_path: str = "simulation_stats.png"):
    """
    Draw a dashboard of simulation statistics:
      - Delivery / Loss / ACL Blocked bar chart
      - Hop count histogram
      - End-to-end delay histogram
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    s = network.stats

    # --- Delivery breakdown ---
    labels = ["Delivered", "Link Loss", "TTL Drop", "ACL Blocked"]
    values = [s["delivered"], s["dropped_loss"], s["dropped_ttl"], s["acl_blocked"]]
    colors = ["#43A047", "#E53935", "#FF9800", "#8E24AA"]
    axes[0].bar(labels, values, color=colors, edgecolor="white")
    axes[0].set_title(f"Packet Outcomes {title_suffix}", fontweight="bold")
    axes[0].set_ylabel("Packet Count")
    for i, v in enumerate(values):
        axes[0].text(i, v + max(values) * 0.02, str(v),
                     ha="center", fontweight="bold", fontsize=10)

    # --- Hop count distribution ---
    if network.hop_log:
        max_h = max(network.hop_log)
        axes[1].hist(network.hop_log,
                     bins=range(1, max_h + 2),
                     align="left", rwidth=0.8,
                     color="#1E88E5", edgecolor="white")
    axes[1].set_title(f"Hop Count Distribution {title_suffix}", fontweight="bold")
    axes[1].set_xlabel("Number of Hops")
    axes[1].set_ylabel("Frequency")

    # --- Delay distribution ---
    if network.delay_log:
        axes[2].hist(network.delay_log, bins=15,
                     color="#FFB300", edgecolor="black", alpha=0.85)
    axes[2].set_title(f"End-to-End Delay {title_suffix}", fontweight="bold")
    axes[2].set_xlabel("Delay (ms)")
    axes[2].set_ylabel("Frequency")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    logger.info(f"Stats dashboard saved to: {save_path}")
    plt.close(fig)

    return save_path


# =========================================================================
#  SIMULATION RUNNERS
# =========================================================================
def run_simulation(mode: str = "normal", sim_time: float = SIM_TIME) -> CampusNetwork:
    """
    Run a full simulation in either 'normal' or 'exam' mode.
    Returns the CampusNetwork instance with results.
    """
    logger.info(f"  SIMULATION START - MODE: {mode.upper()}")
    logger.info("=" * 60)

    env = simpy.Environment()
    net = CampusNetwork(env)

    # Set ACL mode
    net.set_exam_mode(mode == "exam")

    # Start traffic generation
    env.process(net.generate_traffic(duration=sim_time))

    # Run
    env.run(until=sim_time)

    # Print summary
    logger.info(f"  RESULTS - {mode.upper()} MODE")
    logger.info("-" * 60)
    logger.info(f"  Total packets sent:    {net.stats['packets_sent']}")
    logger.info(f"  Delivered:             {net.stats['delivered']}")
    logger.info(f"  Dropped (link loss):   {net.stats['dropped_loss']}")
    logger.info(f"  Dropped (TTL/no path): {net.stats['dropped_ttl']}")
    logger.info(f"  ACL blocked:           {net.stats['acl_blocked']}")
    logger.info(f"  DHCP leases:           {net.stats['dhcp_assigned']}")
    if net.delay_log:
        avg_d = sum(net.delay_log) / len(net.delay_log)
        logger.info(f"  Avg delay:             {avg_d:.2f} ms")
    if net.hop_log:
        avg_h = sum(net.hop_log) / len(net.hop_log)
        logger.info(f"  Avg hops:              {avg_h:.1f}")
    logger.info("-" * 60)

    return net


# =========================================================================
#  MAIN
# =========================================================================
def main():
    """Run both normal and exam-mode simulations, then compare."""

    logger.info("Multi-Campus Network Simulation")
    logger.info("Libraries: NetworkX + SimPy + Matplotlib")
    logger.info("")

    # --- Run 1: Normal Mode ---
    net_normal = run_simulation(mode="normal", sim_time=SIM_TIME)

    visualize_stats(net_normal,
                    title_suffix="(Normal Mode)",
                    save_path="stats_normal.png")

    # --- Run 2: Exam Mode ---
    net_exam = run_simulation(mode="exam", sim_time=SIM_TIME)

    visualize_stats(net_exam,
                    title_suffix="(Exam Mode)",
                    save_path="stats_exam.png")

    # --- Comparison ---
    logger.info("  COMPARISON: NORMAL vs EXAM MODE")
    logger.info("=" * 60)
    logger.info(f"  {'Metric':<25} {'Normal':>10} {'Exam':>10}")
    logger.info(f"  {'-'*25} {'-'*10} {'-'*10}")
    logger.info(f"  {'Packets sent':<25} {net_normal.stats['packets_sent']:>10} "
                f"{net_exam.stats['packets_sent']:>10}")
    logger.info(f"  {'Delivered':<25} {net_normal.stats['delivered']:>10} "
                f"{net_exam.stats['delivered']:>10}")
    logger.info(f"  {'ACL blocked':<25} {net_normal.stats['acl_blocked']:>10} "
                f"{net_exam.stats['acl_blocked']:>10}")
    logger.info(f"  {'Link loss':<25} {net_normal.stats['dropped_loss']:>10} "
                f"{net_exam.stats['dropped_loss']:>10}")
    logger.info(f"  {'TTL drops':<25} {net_normal.stats['dropped_ttl']:>10} "
                f"{net_exam.stats['dropped_ttl']:>10}")
    if net_normal.delay_log and net_exam.delay_log:
        avg_n = sum(net_normal.delay_log) / len(net_normal.delay_log)
        avg_e = sum(net_exam.delay_log) / len(net_exam.delay_log)
        logger.info(f"  {'Avg delay (ms)':<25} {avg_n:>10.2f} {avg_e:>10.2f}")
    logger.info("=" * 60)

    logger.info(f"Full log written to: {LOG_FILE}")
    logger.info("Generated images: stats_normal.png, stats_exam.png")
    logger.info("Simulation complete.")


if __name__ == "__main__":
    main()
