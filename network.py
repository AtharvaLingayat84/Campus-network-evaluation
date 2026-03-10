import simpy
import networkx as nx
import matplotlib.pyplot as plt
import random

# --- SETTINGS ---
SIM_TIME = 100
PACKET_LOSS_RATE = 0.05  # 5% chance a packet is lost to random link errors
RIP_MAX_HOPS = 15        # RIP Realism: RIP drops packets if hops > 15

class CampusNetwork:
    def __init__(self, env):
        self.env = env
        self.G = nx.Graph()
        
        # Data trackers for our Charts
        self.delivered = 0
        self.lost_to_errors = 0
        self.lost_to_rip = 0
        self.delay_log = []
        self.hop_log = []
        
        self.create_topology()

    def create_topology(self):
        # 1. CORE LAYER (Top layer = 0)
        self.G.add_node("Core", layer=0)
        
        # 2. DISTRIBUTION LAYER (Middle layer = 1 - Department Routers)
        depts = ['IT', 'CS', 'EXTC']
        for dept in depts:
            router = f"R_{dept}"
            self.G.add_node(router, layer=1)
            self.G.add_edge("Core", router)
            
            # 3. ACCESS LAYER (Bottom layer = 2 - Student/Lab Hosts)
            for i in range(1, 4):
                host = f"H_{dept}_{i}"
                self.G.add_node(host, layer=2)
                self.G.add_edge(router, host)

    def send_packet(self, src, dest):
        # RIP LOGIC: RIP uses hop count as its routing metric. 
        # nx.shortest_path perfectly mimics RIP because it counts nodes to find the shortest path.
        path = nx.shortest_path(self.G, src, dest)
        hops = len(path) - 1
        
        # Simulating the time it takes for routers to initially process the packet
        yield self.env.timeout(0.5) 
        
        # RIP REALISM: Drop packet if it exceeds the 15-hop limit
        if hops > RIP_MAX_HOPS:
            self.lost_to_rip += 1
            return # Stop processing this packet, it's dropped
            
        # Simulate random network link errors
        if random.random() < PACKET_LOSS_RATE:
            self.lost_to_errors += 1
        else:
            # Realistic delay math: Base transit time + (hops * processing time) + random jitter
            total_delay = 5 + (hops * 2) + random.uniform(0, 3)
            self.delay_log.append(total_delay)
            self.hop_log.append(hops)
            self.delivered += 1

    def generate_traffic(self):
        # Create a list of ONLY the hosts (layer 2) to send traffic between
        hosts = [n for n, d in self.G.nodes(data=True) if d.get('layer') == 2]
        
        while True:
            # Wait a random amount of time before sending the next packet
            yield self.env.timeout(random.uniform(0.2, 1.0))
            
            # Pick a random source and destination host
            src, dest = random.sample(hosts, 2)
            
            # Trigger the packet sending process
            self.env.process(self.send_packet(src, dest))

# --- RUN SIMULATION ---
env = simpy.Environment()
net = CampusNetwork(env)
env.process(net.generate_traffic())
print("Running simulation...")
env.run(until=SIM_TIME)

# --- VISUALIZATION ---
fig = plt.figure(figsize=(16, 10))

# 1. TOPOLOGY MAP (Top Half)
ax_top = plt.subplot2grid((2, 3), (0, 0), colspan=3)

# Use multipartite_layout to structure the layers
pos = nx.multipartite_layout(net.G, subset_key="layer", align="horizontal")

# FIX: Flip the Y-coordinates to put Layer 0 (Core) at the TOP of the image
for node in pos:
    pos[node][1] = -pos[node][1]

colors = ['#FF5733', '#33FF57', '#3357FF'] # Red=Core, Green=Router, Blue=Host
node_colors = [colors[net.G.nodes[n]['layer']] for n in net.G.nodes]

# Draw the network 
nx.draw(net.G, pos, ax=ax_top, with_labels=True, node_color=node_colors, 
        node_size=1500, font_size=10, font_weight="bold", edge_color='gray')
ax_top.set_title("Campus Network Topology (Core -> Distribution -> Access)")
ax_top.margins(0.1) # Add padding so top/bottom nodes aren't cut off

# 2. DELIVERY VS LOSS (Bottom Left)
ax1 = plt.subplot2grid((2, 3), (1, 0))
ax1.bar(['Delivered', 'Link Loss', 'RIP Drop'], 
        [net.delivered, net.lost_to_errors, net.lost_to_rip], 
        color=['blue', 'red', 'darkred'])
ax1.set_title("Packet Delivery Status")

# 3. HOP COUNT (Bottom Middle)
ax2 = plt.subplot2grid((2, 3), (1, 1))
if net.hop_log:
    ax2.hist(net.hop_log, bins=range(1, 8), align='left', rwidth=0.7, color='green')
ax2.set_title("Hop Count Distribution (RIP Metric)")
ax2.set_xlabel("Number of Hops")

# 4. DELAY (Bottom Right)
ax3 = plt.subplot2grid((2, 3), (1, 2))
if net.delay_log:
    ax3.hist(net.delay_log, bins=12, color='orange', edgecolor='black')
ax3.set_title("End-to-End Delay")
ax3.set_xlabel("Delay (ms)")

plt.tight_layout()
plt.show()