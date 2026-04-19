# Developer's Guide - Extending the Simulator

This guide explains how to add new features, metrics, visualizations, and network topologies to the simulator.

## Architecture Overview

The simulator consists of interconnected modules:

```
run_enhanced_simulation.py (Main entry point)
├── campus_network_simulation.py (Core SimPy engine)
├── network_analyzer.py (Metrics computation)
├── data_exporter.py (CSV/JSON export)
├── visualization_enhanced.py (Charts)
├── report_generator.py (Report generation)
└── packet_collector.py (Data structures)
```

### Module Responsibilities

| Module | Purpose | Key Classes/Functions |
|--------|---------|---------------------|
| campus_network_simulation | Network simulation engine | CampusNetwork, Packet, run_simulation() |
| network_analyzer | Analytics computation | NetworkAnalyzer.get_vlan_statistics() |
| data_exporter | Structured output | DataExporter.to_csv(), to_json() |
| visualization_enhanced | Charts and graphs | EnhancedVisualizations.plot_*() |
| report_generator | Reports | ReportGenerator.generate_text_report() |
| packet_collector | Data structures | PacketRecord, PacketCollector |

---

## Adding New Metrics

### Step 1: Define Metric Computation

Add method to `NetworkAnalyzer` class in `network_analyzer.py`:

```python
def get_link_utilization(self) -> Dict[str, float]:
    """
    Calculate per-link utilization based on packet volume.
    
    Returns:
        Dictionary mapping link ID to utilization percentage
    """
    link_traffic = defaultdict(int)
    
    for _, row in self.df.iterrows():
        # Attribute packets to links along their path
        # (This is a simplified example)
        link_traffic[f"{row['src_vlan']}-{row['dst_vlan']}"] += 1
    
    # Normalize by link bandwidth (from config)
    # utilization = packets / (bandwidth * time)
    
    return {link: (traffic / expected_capacity) * 100 
            for link, traffic in link_traffic.items()}
```

### Step 2: Export Metric in JSON

Update `DataExporter` to include new metric:

```python
def to_json(self, filename: str = "simulation_summary.json") -> str:
    # ... existing code ...
    
    json_data = {
        # ... existing fields ...
        'link_utilization': self.analyzer.get_link_utilization(),  # ADD THIS
    }
    
    # ... rest of method ...
```

### Step 3: Visualize Metric (Optional)

Add visualization to `EnhancedVisualizations`:

```python
def plot_link_utilization(self) -> str:
    """Visualize per-link utilization."""
    util = self.analyzer.get_link_utilization()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    links = list(util.keys())
    values = list(util.values())
    
    colors = ['#2ecc71' if v < 60 else '#f39c12' if v < 80 else '#e74c3c' 
              for v in values]
    ax.bar(links, values, color=colors, alpha=0.8)
    
    ax.set_ylabel('Utilization (%)', fontweight='bold')
    ax.set_title('Per-Link Utilization', fontweight='bold')
    ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Warning threshold')
    ax.legend()
    
    filepath = os.path.join(self.output_dir, "link_utilization.png")
    plt.tight_layout()
    plt.savefig(filepath, dpi=self.dpi)
    plt.close()
    
    return filepath
```

### Step 4: Integrate into Simulation

Update `run_enhanced_simulation.py`:

```python
# In run_complete_simulation():

# Generate visualizations
visualizer = EnhancedVisualizations(analyzer_normal, output_dir)
# ... existing visualizations ...
visualizer.plot_link_utilization()  # ADD THIS
```

---

## Adding New Visualizations

### Creating a Simple Histogram

```python
# In visualization_enhanced.py

def plot_packet_sizes(self) -> str:
    """
    Visualize distribution of packet sizes.
    """
    if len(self.analyzer.df) == 0:
        return ""
    
    sizes = self.analyzer.df['bytes'].values
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(sizes, bins=20, color='#3498db', alpha=0.8, edgecolor='black')
    ax.set_xlabel('Packet Size (bytes)', fontweight='bold')
    ax.set_ylabel('Frequency', fontweight='bold')
    ax.set_title('Packet Size Distribution', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    
    filepath = os.path.join(self.output_dir, "packet_sizes.png")
    plt.tight_layout()
    plt.savefig(filepath, dpi=self.dpi)
    plt.close()
    
    print(f"✓ Visualization: {filepath}")
    return filepath
```

### Creating a Network Graph Visualization

```python
import networkx as nx

def plot_traffic_graph(self) -> str:
    """
    Create network graph showing traffic flows.
    """
    comm_matrix = self.analyzer.get_device_pair_communication()
    
    # Build directed graph
    G = nx.DiGraph()
    
    # Add edges weighted by traffic volume
    for src, dests in comm_matrix.items():
        for dst, traffic in dests.items():
            if traffic > 10:  # Only show significant flows
                G.add_edge(src, dst, weight=traffic)
    
    fig, ax = plt.subplots(figsize=(16, 12))
    
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Draw edges with width proportional to traffic
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    max_weight = max(weights) if weights else 1
    
    nx.draw_networkx_edges(G, pos, width=[w/max_weight*3 for w in weights],
                          alpha=0.5, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color='#3498db', 
                          ax=ax, alpha=0.8)
    nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
    
    ax.set_title('Device Communication Flows', fontsize=14, fontweight='bold')
    ax.axis('off')
    
    filepath = os.path.join(self.output_dir, "traffic_graph.png")
    plt.tight_layout()
    plt.savefig(filepath, dpi=self.dpi)
    plt.close()
    
    return filepath
```

---

## Modifying Network Topology

### Adding a New Device Type

Edit `campus_network_simulation.py`, find `_build_topology()` method:

```python
def _build_topology(self):
    # ... existing code ...
    
    # Add new device type to existing VLAN
    self._add_node(
        "SURVEILLANCE_CAM_101",
        type="camera",
        vlan=101,
        campus="MAIN",
        floor=1,
    )
    
    # Connect to access switch
    self._add_link("SURVEILLANCE_CAM_101", "FLOOR1_SWITCH", tier="access")
```

### Adding a New Floor

```python
def _build_topology(self):
    # ... existing code ...
    
    # Increase floor count
    "num_floors": 9,  # Was 8
    "vlans": list(range(101, 110)),  # Add VLAN 109
    
    # Add new floor devices
    new_vlan = 109
    floor = 9
    
    # Create floor switch
    self._add_node(
        f"MAIN_F{floor}_SWITCH",
        type="switch",
        vlan=new_vlan,
        campus="MAIN",
        floor=floor,
    )
    
    # Connect to distribution layer
    self._add_link(f"MAIN_F{floor}_SWITCH", "DIST_SW1", tier="distribution")
    
    # Add devices (PCs, printer, AP, etc.)
    for pc_id in range(1, 9):  # 8 PCs
        self._add_node(
            f"MAIN_F{floor}_PC{pc_id}",
            type="pc",
            vlan=new_vlan,
            campus="MAIN",
            floor=floor,
        )
        self._add_link(f"MAIN_F{floor}_PC{pc_id}", 
                      f"MAIN_F{floor}_SWITCH", 
                      tier="access")
    
    # Add other devices (printer, AP, laptop, phone)
    # ... (follow pattern from existing floors)
```

### Adding a New Server

```python
def _build_topology(self):
    # Update SERVERS_INFO
    self.SERVERS_INFO = {
        "EXAM_SERVER": {"ip": "10.128.0.10", "role": "exam"},
        "EMAIL_SERVER": {"ip": "10.128.0.20", "role": "email"},
        "CLOUD_SERVER": {"ip": "10.128.0.30", "role": "cloud"},
        "FILE_SERVER": {"ip": "10.128.0.40", "role": "file"},  # NEW
    }
    
    # Add node for server
    self._add_node(
        "FILE_SERVER",
        type="server",
        vlan=128,
        ip="10.128.0.40",
        campus=None,
    )
    
    # Connect to server switch
    self._add_link("FILE_SERVER", "SERVER_SWITCH", tier="access")
```

### Changing Link Bandwidth

Edit `LINK_BW` dictionary at top of `campus_network_simulation.py`:

```python
LINK_BW = {
    "wan":        20000,    # 2x faster internet
    "core":       16000,    # 2x faster core
    "distribution": 8000,   # 2x faster distribution
    "access":     2000,     # 2x faster access
    "end_device": 200,      # 2x faster end devices
}
```

Or use config file (recommended):

```yaml
bandwidth:
  wan_link_mbps: 20000
  core_link_mbps: 16000
  distribution_link_mbps: 8000
  access_link_mbps: 2000
  end_device_mbps: 200
```

---

## Modifying Traffic Patterns

### Changing Normal Mode Distribution

In `campus_network_simulation.py`, find `generate_traffic()` method:

```python
# Change traffic weights
roll = random.random()
if roll < 0.50:          # 50% (was 40%)
    dst = "EXAM_SERVER"
elif roll < 0.70:        # 20% (was 20%)
    dst = "EMAIL_SERVER"
elif roll < 0.85:        # 15% (was 10%)
    dst = "CLOUD_SERVER"
elif roll < 0.95:        # 10% (was 10%)
    dst = "INTERNET"
else:                    # 5% (was 20%)
    dst = random.choice([c for c in clients if c != src])
```

Or use config file:

```yaml
traffic:
  traffic_weights:
    exam_server: 0.50
    email_server: 0.20
    cloud_server: 0.15
    internet: 0.10
    peer_to_peer: 0.05
```

### Adding New Traffic Types

Create new method in `CampusNetwork`:

```python
def generate_traffic_backup(self, duration: float = SIM_TIME):
    """Alternative traffic pattern: Heavy backup traffic to file server."""
    
    while True:
        yield self.env.timeout(random.uniform(0.1, 0.3))
        
        src = random.choice(self.clients)
        
        # 70% to file server, 30% P2P
        if random.random() < 0.70:
            dst = "FILE_SERVER"
        else:
            dst = random.choice([c for c in self.clients if c != src])
        
        env.process(self.simulate_packet_flow(src, dst))
```

---

## Adding Network Conditions

### Simulating Link Failure

Modify `simulate_packet_flow()` in campus_network_simulation.py:

```python
# After path computation
path = self._find_path(src_name, dst_name)

# NEW: Simulate link failure between hop i and i+1
failed_link = ("DIST_SW1", "CORE_ROUTER")  # Hard-coded for example
if failed_link in [(path[i], path[i+1]) for i in range(len(path)-1)]:
    self.stats["dropped_loss"] += 1
    logger.info(f"LINK FAILURE: {failed_link[0]} -> {failed_link[1]}")
    return
```

### Simulating Congestion Burst

```python
def generate_traffic_burst(self, duration: float = SIM_TIME):
    """Generate occasional traffic bursts."""
    
    burst_active = False
    
    while True:
        if random.random() < 0.1:  # 10% chance each iteration
            burst_active = not burst_active
        
        # Reduce interval during burst
        interval = 0.02 if burst_active else 0.1
        yield self.env.timeout(random.uniform(interval, interval * 2))
        
        # ... rest of traffic generation ...
```

---

## Creating Custom Analyses

### Example: Per-Floor Analysis

Add to `network_analyzer.py`:

```python
def get_floor_statistics(self) -> Dict[int, Dict[str, Any]]:
    """
    Analyze performance per floor.
    
    Returns:
        Dictionary mapping floor number to statistics
    """
    floor_stats = {}
    
    # Extract floor from device name (e.g., "MAIN_F3_PC1" → floor 3)
    for _, row in self.df.iterrows():
        src_name = row['src_name']
        
        # Parse floor number
        if '_F' in src_name:
            parts = src_name.split('_F')
            if len(parts) > 1:
                floor_num = int(parts[1].split('_')[0])
                
                if floor_num not in floor_stats:
                    floor_stats[floor_num] = {
                        'packets': 0,
                        'delivered': 0,
                        'avg_delay': 0.0,
                    }
                
                floor_stats[floor_num]['packets'] += 1
                if row['status'] == 'delivered':
                    floor_stats[floor_num]['delivered'] += 1
                floor_stats[floor_num]['avg_delay'] += row['delay_ms']
    
    # Finalize statistics
    for floor, stats in floor_stats.items():
        if stats['packets'] > 0:
            stats['delivery_rate'] = round((stats['delivered'] / stats['packets']) * 100, 2)
            stats['avg_delay'] = round(stats['avg_delay'] / stats['packets'], 2)
    
    return floor_stats
```

### Visualization for Custom Analysis

```python
def plot_floor_performance(self) -> str:
    """Visualize per-floor delivery rates."""
    
    floor_stats = self.analyzer.get_floor_statistics()
    
    floors = sorted(floor_stats.keys())
    delivery_rates = [floor_stats[f]['delivery_rate'] for f in floors]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = ['#2ecc71' if r > 95 else '#f39c12' if r > 85 else '#e74c3c' 
              for r in delivery_rates]
    ax.bar(floors, delivery_rates, color=colors, alpha=0.8)
    
    ax.set_xlabel('Floor Number', fontweight='bold')
    ax.set_ylabel('Delivery Rate (%)', fontweight='bold')
    ax.set_title('Delivery Performance by Floor', fontweight='bold')
    ax.set_ylim([0, 105])
    
    filepath = os.path.join(self.output_dir, "floor_performance.png")
    plt.savefig(filepath, dpi=self.dpi)
    plt.close()
    
    return filepath
```

---

## Best Practices

### 1. Maintain Backward Compatibility

When modifying core modules:
- Add new methods rather than changing existing ones
- Use optional parameters with defaults
- Document changes thoroughly

### 2. Follow Naming Conventions

- **Classes**: PascalCase (e.g., `CampusNetwork`)
- **Methods/functions**: snake_case (e.g., `get_vlan_statistics`)
- **Constants**: UPPER_CASE (e.g., `MAX_TTL`)
- **Private methods**: leading underscore (e.g., `_find_path`)

### 3. Add Docstrings

```python
def new_method(self, param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief description of what method does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Example:
        >>> result = obj.new_method("test", 42)
        >>> print(result['key'])
        value
    """
    # Implementation
    pass
```

### 4. Error Handling

```python
def safe_computation(self):
    """Method that handles potential errors."""
    try:
        result = complex_operation()
    except KeyError as e:
        logger.warning(f"Missing data: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
    
    return result
```

### 5. Performance Considerations

- Use Pandas operations (vectorized) instead of loops
- Cache expensive computations
- Profile before optimizing
- Document complexity (O(n²) algorithms, etc.)

---

## Testing New Features

```python
# test_new_feature.py

import pytest
from network_analyzer import NetworkAnalyzer
from packet_collector import PacketRecord

def test_floor_statistics():
    """Test floor analysis computation."""
    
    # Create sample packets
    packets = [
        PacketRecord(
            src_name="MAIN_F1_PC1",
            src_ip="10.1.101.21",
            dst_name="EXAM_SERVER",
            dst_ip="10.128.0.10",
            src_vlan=101,
            dst_vlan=128,
            status="delivered",
            delay_ms=45.0,
            hops=3,
        ),
        # ... more test packets
    ]
    
    analyzer = NetworkAnalyzer(packets)
    floor_stats = analyzer.get_floor_statistics()
    
    assert 1 in floor_stats
    assert floor_stats[1]['packets'] == 1
    assert floor_stats[1]['delivery_rate'] == 100.0

if __name__ == "__main__":
    test_floor_statistics()
    print("✓ Tests passed!")
```

Run tests:
```bash
python test_new_feature.py
# or
pytest test_new_feature.py -v
```

---

## Troubleshooting Common Issues

### Issue: "AttributeError: 'PacketRecord' has no attribute 'xxx'"

**Solution**: Check PacketRecord class definition in `packet_collector.py`. Add missing attribute if needed.

### Issue: "ImportError: No module named 'xxx'"

**Solution**: Ensure all imports in run_enhanced_simulation.py are correct. Check file exists in project directory.

### Issue: "Visualization not appearing"

**Solution**: 
1. Check output directory exists
2. Ensure plt.close() is called after save
3. Verify file paths are correct

### Issue: "Pandas DataFrame operations slow"

**Solution**:
1. Use `.loc` and `.iloc` instead of iterating rows
2. Use `.groupby()` for aggregations
3. Use `.apply()` instead of loops
4. Profile with `cProfile` module

---

## Resources

- **SimPy Documentation**: https://simpy.readthedocs.io/
- **NetworkX Documentation**: https://networkx.org/
- **Pandas Documentation**: https://pandas.pydata.org/
- **Matplotlib Documentation**: https://matplotlib.org/

---

**Last Updated**: 2026-04-08
**Version**: 2.0 (Developer Guide)
