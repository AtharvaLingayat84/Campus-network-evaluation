# Campus Network Evaluation Simulator

A discrete-event network simulator that models a realistic 2-campus enterprise network with 250+ devices, VLAN segmentation, and Cisco IOS routing concepts. Provides comprehensive analysis capabilities including advanced visualizations, detailed metrics, and automated reporting.

## 🎯 Overview

This project simulates a complex campus network topology with:
- **2 campuses**: Main Campus (8 floors) + Campus 2 (4 floors)
- **250+ network devices**: PCs, printers, wireless APs, phones, servers, routers, switches
- **VLAN segmentation**: Isolated VLANs per floor with inter-VLAN routing
- **Router-on-a-stick architecture**: Central core router for VLAN communication
- **Dynamic DHCP**: Automatic IP assignment per VLAN
- **ACL-based policies**: Normal vs. Exam mode traffic restrictions
- **Realistic packet flow**: Hop-by-hop forwarding, TTL handling, congestion-based loss

## ✨ Key Features

### Simulation Capabilities
- **60-second simulation** of realistic enterprise network traffic
- **Packet-level tracking**: Source, destination, VLAN, delay, hops, status
- **Dual-mode operation**: Normal mode (all traffic) vs. Exam mode (restricted destinations)
- **Loss modeling**: Congestion-based link loss, TTL expiration, ACL blocking
- **Delay calculation**: Per-link delays with congestion factor

### Analysis & Reporting
- **8 advanced visualizations**: VLAN traffic, device performance, delay distribution, loss breakdown, temporal analysis, path efficiency, traffic distribution, device communication heatmap
- **Structured data export**: CSV (packet-level) and JSON (summary metrics)
- **Per-VLAN analytics**: Traffic volume, delivery rate, latency, packet loss reasons
- **Per-device analytics**: Sender/receiver statistics, primary destinations, performance
- **Per-traffic-type analytics**: Server-specific metrics and comparison
- **Human-readable reports**: Executive summary, findings, recommendations, detailed metrics tables
- **Comparative analysis**: Normal vs. Exam mode deltas and insights

### Configuration Management
- **YAML-based configuration**: Network parameters without code changes
- **Tunable parameters**: Simulation duration, loss rates, bandwidth tiers, traffic patterns
- **Default fallbacks**: Sensible defaults if config file missing

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install simpy networkx matplotlib pyyaml
```

### 2. Run Simulation

```bash
# Using enhanced simulation (recommended)
python run_enhanced_simulation.py

# Or run original simulation
python campus_network_simulation.py
```

### 3. Review Outputs

All outputs saved to `./output/`:
- **PNG visualizations**: Charts and graphs
- **CSV files**: Packet-level data for external analysis
- **JSON files**: Summary metrics and comparison
- **Text reports**: Human-readable evaluation and findings

## 📊 Output Files

### Per Simulation Run (16-18 files total)

#### Visualizations
- `topology_normal.png` - Network topology (normal mode)
- `topology_exam.png` - Network topology (exam mode)
- `vlan_traffic_normal.png` - Per-VLAN packet volume
- `vlan_traffic_exam.png` - Per-VLAN packet volume (exam)
- `device_performance.png` - Device type delivery rates
- `traffic_distribution.png` - Pie chart of traffic breakdown
- `delay_distribution_normal.png` - VLAN latency box plots
- `delay_distribution_exam.png` - VLAN latency box plots (exam)
- `loss_breakdown_normal.png` - Loss reason stacked bars
- `loss_breakdown_exam.png` - Loss reason stacked bars (exam)
- `path_efficiency.png` - Hop count distribution histogram
- `temporal_analysis.png` - Cumulative delivery over time
- `communication_heatmap.png` - Device pair traffic matrix

#### Data Exports
- `simulation_results_normal.csv` - Packet-level data (normal)
- `simulation_results_exam.csv` - Packet-level data (exam)
- `simulation_summary_normal.json` - Metrics summary (normal)
- `simulation_summary_exam.json` - Metrics summary (exam)

#### Reports
- `network_evaluation_report_normal.txt` - Text report (normal)
- `network_evaluation_report_exam.txt` - Text report (exam)
- `simulation_comparison.json` - Mode comparison with deltas

## 🏗️ Network Architecture

### Campus Layout

```
Main Campus (8 floors, VLANs 101-108)
├── ISR4331 Router (WAN gateway)
├── ASA Firewall
├── Core Router/Switch
├── Distribution Layer (2 switches)
└── Access Layer (8 floor switches, 1 per floor)
    └── 12 devices per floor:
        ├── 8 PCs (10.1.VLAN.x)
        ├── 1 Printer (10.1.VLAN.x)
        ├── 1 Wireless AP (10.1.VLAN.x)
        ├── 1 Laptop (10.1.VLAN.x)
        └── 1 Smartphone (10.1.VLAN.x)

Campus 2 (4 floors, VLANs 201-204)
└── [Same structure as Main Campus]

Server VLAN (VLAN 128, 10.128.0.0/24)
├── Exam Server (10.128.0.10)
├── Email Server (10.128.0.20)
└── Cloud Server (10.128.0.30)
```

### IP Addressing Scheme

- **Main Campus**: `10.1.{VLAN}.0/24` (e.g., 10.1.101.0/24 for VLAN 101)
- **Campus 2**: `10.2.{VLAN}.0/24` (e.g., 10.2.201.0/24 for VLAN 201)
- **Servers**: `10.128.0.0/24` (VLAN 128)
- **DHCP**: First 20 IPs reserved for infrastructure, rest for end devices

### Traffic Patterns

Normal mode traffic distribution:
- **40%** → Exam Server
- **20%** → Email Server
- **10%** → Cloud Server
- **10%** → Internet (via ISR4331)
- **20%** → Peer-to-peer (other clients)

Exam mode (ACL active):
- **50%** → Exam Server
- **50%** → Email Server
- Other destinations **blocked**

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
simulation:
  duration_seconds: 60              # Simulation time
  packet_loss_rate: 0.02            # Baseline loss probability
  max_ttl: 64                       # IP TTL limit

bandwidth:
  wan_link_mbps: 10000              # WAN uplink
  core_link_mbps: 8000              # Core infrastructure
  distribution_link_mbps: 4000      # Distribution layer
  access_link_mbps: 1000            # Access layer
  end_device_mbps: 100              # End device links

traffic:
  packet_generation_interval_ms: [100, 500]  # Generation timing
  traffic_weights:
    exam_server: 0.40
    email_server: 0.20
    cloud_server: 0.10
    internet: 0.10
    peer_to_peer: 0.20

output:
  output_directory: "./output"
  export_csv: true
  export_json: true
  generate_text_report: true
  generate_comparison: true

visualization:
  show_plots: true
  save_formats: ["png"]
  dpi: 300
```

## 📖 Documentation

All core project guidance is compiled below so the repository can be understood from this file alone.

### Architecture Summary

- Core engine: `campus_network_simulation.py`
- Unified entry point: `app.py`
- Analytics: `network_analyzer.py`
- Charts: `visualization_enhanced.py`
- Export: `data_exporter.py`
- Reports: `report_generator.py`
- Packet structure: `packet_collector.py`

### Network Flow Summary

1. Build the campus topology with routers, firewall, switches, servers, and end devices.
2. Run traffic in `normal` mode or `exam` mode.
3. Collect packet outcomes and timing data.
4. Analyze the packet set for VLAN, device, traffic-type, delay, and hop metrics.
5. Generate charts, CSV/JSON exports, and text reports.

### Analysis Guide

- Delivery rate shows how many packets reached their destination.
- Average delay measures end-to-end latency.
- Hop count shows path efficiency.
- Loss breakdown separates link loss, TTL expiry, ACL blocking, timeout, and other drops.
- VLAN statistics show performance per subnet/floor.
- Device statistics show how individual sources behave.

### Extension Guide

- To add a chart, extend `EnhancedVisualizations`.
- To add a metric, extend `NetworkAnalyzer`.
- To add a new export format, extend `DataExporter`.
- To change topology or routing behavior, update `campus_network_simulation.py`.
- To change default behavior, edit `config.yaml`.

### Generated Files

- `network_simulation.log` - runtime event log
- `output/*.png` - charts and topology images
- `output/*.csv` - packet-level exports
- `output/*.json` - summaries and comparisons
- `output/*.txt` - human-readable reports

## 🔍 Interpretation Guide

### Delivery Rate
- **Target**: >95% successful delivery
- **What affects it**: Link congestion, ACL rules, path availability
- **Exam vs. Normal**: Usually improves in exam mode (less traffic)

### Average Delay
- **Target**: <50ms average
- **What affects it**: Path length, congestion, number of hops
- **Exam vs. Normal**: May increase due to concentration on fewer servers

### Hop Count Efficiency
- **Ideal**: 3-5 hops average for multi-VLAN communication
- **What affects it**: Network diameter, routing algorithm efficiency
- **Check for**: Suboptimal routing paths, misconfigurations

### Loss Breakdown
- **Link Loss**: Congestion-based packet drop
- **TTL Exceeded**: Packet exceeded hop limit (misconfigured paths)
- **ACL Blocked**: Policy-enforced drop (exam mode)
- **Timeout**: Connection timeout (rare in this simulation)

## 📊 Metrics Explained

### Per-VLAN Metrics
- `packets_total`: Total packets from/to this VLAN
- `delivery_rate`: % successfully delivered
- `avg_delay_ms`: Mean latency for this VLAN
- `loss_reasons`: Breakdown of why packets were lost

### Per-Device Metrics
- `packets_sent`: Packets originated from this device
- `delivery_rate`: % of sent packets successfully delivered
- `primary_destinations`: Top 3 destination devices
- `avg_delay_ms`: Mean latency from this device

### Traffic Type Metrics
- `packets`: Total packets to this destination
- `delivery_rate`: % delivery success
- `percentage`: % of total simulation traffic
- `avg_delay_ms`: Mean latency to this destination

## 🛠️ Development

### Project Structure

```
Campus-network-evaluation/
├── campus_network_simulation.py       # Core simulation engine
├── run_enhanced_simulation.py         # Enhanced wrapper with analytics
├── config.yaml                        # Configuration file
├── data_exporter.py                   # CSV/JSON export module
├── network_analyzer.py                # Analytics computation
├── report_generator.py                # Report generation
├── visualization_enhanced.py          # Enhanced charts and graphs
├── packet_collector.py                # Packet data structures
├── README.md                          # This file
├── docs/
│   ├── ARCHITECTURE.md                # Network design details
│   ├── ANALYSIS_GUIDE.md              # Visualization interpretation
│   └── EXTENDING.md                   # Developer guide
├── archive/                           # Deprecated implementations
│   ├── network.py
│   ├── network_log.py
│   └── project_try.py
└── output/                            # Generated files
    ├── *.png                          # Visualizations
    ├── *.csv                          # Packet data
    └── *.json                         # Metrics and reports
```

### Adding New Features

1. **New visualization**: Add method to `EnhancedVisualizations` class
2. **New metric**: Add computation to `NetworkAnalyzer` class
3. **Custom export**: Extend `DataExporter` class
4. **Topology change**: Modify `campus_network_simulation.py` (see EXTENDING.md)

## 🧪 Testing

```bash
# Run simulation and verify outputs
python run_enhanced_simulation.py

# Check generated files
ls output/

# Validate CSV export
python -c "import csv; print(sum(1 for _ in csv.DictReader(open('output/simulation_results_normal.csv', encoding='utf-8'))))"

# Validate JSON
python -c "import json; data = json.load(open('output/simulation_comparison.json')); print(data['deltas'])"
```

## 📈 Performance

- **Simulation runtime**: ~30-60 seconds (60s sim time on modern laptop)
- **Memory usage**: ~200-300 MB (topology + packet collection)
- **Visualization**: ~10-20 seconds for all 8 charts
- **Total execution**: ~2-3 minutes end-to-end

## ⚠️ Known Limitations

1. **Packet collection**: Currently reconstructed from statistics (not live-collected)
2. **Topology size**: Tested up to 250 devices; scalability beyond 500 not verified
3. **Wireless modeling**: No channel interference or signal strength simulation
4. **Dynamic routing**: Uses static Dijkstra; no OSPF/BGP failover
5. **Traffic patterns**: Fixed weighted distribution; no temporal variation
6. **STP**: No Spanning Tree Protocol; topology must be loop-free

## 🔮 Future Enhancements

- **Phase 2**: Dynamic routing protocols (OSPF, BGP)
- **Phase 3**: Spanning Tree Protocol (STP) simulation
- **Phase 4**: Wireless channel modeling
- **Phase 5**: Real-time dashboard and live monitoring
- **Phase 6**: Cisco Packet Tracer bidirectional integration

## 📝 License

[Add your license here]

## 👤 Author

Campus Network Simulation Project

## 📞 Support

For issues, bugs, or feature requests, please refer to the documentation files or review the source code comments. The system is extensively documented with docstrings and inline comments.

---

**Last Updated**: 2026-04-08
**Version**: 2.0 (Enhanced with Analytics & Reporting)
