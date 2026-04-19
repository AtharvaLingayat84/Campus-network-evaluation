# Quick Reference Guide

## Running the Simulation

### Option 1: Enhanced Simulation (Recommended)
```bash
python run_enhanced_simulation.py
```
Generates all outputs: visualizations, CSV, JSON, reports, comparison analysis.

### Option 2: Original Simulation
```bash
python campus_network_simulation.py
```
Generates basic topology and statistics visualizations only.

---

## Configuration

Edit `config.yaml` to customize simulation parameters without code changes:

```yaml
simulation:
  duration_seconds: 60
  packet_loss_rate: 0.02
  max_ttl: 64

bandwidth:
  wan_link_mbps: 10000
  core_link_mbps: 8000
  distribution_link_mbps: 4000
  access_link_mbps: 1000
  end_device_mbps: 100
```

---

## Output Files

### Visualizations
| File | Shows |
|------|-------|
| topology_*.png | Network topology diagram |
| vlan_traffic_*.png | Per-VLAN packet volume |
| device_performance.png | Device type delivery rates |
| traffic_distribution.png | Pie chart of traffic breakdown |
| delay_distribution_*.png | Latency box plots by VLAN |
| loss_breakdown_*.png | Loss reasons (stacked bar) |
| path_efficiency.png | Hop count distribution |
| temporal_analysis.png | Cumulative delivery over time |
| communication_heatmap.png | Device pair traffic matrix |

### Data Exports
| File | Format | Content |
|------|--------|---------|
| simulation_results_*.csv | CSV | Packet-level data |
| simulation_summary_*.json | JSON | Summary metrics |
| network_evaluation_report_*.txt | Text | Human-readable analysis |
| simulation_comparison.json | JSON | Normal vs. exam comparison |

---

## Interpreting Results

### Key Metrics
- **Delivery Rate**: % of packets successfully delivered (target: >95%)
- **Avg Delay**: Mean end-to-end latency in ms (target: <50ms)
- **Avg Hops**: Average hop count (target: 3-5)
- **Link Loss**: Congestion-based packet drop (check if >5%)
- **TTL Exceeded**: Misconfigured routing (should be ~0%)
- **ACL Blocked**: Policy-enforced drops (expected in exam mode)

### Comparing Modes
- **Normal mode**: All traffic destinations active (5 types)
- **Exam mode**: Only Exam + Email servers active (2 types)
- **Expected difference**: Exam mode ~30-40% fewer packets, similar delivery rate, possible latency increase

---

## Troubleshooting

### Low Delivery Rate (<85%)
1. Check `loss_breakdown` visualization: Which reason dominates?
2. Increase bandwidth in config.yaml
3. Review `delay_distribution`: High variance = congestion

### High Latency (>100ms)
1. Check hop count distribution (too many hops?)
2. Review per-VLAN delay: Which VLAN is slow?
3. Consider network diameter - is topology too large?

### Unexpected ACL Blocks
1. Verify exam mode is active (check logs)
2. Check EXAM_ALLOWED_IPS in config
3. Review loss_breakdown: ACL blocked % should be ~10-15% in exam mode

### Missing Visualizations
1. Ensure output/ directory exists
2. Check matplotlib is installed: `pip install matplotlib`
3. Verify pandas and numpy are available

---

## Code Examples

### Running Simulation Programmatically
```python
from run_enhanced_simulation import run_complete_simulation

# Run both normal and exam mode
normal_results, exam_results = run_complete_simulation()

# Access packet data
packets = normal_results['packets']
print(f"Total packets: {len(packets)}")

# Access analyzer
analyzer = normal_results['analyzer']
stats = analyzer.get_overall_stats()
print(f"Delivery rate: {stats['delivery_rate']}%")
```

### Custom Analysis
```python
from network_analyzer import NetworkAnalyzer
from packet_collector import PacketRecord

# Create analyzer from packets
analyzer = NetworkAnalyzer(packets)

# Get various statistics
vlan_stats = analyzer.get_vlan_statistics()
device_stats = analyzer.get_device_statistics()
traffic_stats = analyzer.get_traffic_type_statistics()

# Print results
print(vlan_stats)
print(device_stats)
```

### Custom Export
```python
from data_exporter import DataExporter

exporter = DataExporter(packets, {}, output_dir="./output")
exporter.to_csv("my_results.csv")
exporter.to_json("my_summary.json")
```

---

## Module Reference

| Module | Purpose | Key Classes |
|--------|---------|------------|
| campus_network_simulation.py | Core SimPy engine | CampusNetwork, Packet |
| network_analyzer.py | Metrics computation | NetworkAnalyzer |
| data_exporter.py | Data export | DataExporter |
| visualization_enhanced.py | Charts and graphs | EnhancedVisualizations |
| report_generator.py | Report generation | ReportGenerator |
| packet_collector.py | Data structures | PacketRecord |

---

## Performance Tips

- **Faster visualization**: Comment out optional heatmap (slow with many devices)
- **Faster analysis**: Use pre-computed DataFrames from analyzer
- **Faster export**: CSV faster than Pickle for large datasets
- **Faster simulation**: Reduce SIM_TIME in config.yaml for testing

---

## File Structure Explanation

```
Campus-network-evaluation/
├── campus_network_simulation.py     # Original core engine
├── run_enhanced_simulation.py       # New: Enhanced wrapper
├── network_analyzer.py              # New: Analytics
├── data_exporter.py                 # New: Export
├── visualization_enhanced.py        # New: Visualizations
├── report_generator.py              # New: Reports
├── packet_collector.py              # New: Data structures
├── config.yaml                      # New: Configuration
├── README.md                        # Updated: Comprehensive guide
├── docs/
│   ├── ARCHITECTURE.md              # New: Network design
│   ├── ANALYSIS_GUIDE.md            # New: Interpretation
│   └── EXTENDING.md                 # New: Developer guide
├── archive/                         # Old: Deprecated files
└── output/                          # Generated: Results
```

---

## Documentation Quick Links

- **Getting Started**: README.md (Quick Start section)
- **Network Design**: docs/ARCHITECTURE.md
- **Understanding Results**: docs/ANALYSIS_GUIDE.md
- **Adding Features**: docs/EXTENDING.md
- **Configuration**: config.yaml (well-commented)

---

## Common Commands

```bash
# Run simulation
python run_enhanced_simulation.py

# Load results in Python
python -c "
import json
data = json.load(open('output/simulation_comparison.json'))
print(data['deltas'])
"

# Analyze CSV
python -c "
import pandas as pd
df = pd.read_csv('output/simulation_results_normal.csv')
print(df['delay_ms'].describe())
"

# List all outputs
ls -lah output/
```

---

## Version History

- **v1.0** (original): Basic topology + 2 visualizations
- **v2.0** (current): Full analytics, reporting, 8+ visualizations, documentation

---

## Support

For detailed help:
- **How to interpret a specific chart?** → See docs/ANALYSIS_GUIDE.md
- **How to add a new metric?** → See docs/EXTENDING.md
- **How does routing work?** → See docs/ARCHITECTURE.md
- **What does delivery rate mean?** → See README.md (Interpretation Guide)

---

**Last Updated**: 2026-04-08
