import simpy
import networkx as nx
import matplotlib.pyplot as plt
import random

# --- SETTINGS ---
SIM_TIME = 100
PACKET_LOSS_RATE = 0.05  
RIP_MAX_HOPS = 15        

class CampusNetwork:
    def __init__(self, env):
        self.env = env
        self.G = nx.Graph()
        
        self.delivered = 0
        self.lost_to_errors = 0
        self.lost_to_rip = 0
        self.delay_log = []
        self.hop_log = []
        
        self.create_topology()

    def create_topology(self):
        # 1. CORE LAYER
        self.G.add_node("Core", layer=0)
        
        # 2. DISTRIBUTION LAYER (Academic Departments)
        depts = ['IT', 'CS', 'EXTC']
        for dept in depts:
            router = f"R_{dept}"
            self.G.add_node(router, layer=1)
            self.G.add_edge("Core", router)
            
            # 3. ACCESS LAYER (Student Labs)
            for i in range(1, 4):
                host = f"H_{dept}_{i}"
                self.G.add_node(host, layer=2)
                self.G.add_edge(router, host)

    def break_link_event(self):
        # Wait exactly halfway through the simulation
        yield self.env.timeout(SIM_TIME / 2)
        
        print("\n" + "="*60)
        print(f"[!] TIME {self.env.now}: FIBER CUT DETECTED!")
        print("[!] A construction crew cut the main cable to the IT building.")
        print("[!] WARNING: IT Department is now completely isolated!")
        print("="*60 + "\n")
        
        # Remove the main edge connecting the Core to the IT department
        if self.G.has_edge("Core", "R_IT"):
            self.G.remove_edge("Core", "R_IT")

    def send_packet(self, src, dest):
        try:
            path = nx.shortest_path(self.G, src, dest)
            hops = len(path) - 1
            
            yield self.env.timeout(0.5) 
            
            if hops > RIP_MAX_HOPS:
                self.lost_to_rip += 1
                return 
                
            if random.random() < PACKET_LOSS_RATE:
                self.lost_to_errors += 1
            else:
                total_delay = 5 + (hops * 2) + random.uniform(0, 3)
                self.delay_log.append(total_delay)
                self.hop_log.append(hops)
                self.delivered += 1
                
                # We increased traffic, so now we only print every 100th success to avoid lag
                if self.delivered % 100 == 0:
                    print(f"[{self.env.now:>5.1f}s] Success: {src} -> {dest} | Hops: {hops} | Delay: {total_delay:.1f}ms")
                    
        except nx.NetworkXNoPath:
            # When IT gets cut off, routing fails. 
            self.lost_to_errors += 1
            
            # Print a warning for dropped packets so we can see the outage happening
            if self.lost_to_errors % 50 == 0: 
                print(f"[{self.env.now:>5.1f}s] DROP: No route between {src} and {dest}!")

    def generate_traffic(self):
        hosts = [n for n, d in self.G.nodes(data=True) if d.get('layer') == 2]
        while True:
            # FIX: We dramatically lowered the delay here to pump out 10x more packets!
            yield self.env.timeout(random.uniform(0.01, 0.05)) 
            src, dest = random.sample(hosts, 2)
            self.env.process(self.send_packet(src, dest))

# --- RUN SIMULATION ---
env = simpy.Environment()
net = CampusNetwork(env)

env.process(net.generate_traffic())
env.process(net.break_link_event()) 

print("Running High-Traffic simulation... Watch the console!\n")
env.run(until=SIM_TIME)

# --- VISUALIZATION ---
fig = plt.figure(figsize=(16, 10))

# 1. TOPOLOGY MAP
ax_top = plt.subplot2grid((2, 3), (0, 0), colspan=3)
pos = nx.multipartite_layout(net.G, subset_key="layer", align="horizontal")

for node in pos:
    pos[node][1] = -pos[node][1]

colors = ['#FF5733', '#33FF57', '#3357FF'] 
node_colors = [colors[net.G.nodes[n]['layer']] for n in net.G.nodes]

nx.draw(net.G, pos, ax=ax_top, with_labels=True, node_color=node_colors, 
        node_size=1500, font_size=10, font_weight="bold", edge_color='gray')
ax_top.set_title("Campus Network (Warning: IT Link will fail at T=50)")
ax_top.margins(0.1) 

# 2. DELIVERY VS LOSS
ax1 = plt.subplot2grid((2, 3), (1, 0))
ax1.bar(['Delivered', 'Link Loss', 'RIP Drop'], 
        [net.delivered, net.lost_to_errors, net.lost_to_rip], 
        color=['blue', 'red', 'darkred'])
ax1.set_title("Packet Delivery Status")

# 3. HOP COUNT 
ax2 = plt.subplot2grid((2, 3), (1, 1))
if net.hop_log:
    ax2.hist(net.hop_log, bins=range(1, 8), align='left', rwidth=0.7, color='green')
ax2.set_title("Hop Count Distribution (RIP Metric)")
ax2.set_xlabel("Number of Hops")

# 4. DELAY 
ax3 = plt.subplot2grid((2, 3), (1, 2))
if net.delay_log:
    ax3.hist(net.delay_log, bins=12, color='orange', edgecolor='black')
ax3.set_title("End-to-End Delay")
ax3.set_xlabel("Delay (ms)")

plt.tight_layout()
plt.show()