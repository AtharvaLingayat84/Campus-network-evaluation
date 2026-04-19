import simpy
import networkx as nx
import matplotlib.pyplot as plt
import random

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
        self.G.add_node("Core", layer=0)

        depts = ['IT', 'CS', 'EXTC']

        for dept in depts:
            router = f"R_{dept}"
            self.G.add_node(router, layer=1)
            self.G.add_edge("Core", router)

            for i in range(1,4):
                host = f"H_{dept}_{i}"
                self.G.add_node(host, layer=2)
                self.G.add_edge(router, host)

    def send_packet(self, src, dest):

        path = nx.shortest_path(self.G, src, dest)
        hops = len(path) - 1

        yield self.env.timeout(0.5)

        if hops > RIP_MAX_HOPS:
            self.lost_to_rip += 1
            return

        if random.random() < PACKET_LOSS_RATE:
            self.lost_to_errors += 1

        else:
            total_delay = 5 + (hops * 2) + random.uniform(0,3)
            self.delay_log.append(total_delay)
            self.hop_log.append(hops)
            self.delivered += 1

    def generate_traffic(self):

        hosts = [n for n,d in self.G.nodes(data=True) if d.get('layer') == 2]

        while True:
            yield self.env.timeout(random.uniform(0.2,1.0))

            src, dest = random.sample(hosts,2)

            self.env.process(self.send_packet(src,dest))


env = simpy.Environment()
net = CampusNetwork(env)

env.process(net.generate_traffic())

print("Running simulation...")
env.run(until=SIM_TIME)

nx.write_gexf(net.G,"campus_network.gexf")

fig = plt.figure(figsize=(16,10))

ax_top = plt.subplot2grid((2,3),(0,0),colspan=3)

pos = nx.multipartite_layout(net.G,subset_key="layer",align="horizontal")

for node in pos:
    pos[node][1] = -pos[node][1]

colors = ['#FF5733','#33FF57','#3357FF']
node_colors = [colors[net.G.nodes[n]['layer']] for n in net.G.nodes]

nx.draw(net.G,pos,ax=ax_top,with_labels=True,node_color=node_colors,
        node_size=1500,font_size=10,font_weight="bold",edge_color='gray')

ax_top.set_title("Campus Network Topology (Core -> Distribution -> Access)")
ax_top.margins(0.1)

ax1 = plt.subplot2grid((2,3),(1,0))
ax1.bar(['Delivered','Link Loss','RIP Drop'],
        [net.delivered,net.lost_to_errors,net.lost_to_rip],
        color=['blue','red','darkred'])
ax1.set_title("Packet Delivery Status")

ax2 = plt.subplot2grid((2,3),(1,1))
if net.hop_log:
    ax2.hist(net.hop_log,bins=range(1,8),align='left',rwidth=0.7,color='green')
ax2.set_title("Hop Count Distribution (RIP Metric)")
ax2.set_xlabel("Number of Hops")

ax3 = plt.subplot2grid((2,3),(1,2))
if net.delay_log:
    ax3.hist(net.delay_log,bins=12,color='orange',edgecolor='black')
ax3.set_title("End-to-End Delay")
ax3.set_xlabel("Delay (ms)")

plt.tight_layout()
plt.show()