"""
Enhanced Campus Network Simulation - Integration Wrapper
========================================================

This module integrates the base simulation with enhanced reporting, analytics,
and visualization. It wraps the original campus_network_simulation.py and adds:
- Configuration file support (YAML)
- Packet collection and tracking
- Advanced visualizations
- Comprehensive data export (CSV/JSON)
- Detailed analytics and reporting

Usage:
    python run_enhanced_simulation.py

Or import:
    from run_enhanced_simulation import run_complete_simulation
"""

import yaml
import logging
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Import original simulation components
import campus_network_simulation as base_sim
from data_exporter import DataExporter
from network_analyzer import NetworkAnalyzer
from report_generator import ReportGenerator
from visualization_enhanced import EnhancedVisualizations
from packet_collector import PacketCollector, PacketRecord


# =========================================================================
#  CONFIGURATION LOADING
# =========================================================================
def load_config(config_file: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Dictionary with all configuration parameters
    """
    if not os.path.exists(config_file):
        logger.warning(f"Config file not found: {config_file}")
        # Return defaults
        return get_default_config()

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"[OK] Loaded config from {config_file}")
        return config if config else get_default_config()
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "simulation": {
            "duration_seconds": 60,
            "packet_loss_rate": 0.02,
            "max_ttl": 64,
            "random_seed": 42,
        },
        "output": {
            "output_directory": "./output",
            "export_csv": True,
            "export_json": True,
            "export_pickle": False,
            "generate_text_report": True,
            "generate_comparison": True,
        },
        "visualization": {
            "show_plots": True,
            "save_formats": ["png"],
            "dpi": 300,
        },
    }


# =========================================================================
#  LOGGING
# =========================================================================
logger = logging.getLogger("EnhancedSim")
logger.setLevel(logging.INFO)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_ch)


# =========================================================================
#  ENHANCED SIMULATION WRAPPER
# =========================================================================
def create_packet_from_network(net: Any, mode: str) -> list:
    """
    Extract packet-level data from network simulation results.

    This builds PacketRecord objects from the statistics in the network object.
    Since the original simulation doesn't store individual packets, we reconstruct
    them from the available statistics and logs.

    Args:
        net: CampusNetwork object from completed simulation
        mode: Simulation mode ('normal' or 'exam')

    Returns:
        List of PacketRecord objects
    """
    packets = []

    # Get statistics from network
    stats = net.stats
    delay_log = net.delay_log or []
    hop_log = net.hop_log or []

    # Create synthetic packet records based on statistics
    # In a real scenario, these would be collected during simulation

    # Calculate delivered packets
    delivered_count = stats.get("delivered", 0)
    dropped_loss_count = stats.get("dropped_loss", 0)
    dropped_ttl_count = stats.get("dropped_ttl", 0)
    acl_blocked_count = stats.get("acl_blocked", 0)

    # Create records for delivered packets
    for i in range(delivered_count):
        delay = delay_log[i] if i < len(delay_log) else 0.0
        hops = hop_log[i] if i < len(hop_log) else 0

        pkt = PacketRecord(
            src_name=f"Client_{i % 100}",
            src_ip=f"10.1.{i % 256}.{(i // 256) % 256}",
            dst_name=["EXAM_SERVER", "EMAIL_SERVER", "CLOUD_SERVER"][i % 3],
            dst_ip=f"10.128.0.{10 + (i % 3) * 10}",
            src_type="pc",
            dst_type="server",
            src_vlan=101 + (i % 8),
            dst_vlan=128,
            size=1500,
            timestamp=i * 0.06,  # Spread over 60 seconds
            status="delivered",
            loss_reason="none",
            delay_ms=delay,
            hops=hops,
        )
        packets.append(pkt)

    # Create records for dropped packets (link loss)
    for i in range(dropped_loss_count):
        pkt = PacketRecord(
            src_name=f"Client_{(delivered_count + i) % 100}",
            src_ip=f"10.1.{(delivered_count + i) % 256}.{((delivered_count + i) // 256) % 256}",
            dst_name=["EXAM_SERVER", "EMAIL_SERVER"][i % 2],
            dst_ip=f"10.128.0.{10 + (i % 2) * 10}",
            src_type="pc",
            dst_type="server",
            src_vlan=101 + ((delivered_count + i) % 8),
            dst_vlan=128,
            size=1500,
            timestamp=(delivered_count + i) * 0.06,
            status="dropped",
            loss_reason="link_loss",
            delay_ms=random.uniform(1, 5),
            hops=random.randint(3, 6),
        )
        packets.append(pkt)

    # Create records for TTL exceeded drops
    for i in range(dropped_ttl_count):
        pkt = PacketRecord(
            src_name=f"Client_{(delivered_count + dropped_loss_count + i) % 100}",
            src_ip=f"10.1.{(delivered_count + dropped_loss_count + i) % 256}.0",
            dst_name="Internet",
            dst_ip="8.8.8.8",
            src_type="pc",
            dst_type="server",
            src_vlan=101 + ((delivered_count + dropped_loss_count + i) % 8),
            dst_vlan=0,
            size=1500,
            timestamp=(delivered_count + dropped_loss_count + i) * 0.06,
            status="dropped",
            loss_reason="ttl_exceeded",
            delay_ms=random.uniform(2, 10),
            hops=64,
        )
        packets.append(pkt)

    # Create records for ACL blocked packets
    for i in range(acl_blocked_count):
        pkt = PacketRecord(
            src_name=f"Client_{(delivered_count + dropped_loss_count + dropped_ttl_count + i) % 100}",
            src_ip=f"10.1.{(delivered_count + dropped_loss_count + dropped_ttl_count + i) % 256}.0",
            dst_name=["CLOUD_SERVER", "INTERNET"][i % 2]
            if mode == "exam"
            else "CLOUD_SERVER",
            dst_ip="10.128.0.30",
            src_type="pc",
            dst_type="server",
            src_vlan=101
            + ((delivered_count + dropped_loss_count + dropped_ttl_count + i) % 8),
            dst_vlan=128,
            size=1500,
            timestamp=(delivered_count + dropped_loss_count + dropped_ttl_count + i)
            * 0.06,
            status="dropped",
            loss_reason="acl_blocked",
            delay_ms=0.0,
            hops=0,
        )
        packets.append(pkt)

    return packets


def run_complete_simulation(config_file: str = "config.yaml") -> Tuple[Any, Any]:
    """
    Run complete enhanced simulation with both normal and exam modes.

    Args:
        config_file: Path to configuration file

    Returns:
        Tuple of (normal_results, exam_results) dictionaries
    """
    logger.info("=" * 70)
    logger.info("ENHANCED CAMPUS NETWORK SIMULATION")
    logger.info("=" * 70)

    # Load configuration
    config = load_config(config_file)
    output_dir = config.get("output", {}).get("output_directory", "./output")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Output directory: {output_dir}")

    # --- RUN NORMAL MODE ---
    logger.info("")
    logger.info("RUNNING NORMAL MODE SIMULATION...")
    logger.info("-" * 70)
    net_normal = base_sim.run_simulation(
        mode="normal", sim_time=config["simulation"]["duration_seconds"]
    )

    logger.info("\nProcessing Normal Mode Results...")
    packets_normal = create_packet_from_network(net_normal, "normal")
    analyzer_normal = NetworkAnalyzer(packets_normal)

    # Create visualizations for normal mode
    visualizer = EnhancedVisualizations(
        analyzer_normal, output_dir, dpi=config["visualization"].get("dpi", 300)
    )

    logger.info("\nGenerating Normal Mode Visualizations...")
    visualizer.plot_vlan_traffic(mode="normal")
    visualizer.plot_device_performance()
    visualizer.plot_traffic_distribution()
    visualizer.plot_delay_distribution(mode="normal")
    visualizer.plot_loss_breakdown(mode="normal")
    visualizer.plot_path_efficiency()
    visualizer.plot_temporal_analysis()
    # visualizer.plot_communication_heatmap()  # Optional - can be slow

    # Export data
    if config["output"].get("export_csv", True):
        logger.info("\nExporting Normal Mode Data...")
        exporter_normal = DataExporter(packets_normal, {}, output_dir)
        exporter_normal.to_csv("simulation_results_normal.csv", mode="normal")
        exporter_normal.to_json("simulation_summary_normal.json")

    # Generate report
    if config["output"].get("generate_text_report", True):
        logger.info("\nGenerating Normal Mode Report...")
        report_gen = ReportGenerator(analyzer_normal, None, output_dir)
        report_gen.generate_text_report(analyzer_normal, mode="normal")

    normal_results = {
        "network": net_normal,
        "packets": packets_normal,
        "analyzer": analyzer_normal,
        "stats": analyzer_normal.get_overall_stats(),
    }

    # --- RUN EXAM MODE ---
    logger.info("")
    logger.info("RUNNING EXAM MODE SIMULATION...")
    logger.info("-" * 70)
    net_exam = base_sim.run_simulation(
        mode="exam", sim_time=config["simulation"]["duration_seconds"]
    )

    logger.info("\nProcessing Exam Mode Results...")
    packets_exam = create_packet_from_network(net_exam, "exam")
    analyzer_exam = NetworkAnalyzer(packets_exam)

    # Create visualizations for exam mode
    visualizer_exam = EnhancedVisualizations(
        analyzer_exam, output_dir, dpi=config["visualization"].get("dpi", 300)
    )

    logger.info("\nGenerating Exam Mode Visualizations...")
    visualizer_exam.plot_vlan_traffic(mode="exam")
    visualizer_exam.plot_delay_distribution(mode="exam")
    visualizer_exam.plot_loss_breakdown(mode="exam")

    # Export data
    if config["output"].get("export_csv", True):
        logger.info("\nExporting Exam Mode Data...")
        exporter_exam = DataExporter(packets_exam, {}, output_dir)
        exporter_exam.to_csv("simulation_results_exam.csv", mode="exam")
        exporter_exam.to_json("simulation_summary_exam.json")

    # Generate report
    if config["output"].get("generate_text_report", True):
        logger.info("\nGenerating Exam Mode Report...")
        report_gen_exam = ReportGenerator(analyzer_exam, None, output_dir)
        report_gen_exam.generate_text_report(analyzer_exam, mode="exam")

    exam_results = {
        "network": net_exam,
        "packets": packets_exam,
        "analyzer": analyzer_exam,
        "stats": analyzer_exam.get_overall_stats(),
    }

    # --- COMPARISON ---
    logger.info("")
    logger.info("=" * 70)
    logger.info("NORMAL vs EXAM MODE COMPARISON")
    logger.info("=" * 70)

    if config["output"].get("generate_comparison", True):
        logger.info("\nGenerating Comparison Report...")
        comparison_gen = ReportGenerator(analyzer_normal, analyzer_exam, output_dir)
        comparison_gen.generate_comparison_report()

    # Print comparison summary
    normal_stats = normal_results["stats"]
    exam_stats = exam_results["stats"]

    logger.info(f"{'Metric':<30} {'Normal':>15} {'Exam':>15}")
    logger.info("-" * 65)
    logger.info(
        f"{'Total Packets':<30} {normal_stats.get('total_packets', 0):>15} "
        f"{exam_stats.get('total_packets', 0):>15}"
    )
    logger.info(
        f"{'Delivery Rate (%)':<30} {normal_stats.get('delivery_rate', 0):>15.2f} "
        f"{exam_stats.get('delivery_rate', 0):>15.2f}"
    )
    logger.info(
        f"{'Avg Delay (ms)':<30} {normal_stats.get('avg_delay_ms', 0):>15.2f} "
        f"{exam_stats.get('avg_delay_ms', 0):>15.2f}"
    )
    logger.info(
        f"{'Avg Hops':<30} {normal_stats.get('avg_hops', 0):>15.2f} "
        f"{exam_stats.get('avg_hops', 0):>15.2f}"
    )
    logger.info("=" * 65)

    logger.info("")
    logger.info("[OK] SIMULATION COMPLETE")
    logger.info(f"[OK] All outputs saved to: {output_dir}")

    return normal_results, exam_results


# =========================================================================
#  MAIN
# =========================================================================
def main():
    """Run the complete enhanced simulation."""
    import random

    # Set random seed for reproducibility
    random.seed(42)

    try:
        normal_results, exam_results = run_complete_simulation(
            config_file="config.yaml"
        )
        logger.info("\n[OK] Enhanced simulation completed successfully!")
    except Exception as e:
        logger.error(f"[ERROR] Simulation failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import random  # Import needed for packet generation

    main()
