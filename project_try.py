import networkx as nx
import matplotlib.pyplot as plt
import ipaddress
import random

# -----------------------------
# CONFIG
# -----------------------------
FLOORS = 8
TTL_INIT = 16
PACKETS = 300

CAPACITY = {
    "core_dist": 10000,
    "dist_access": 1000,
    "access_pc": 100
}

ROLE_OCTET = {
    "CLASS": 10,
    "LAB": 20,
    "FAC": 30
}

# -----------------------------
# GRAPH INIT
# -----------------------------
G = nx.Graph()
G.add_node("CORE", type="core", layer="core")

# -----------------------------
# DHCP POOL FUNCTION
# -----------------------------
def make_dhcp_pool(cidr):
    net = ipaddress.ip_network(cidr)
    return list(net.hosts())[10:]

dhcp_pools = {}

# -----------------------------
# BUILD TOPOLOGY
# -----------------------------
for floor in range(1, FLOORS + 1):

    dist = f"DIST_F{floor}"
    G.add_node(dist, type="distribution", floor=floor)
    G.add_edge("CORE", dist, bandwidth=CAPACITY["core_dist"])

    vlans = {
        "CLASS": floor * 100 + 1,
        "LAB": floor * 100 + 2,
        "FAC": floor * 100 + 3
    }

    for role, vlan in vlans.items():

        access = f"F{floor}_{role}_SW"
        G.add_node(access, type="access", floor=floor, vlan=vlan, role=role)
        G.add_edge(dist, access, bandwidth=CAPACITY["dist_access"])

        role_octet = ROLE_OCTET[role]
        subnet = f"10.{floor}.{role_octet}.0/24"
        dhcp_pools[vlan] = make_dhcp_pool(subnet)

        pc_count = 2 if role == "CLASS" else 10

        for i in range(pc_count):
            pc = f"PC_F{floor}_{role}_{i+1}"
            ip = str(dhcp_pools[vlan].pop(0))

            G.add_node(
                pc,
                type="pc",
                vlan=vlan,
                floor=floor,
                role=role,
                ip=ip
            )

            G.add_edge(access, pc, bandwidth=CAPACITY["access_pc"])

# -----------------------------
# EXAM SERVER
# -----------------------------
G.add_node(
    "EXAM_SERVER",
    type="server",
    vlan=102,
    ip="10.1.20.10"
)

G.add_edge("CORE", "EXAM_SERVER", bandwidth=1000)

# -----------------------------
# EDGE ATTRIBUTES
# -----------------------------
for u, v, d in G.edges(data=True):
    d["base_delay"] = random.uniform(1, 5)
    d["load"] = 0

# -----------------------------
# PACKET SIMULATION
# -----------------------------
def simulate_packet(G, src, dst):
    try:
        path = nx.shortest_path(G, src, dst)
    except nx.NetworkXNoPath:
        return None

    ttl = TTL_INIT
    delay = 0
    hops = 0

    for i in range(len(path) - 1):

        if ttl <= 0:
            return False, delay, hops, "TTL"

        u, v = path[i], path[i + 1]
        e = G[u][v]

        congestion = max(1, e["load"] / e["bandwidth"])
        d = e["base_delay"] * congestion
        loss_prob = min(0.3, congestion * 0.05)

        if random.random() < loss_prob:
            return False, delay, hops, "LOSS"

        delay += d
        ttl -= 1
        hops += 1
        e["load"] += random.randint(1, 10)

    return True, delay, hops, "OK"

# -----------------------------
# RUN SIMULATION
# -----------------------------
lab_pcs = [
    n for n in G.nodes
    if G.nodes[n].get("type") == "pc" and G.nodes[n].get("role") == "LAB"
]

delays = []
hops = []
loss = 0
ttl_drop = 0

for _ in range(PACKETS):
    src = random.choice(lab_pcs)
    result = simulate_packet(G, src, "EXAM_SERVER")

    if result is None:
        continue

    delivered, d, h, reason = result

    if delivered:
        delays.append(d)
        hops.append(h)
    else:
        loss += 1
        if reason == "TTL":
            ttl_drop += 1

# -----------------------------
# PLOTS
# -----------------------------
plt.figure()
plt.hist(delays, bins=20)
plt.xlabel("End-to-End Delay (ms)")
plt.ylabel("Packets")
plt.title("Packet Delay Distribution")
plt.show()

plt.figure()
plt.bar(["Delivered", "Lost"], [len(delays), loss])
plt.ylabel("Packets")
plt.title("Packet Delivery vs Loss")
plt.show()

plt.figure()
plt.hist(hops, bins=range(min(hops), max(hops) + 2))
plt.xlabel("Hop Count (TTL Used)")
plt.ylabel("Packets")
plt.title("TTL / Hop Count Distribution")
plt.show()

# -----------------------------
# STATS
# -----------------------------
print("Packets sent:", PACKETS)
print("Delivered:", len(delays))
print("Lost:", loss)
print("TTL drops:", ttl_drop)
print("Average delay:", sum(delays) / len(delays) if delays else 0)
print("Average hops:", sum(hops) / len(hops) if hops else 0)