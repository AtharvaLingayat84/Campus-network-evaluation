# Network Architecture Guide

## Topology Overview

The simulator models a realistic enterprise network spanning two physical campuses with centralized server infrastructure.

### Campus Hierarchy

```
┌─────────────────────────────────────────────────────┐
│                 ISR4331 Router (WAN)                │
│              Internet Uplink 10 Gbps                │
└────────────────────────┬────────────────────────────┘
                         │
                  ┌──────┴──────┐
                  │             │
           ┌──────▼──┐   ┌──────▼──┐
           │ ASA FW  │   │ Firewall│
           └──────┬──┘   └────┬─────┘
                  │           │
           ┌──────┴───────────┴──────┐
           │                         │
        ┌──▼────────┐          ┌────▼──────┐
        │Core Router│          │Core Router│
        │8 Gbps     │          │8 Gbps     │
        └──┬────────┘          └────┬──────┘
           │                        │
        ┌──▼─────────────┬──────────▼──┐
        │                │             │
   ┌────▼──────┐   ┌────▼──────┐  ┌──▼──────┐
   │ Dist Sw 1 │   │ Dist Sw 2 │  │Dist Sw 3│
   │4 Gbps     │   │4 Gbps     │  │4 Gbps   │
   └────┬──────┘   └────┬──────┘  └──┬──────┘
        │                │           │
        └────────┬────────┴───────────┘
                 │
        ┌────────┼────────┐
        │        │        │
    ┌───▼──┐ ┌──▼──┐ ┌──▼──┐
    │VLAN  │ │VLAN │ │VLAN │  (12 devices per VLAN)
    │101-  │ │201- │ │ 128 │
    │108   │ │204  │ │ Srv │
    └──────┘ └─────┘ └─────┘
```

### Device Counts

- **ISR4331 Router**: 1 (main gateway)
- **ASA Firewalls**: 2 (security)
- **Core Routers**: 2 (redundancy)
- **Distribution Switches**: 3 (per-campus distribution)
- **Access/Floor Switches**: 12 (8 main + 4 campus2)
- **End Devices**: 144 (12 devices × 12 floors)
- **Servers**: 3 (Exam, Email, Cloud)
- **Total**: 250+ devices

## VLAN Design

### VLAN Allocation

| VLAN | Campus | Name | Purpose | Devices |
|------|--------|------|---------|---------|
| 101-108 | Main | Floor VLANs | End device segmentation | 96 PCs + APs |
| 201-204 | Campus2 | Floor VLANs | End device segmentation | 48 PCs + APs |
| 128 | Both | Server VLAN | Server farming | 3 servers |
| N/A | N/A | Mgmt (implicit) | Management/Infrastructure | Core devices |

### Per-VLAN Characteristics

**Floor VLANs (101-108, 201-204)**:
- **Subnet**: `10.1.{VLAN}.0/24` (Main) or `10.2.{VLAN}.0/24` (Campus2)
- **Gateway**: `.1` (core router subinterface)
- **DHCP pool**: `.21` - `.254` (234 usable hosts per VLAN)
- **Devices per VLAN**: 12 (8 PCs, 1 printer, 1 AP, 1 laptop, 1 phone)

**Server VLAN (128)**:
- **Subnet**: `10.128.0.0/24`
- **Gateway**: `10.128.0.1`
- **Servers**:
  - Exam Server: `10.128.0.10`
  - Email Server: `10.128.0.20`
  - Cloud Server: `10.128.0.30`

## IP Address Allocation Scheme

### Main Campus
```
VLAN 101: 10.1.101.0/24
├── Gateway: 10.1.101.1
├── Reserved: 10.1.101.2 - 10.1.101.20 (infrastructure)
└── DHCP: 10.1.101.21 - 10.1.101.254

VLAN 102: 10.1.102.0/24
... (same pattern)

VLAN 108: 10.1.108.0/24
```

### Campus 2
```
VLAN 201: 10.2.201.0/24
├── Gateway: 10.2.201.1
├── Reserved: 10.2.201.2 - 10.2.201.20
└── DHCP: 10.2.201.21 - 10.2.201.254

... (same pattern for 202-204)
```

### Server VLAN
```
VLAN 128: 10.128.0.0/24
├── Gateway: 10.128.0.1
├── Exam Server: 10.128.0.10
├── Email Server: 10.128.0.20
├── Cloud Server: 10.128.0.30
└── Reserved: 10.128.0.2 - 10.128.0.254
```

## Routing Model

### Router-on-a-Stick Architecture

The core router implements inter-VLAN routing using subinterfaces:

```
Core Router
├── Subinterface G0/0.101 - VLAN 101 gateway (10.1.101.1)
├── Subinterface G0/0.102 - VLAN 102 gateway (10.1.102.1)
├── ... (continues for all VLANs)
├── Subinterface G0/0.201 - VLAN 201 gateway (10.2.201.1)
├── ... (continues for campus2)
└── Subinterface G0/0.128 - Server VLAN gateway (10.128.0.1)
```

### Routing Algorithm

- **Algorithm**: Dijkstra's shortest path (static routing)
- **Path computation**: Per-packet (can be optimized with caching)
- **Link metrics**: Hop count (each edge = 1 hop)
- **Convergence**: Instantaneous (no convergence delays)

### Packet Forwarding Process

1. **Source IP Selection**: Device selects source IP from DHCP assignment
2. **Destination Selection**: Random destination based on traffic distribution
3. **Route Lookup**: Dijkstra shortest path computation (G: NetworkX graph)
4. **TTL Check**: Verify hop count < MAX_TTL (default 64)
5. **Hop-by-hop Forwarding**:
   - TTL decrement at each hop
   - Per-link delay calculation (base + congestion)
   - Congestion-based packet loss
6. **Delivery/Drop**: Record result with metrics

## Packet Flow Example

### Inter-VLAN Communication (10.1.101.50 → 10.128.0.10)

```
Step 1: Source Device (Floor 1, VLAN 101)
├── Source IP: 10.1.101.50
├── Destination IP: 10.128.0.10 (Exam Server)
└── Frame: Src MAC: device MAC, Dst MAC: gateway MAC

Step 2: Access Switch (Floor 1)
├── Receives frame on VLAN 101 access port
├── Forwards to core via trunk (tagged VLAN 101)
└── TTL: 64 → 63

Step 3: Core Router (router-on-a-stick)
├── Receives frame on G0/0.101 (VLAN 101)
├── Route lookup: 10.128.0.10 → Server VLAN
├── Next hop: Distribution Switch
├── Rewrite MAC (router egress MAC)
└── Forward on G0/0.128 trunk

Step 4: Server VLAN Network
├── Distribution switch forwards to server directly
├── Server receives packet on VLAN 128
└── Delivery successful

Metrics:
├── Total hops: 3
├── Total delay: ~15 ms
├── Status: Delivered
└── Path: Floor1Switch → Core → ServerSwitch → Server
```

### Peer-to-Peer Communication (same VLAN)

```
10.1.101.50 → 10.1.101.75 (both on VLAN 101)

Step 1: Source device sends ARP/unicast
Step 2: Access switch learns both MACs on VLAN 101
Step 3: Switch performs L2 forwarding (no routing needed)
Step 4: Destination receives directly

Metrics:
├── Total hops: 1
├── Total delay: ~1 ms
├── Status: Delivered
└── Path: Switch → Destination
```

## Bandwidth & Link Characteristics

### Link Tiers (Mbps)

| Tier | Bandwidth | Typical Links |
|------|-----------|---------------|
| WAN | 10,000 | ISR → Internet |
| Core | 8,000 | Core router ↔ Core router |
| Distribution | 4,000 | Core → Distribution switches |
| Access | 1,000 | Distribution → Floor switches |
| End Device | 100 | End devices → Access switch |

### Congestion Modeling

**Per-link congestion factor**:
```
congestion = link_load / link_bandwidth

packet_loss_probability = min(0.30, PACKET_LOSS_RATE * congestion)
link_delay = base_delay * congestion + random_jitter
```

**Impact**:
- Idle link (load=0): 2% baseline loss
- Half-loaded: 4% loss + 2x delay
- Saturated: 30% loss + 4x delay

## Packet Loss Mechanisms

### 1. Link Congestion Loss
- **Cause**: Link bandwidth exceeded
- **Probability**: Congestion-dependent (0-30%)
- **When**: During forwarding across congested link
- **Recovery**: Packet dropped, no retransmission

### 2. TTL Exhaustion
- **Cause**: Packet exceeds MAX_TTL (default 64)
- **Trigger**: TTL reaches 0
- **When**: At hop calculation or during forwarding
- **Typical scenario**: Misconfigured routes or loops

### 3. ACL Blocking (Exam Mode)
- **Cause**: Access Control List restriction
- **Policy**: Only allow traffic to Exam + Email servers
- **When**: At source during ACL check (pre-routing)
- **Exam mode**: 50% traffic blocked (Cloud + Internet + P2P)

### 4. DHCP Pool Exhaustion
- **Cause**: VLAN DHCP pool depleted
- **Trigger**: All IPs assigned, no more available
- **Rare**: Limited number of clients (144 total)
- **Recovery**: Would need pool expansion

## Traffic Generation Model

### Client Selection
- **Pool**: All end devices (PCs, laptops, phones, wireless devices)
- **Count**: ~96 per campus = 144 total clients
- **Randomization**: Uniform random source per packet

### Destination Selection (Normal Mode)

```python
roll = random.random()
if roll < 0.40:
    destination = "EXAM_SERVER"        # 40%
elif roll < 0.60:
    destination = "EMAIL_SERVER"       # 20%
elif roll < 0.70:
    destination = "CLOUD_SERVER"       # 10%
elif roll < 0.80:
    destination = "INTERNET"           # 10%
else:
    destination = random_other_client()  # 20% (P2P)
```

### Destination Selection (Exam Mode - ACL Active)

```python
roll = random.random()
if roll < 0.50:
    destination = "EXAM_SERVER"        # 50%
else:
    destination = "EMAIL_SERVER"       # 50%
# All other destinations blocked by ACL
```

### Packet Generation Rate
- **Interval**: Random between 100-500 ms
- **Average rate**: ~100-200 packets/second
- **Total simulation**: ~6000-12000 packets in 60 seconds

## Device Type Characteristics

### Servers
- **IP**: Static (10.128.0.x)
- **VLAN**: 128
- **Role**: Destination (receive-only in simulation)
- **Types**: Exam, Email, Cloud

### Routers
- **Role**: Forwarding, inter-VLAN routing
- **Types**: ISR4331 (edge), Core routers (2)
- **Processing**: Route lookup, TTL handling

### Switches
- **Levels**: Core, Distribution, Access
- **Functions**: L2 switching, VLAN tagging/untagging, trunk management
- **Load tracking**: Simulated per-link

### End Devices
- **Types**: PC, Printer, Wireless AP, Laptop, Smartphone
- **Role**: Source and destination for traffic
- **IP assignment**: DHCP per VLAN
- **Wireless devices**: Same treatment as wired (no channel simulation)

## Key Design Decisions

### 1. Why Router-on-a-Stick?
- Simulates common enterprise architecture
- Demonstrates VLAN-aware routing
- Single core router handles all inter-VLAN traffic (can be bottleneck)
- More realistic than direct switch-to-switch VLANs

### 2. Why per-packet path lookup?
- **Pro**: Dynamic routing adaptation (if links could fail)
- **Con**: Performance overhead (Dijkstra per packet)
- **Future**: Optimize with path caching per (source, destination) pair

### 3. Why congestion-based loss only?
- **Simplification**: Easier to reason about
- **Real network**: Includes CRC errors, environmental, hardware failures
- **Future**: Add random bit error rate model

### 4. Why no STP?
- **Assumption**: Topology is loop-free (hierarchical)
- **If cycles exist**: Packets could loop indefinitely
- **Future**: Add STP/RSTP simulation for mesh topologies

## Performance Considerations

### Simulation Bottlenecks
1. **Path lookup**: O(V + E log V) per packet via Dijkstra
2. **Graph traversal**: NetworkX operates on full 250+ node graph
3. **Visualization**: Matplotlib rendering 8+ charts

### Optimization Opportunities
1. **Route caching**: Cache (src, dst) → path mappings
2. **Pre-computed paths**: Build APSP (All-Pairs Shortest Path) matrix
3. **Lazy visualization**: Only render requested charts
4. **Batch packet processing**: Process packets in groups instead of individually

### Scalability Limits
- **Tested**: Up to 250 devices
- **Likely limit**: 500-1000 devices before runtime issues
- **Beyond 1000**: Requires different architecture (distributed simulation)

---

**Last Updated**: 2026-04-08
**Version**: 2.0 (Architecture Documentation)
