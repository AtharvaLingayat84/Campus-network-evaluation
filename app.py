"""
Unified Campus Network Simulation App
=====================================

Single entry point for the existing campus network simulation pipeline.
This keeps the current behavior intact while consolidating the workflow into
one runnable file.

Usage:
    python app.py
    python app.py --config config.yaml
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from typing import Any, Dict, Tuple

import simpy
import yaml

import campus_network_simulation as base_sim
from data_exporter import DataExporter
from network_analyzer import NetworkAnalyzer
from packet_collector import PacketRecord
from report_generator import ReportGenerator
from campus_topology_visualizer import render_campus_topology
from visualization_enhanced import EnhancedVisualizations


logger = logging.getLogger("UnifiedCampusApp")
logger.setLevel(logging.INFO)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(message)s"))
if not logger.handlers:
    logger.addHandler(_ch)


def get_default_config() -> Dict[str, Any]:
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


def load_config(config_file: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_file):
        logger.warning("Config file not found: %s", config_file)
        return get_default_config()

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info("Loaded config from %s", config_file)
        return config if config else get_default_config()
    except Exception as exc:
        logger.error("Error loading config: %s", exc)
        return get_default_config()


def create_packet_from_network(net: Any, mode: str) -> list[PacketRecord]:
    packets: list[PacketRecord] = []

    stats = getattr(net, "stats", {})
    delay_log = getattr(net, "delay_log", []) or []
    hop_log = getattr(net, "hop_log", []) or []

    delivered_count = stats.get("delivered", 0)
    dropped_loss_count = stats.get("dropped_loss", 0)
    dropped_ttl_count = stats.get("dropped_ttl", 0)
    acl_blocked_count = stats.get("acl_blocked", 0)

    for i in range(delivered_count):
        packets.append(
            PacketRecord(
                src_name=f"Client_{i % 100}",
                src_ip=f"10.1.{i % 256}.{(i // 256) % 256}",
                dst_name=["EXAM_SERVER", "EMAIL_SERVER", "CLOUD_SERVER"][i % 3],
                dst_ip=f"10.128.0.{10 + (i % 3) * 10}",
                src_type="pc",
                dst_type="server",
                src_vlan=101 + (i % 8),
                dst_vlan=128,
                size=1500,
                timestamp=i * 0.06,
                status="delivered",
                loss_reason="none",
                delay_ms=delay_log[i] if i < len(delay_log) else 0.0,
                hops=hop_log[i] if i < len(hop_log) else 0,
            )
        )

    for i in range(dropped_loss_count):
        packets.append(
            PacketRecord(
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
        )

    for i in range(dropped_ttl_count):
        packets.append(
            PacketRecord(
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
        )

    for i in range(acl_blocked_count):
        packets.append(
            PacketRecord(
                src_name=f"Client_{(delivered_count + dropped_loss_count + dropped_ttl_count + i) % 100}",
                src_ip=f"10.1.{(delivered_count + dropped_loss_count + dropped_ttl_count + i) % 256}.0",
                dst_name=["CLOUD_SERVER", "INTERNET"][i % 2] if mode == "exam" else "CLOUD_SERVER",
                dst_ip="10.128.0.30",
                src_type="pc",
                dst_type="server",
                src_vlan=101 + ((delivered_count + dropped_loss_count + dropped_ttl_count + i) % 8),
                dst_vlan=128,
                size=1500,
                timestamp=(delivered_count + dropped_loss_count + dropped_ttl_count + i) * 0.06,
                status="dropped",
                loss_reason="acl_blocked",
                delay_ms=0.0,
                hops=0,
            )
        )

    return packets




def run_complete_simulation(config_file: str = "config.yaml") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    print("=" * 70)
    print("UNIFIED CAMPUS NETWORK SIMULATION")
    print("=" * 70)

    config = load_config(config_file)
    output_dir = config.get("output", {}).get("output_directory", "./output")
    os.makedirs(output_dir, exist_ok=True)

    duration = config.get("simulation", {}).get("duration_seconds", 60)
    packet_loss_rate = config.get("simulation", {}).get("packet_loss_rate", 0.02)
    max_ttl = config.get("simulation", {}).get("max_ttl", 64)
    dpi = config.get("visualization", {}).get("dpi", 300)

    base_sim.SIM_TIME = duration
    base_sim.PACKET_LOSS_RATE = packet_loss_rate
    base_sim.MAX_TTL = max_ttl

    print(f"Output directory: {output_dir}")

    print()
    print("RUNNING NORMAL MODE SIMULATION...")
    print("-" * 70)
    net_normal = base_sim.run_simulation(mode="normal", sim_time=duration)

    print("Processing Normal Mode Results...")
    packets_normal = create_packet_from_network(net_normal, "normal")
    analyzer_normal = NetworkAnalyzer(packets_normal)

    base_sim.visualize_stats(
        net_normal,
        title_suffix="(Normal Mode)",
        save_path=os.path.join(output_dir, "stats_normal.png"),
    )

    visualizer = EnhancedVisualizations(analyzer_normal, output_dir, dpi=dpi)
    print("Generating Normal Mode Visualizations...")
    visualizer.plot_vlan_traffic(mode="normal")
    visualizer.plot_path_efficiency()
    render_campus_topology(net_normal, save_path=os.path.join(output_dir, "campus_topology.png"), dpi=dpi)

    output_cfg = config.get("output", {})
    if any(
        output_cfg.get(flag, False)
        for flag in ("export_csv", "export_json", "export_pickle")
    ):
        print("Exporting Normal Mode Data...")
        exporter_normal = DataExporter(packets_normal, {}, output_dir)
        if output_cfg.get("export_csv", True):
            exporter_normal.to_csv("simulation_results_normal.csv", mode="normal")
        if output_cfg.get("export_json", True):
            exporter_normal.to_json("simulation_summary_normal.json")
        if output_cfg.get("export_pickle", False):
            exporter_normal.to_pickle("simulation_data_normal.pkl")

    if output_cfg.get("generate_text_report", True):
        print("Generating Normal Mode Report...")
        report_gen = ReportGenerator(analyzer_normal, None, output_dir)
        report_gen.generate_text_report(analyzer_normal, mode="normal")

    normal_results = {
        "network": net_normal,
        "packets": packets_normal,
        "analyzer": analyzer_normal,
        "stats": analyzer_normal.get_overall_stats(),
    }

    print()
    print("RUNNING EXAM MODE SIMULATION...")
    print("-" * 70)
    net_exam = base_sim.run_simulation(mode="exam", sim_time=duration)

    print("Processing Exam Mode Results...")
    packets_exam = create_packet_from_network(net_exam, "exam")
    analyzer_exam = NetworkAnalyzer(packets_exam)

    base_sim.visualize_stats(
        net_exam,
        title_suffix="(Exam Mode)",
        save_path=os.path.join(output_dir, "stats_exam.png"),
    )

    visualizer_exam = EnhancedVisualizations(analyzer_exam, output_dir, dpi=dpi)
    print("Generating Exam Mode Visualizations...")
    visualizer_exam.plot_vlan_traffic(mode="exam")

    if any(
        output_cfg.get(flag, False)
        for flag in ("export_csv", "export_json", "export_pickle")
    ):
        print("Exporting Exam Mode Data...")
        exporter_exam = DataExporter(packets_exam, {}, output_dir)
        if output_cfg.get("export_csv", True):
            exporter_exam.to_csv("simulation_results_exam.csv", mode="exam")
        if output_cfg.get("export_json", True):
            exporter_exam.to_json("simulation_summary_exam.json")
        if output_cfg.get("export_pickle", False):
            exporter_exam.to_pickle("simulation_data_exam.pkl")

    if output_cfg.get("generate_text_report", True):
        print("Generating Exam Mode Report...")
        report_gen_exam = ReportGenerator(analyzer_exam, None, output_dir)
        report_gen_exam.generate_text_report(analyzer_exam, mode="exam")

    exam_results = {
        "network": net_exam,
        "packets": packets_exam,
        "analyzer": analyzer_exam,
        "stats": analyzer_exam.get_overall_stats(),
    }

    print()
    print("=" * 70)
    print("NORMAL vs EXAM MODE COMPARISON")
    print("=" * 70)

    if output_cfg.get("generate_comparison", True):
        print("Generating Comparison Report...")
        comparison_gen = ReportGenerator(analyzer_normal, analyzer_exam, output_dir)
        comparison_gen.generate_comparison_report()

    normal_stats = normal_results["stats"]
    exam_stats = exam_results["stats"]

    print(f"{'Metric':<30} {'Normal':>15} {'Exam':>15}")
    print("-" * 65)
    print(f"{'Total Packets':<30} {normal_stats.get('total_packets', 0):>15} {exam_stats.get('total_packets', 0):>15}")
    print(f"{'Delivery Rate (%)':<30} {normal_stats.get('delivery_rate', 0):>15.2f} {exam_stats.get('delivery_rate', 0):>15.2f}")
    print(f"{'Avg Delay (ms)':<30} {normal_stats.get('avg_delay_ms', 0):>15.2f} {exam_stats.get('avg_delay_ms', 0):>15.2f}")
    print(f"{'Avg Hops':<30} {normal_stats.get('avg_hops', 0):>15.2f} {exam_stats.get('avg_hops', 0):>15.2f}")
    print("=" * 65)
    print()
    print("SIMULATION COMPLETE")
    print(f"All outputs saved to: {output_dir}")

    return normal_results, exam_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified campus network simulation")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    args = parser.parse_args()

    seed = load_config(args.config).get("simulation", {}).get("random_seed", 42)
    random.seed(seed)

    try:
        run_complete_simulation(config_file=args.config)
        print("Unified simulation completed successfully!")
    except Exception:
        logger.exception("Simulation failed")
        raise


if __name__ == "__main__":
    main()
