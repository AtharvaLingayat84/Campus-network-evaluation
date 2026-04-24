"""
Report Generator Module
=======================
Generates human-readable evaluation reports and machine-readable comparison
files from simulation analysis results.

Classes:
    ReportGenerator - Generates text and JSON reports from analysis data
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ReportGenerator:
    """
    Generates comprehensive reports from network simulation analysis.

    Attributes:
        analyzer_normal: NetworkAnalyzer instance for normal mode
        analyzer_exam: NetworkAnalyzer instance for exam mode
        output_dir: Directory for saving reports
    """

    def __init__(
        self,
        analyzer_normal: Any = None,
        analyzer_exam: Any = None,
        output_dir: str = "./output",
    ):
        """
        Initialize ReportGenerator with analysis data.

        Args:
            analyzer_normal: NetworkAnalyzer for normal mode results
            analyzer_exam: NetworkAnalyzer for exam mode results (optional)
            output_dir: Directory for saving reports
        """
        self.analyzer_normal = analyzer_normal
        self.analyzer_exam = analyzer_exam
        self.output_dir = output_dir

        os.makedirs(output_dir, exist_ok=True)

    def generate_text_report(
        self, analyzer: Any, mode: str = "normal", filename: Optional[str] = None
    ) -> str:
        """
        Generate human-readable evaluation report.

        Args:
            analyzer: NetworkAnalyzer instance
            mode: Simulation mode ("normal" or "exam")
            filename: Output filename (if None, uses default)

        Returns:
            Path to generated report file
        """
        if filename is None:
            filename = f"network_evaluation_report_{mode}.txt"

        filepath = os.path.join(self.output_dir, filename)

        # Get analysis data
        overall = analyzer.get_overall_stats()
        vlan_stats = analyzer.get_vlan_statistics()
        traffic_stats = analyzer.get_traffic_type_statistics()
        loss_breakdown = analyzer.get_loss_breakdown()

        # Generate report content
        report = self._generate_report_content(
            overall, vlan_stats, traffic_stats, loss_breakdown, mode
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[OK] Text report: {filepath}")
        return filepath

    def _generate_report_content(
        self,
        overall: Dict[str, Any],
        vlan_stats,
        traffic_stats: Dict[str, Any],
        loss_breakdown: Dict[str, Any],
        mode: str,
    ) -> str:
        """Generate the actual report text."""
        mode_title = "NORMAL MODE" if mode == "normal" else "EXAM MODE"

        report = f"""
{"=" * 80}
CAMPUS NETWORK SIMULATION EVALUATION REPORT
{"=" * 80}

Mode: {mode_title.upper()}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{"=" * 80}
EXECUTIVE SUMMARY
{"=" * 80}

The simulation evaluated network performance across a 2-campus enterprise topology
with 250+ network devices over a 60-second period. This report presents key
findings and detailed performance metrics.

{"=" * 80}
KEY FINDINGS
{"=" * 80}

• Total Packets Processed: {overall.get("total_packets", 0):,}
  Delivered: {overall.get("delivered_packets", 0):,} ({overall.get("delivery_rate", 0)}%)
  Dropped: {overall.get("dropped_packets", 0):,}

• Network Latency
  Average Delay: {overall.get("avg_delay_ms", 0):.2f} ms
  Range: {overall.get("min_delay_ms", 0):.2f} - {overall.get("max_delay_ms", 0):.2f} ms
  Std Dev: {overall.get("std_delay_ms", 0):.2f} ms

• Path Efficiency
  Average Hop Count: {overall.get("avg_hops", 0):.2f}
  Range: {overall.get("min_hops", 0)} - {overall.get("max_hops", 0)} hops

{"=" * 80}
DETAILED METRICS
{"=" * 80}

OVERALL STATISTICS:
"""
        # Add overall stats table
        report += f"""
  Total Packets:        {overall.get("total_packets", 0):>10}
  Delivered:            {overall.get("delivered_packets", 0):>10} ({overall.get("delivery_rate", 0):>5.2f}%)
  Dropped (loss + TTL):  {overall.get("dropped_packets", 0) - overall.get("acl_blocked_packets", 0):>10}
  ACL Blocked (policy action): {overall.get("acl_blocked_packets", 0):>10}
  
  Avg Delay:            {overall.get("avg_delay_ms", 0):>10.2f} ms
  Avg Hop Count:        {overall.get("avg_hops", 0):>10.2f}

  Note: Delay and hop metrics are based on routed paths only; ACL-blocked packets are excluded.

"""

        # Add VLAN statistics table
        if len(vlan_stats) > 0:
            report += """
PER-VLAN PERFORMANCE:
─────────────────────────────────────────────────────────────────────────────
"""
            report += f"{'VLAN':<8} {'Packets':<12} {'Delivery%':<12} {'Avg Delay':<12} {'Avg Hops':<12}\n"
            report += "─" * 79 + "\n"

            for row in vlan_stats:
                vlan = int(row["vlan"])
                packets = row["packets_total"]
                delivery = row["delivery_rate"]
                delay = row["avg_delay_ms"]
                hops = row["avg_hops"]
                report += f"{vlan:<8} {packets:<12} {delivery:<11.2f}% {delay:<11.2f} ms {hops:<12.2f}\n"
                if row.get("acl_blocked", 0):
                    report += f"{'':<8} {'ACL blocked':<12} {row.get('acl_blocked', 0):<12} {'':<12} {'':<12}\n"

        # Add traffic type statistics
        if traffic_stats:
            report += """

TRAFFIC TYPE ANALYSIS:
─────────────────────────────────────────────────────────────────────────────
"""
            report += f"{'Destination':<25} {'Packets':<12} {'Delivery%':<12} {'% of Total':<12}\n"
            report += "─" * 79 + "\n"

            for dest, stats in sorted(traffic_stats.items()):
                packets = stats.get("packets", 0)
                delivery = stats.get("delivery_rate", 0)
                percentage = stats.get("percentage", 0)
                report += f"{dest:<25} {packets:<12} {delivery:<11.2f}% {percentage:<11.2f}%\n"

        # Add loss breakdown
        if loss_breakdown:
            report += """

PACKET LOSS BREAKDOWN:
─────────────────────────────────────────────────────────────────────────────
"""
            report += f"{'Reason':<25} {'Count':<12} {'Percentage':<12}\n"
            report += "─" * 79 + "\n"

            reasons = {
                "delivered": "Delivered",
                "dropped_loss": "Dropped Loss (link/timeout/other)",
                "dropped_ttl": "Dropped TTL",
                "acl_blocked": "ACL Blocked (policy action)",
            }

            for key, label in reasons.items():
                count = loss_breakdown.get(key, 0)
                percentage = loss_breakdown.get("percentages", {}).get(key, 0)
                report += f"{label:<25} {count:<12} {percentage:<11.2f}%\n"

        # Add observations
        report += f"""

{"=" * 80}
OBSERVATIONS
{"=" * 80}

• Network Delivery Performance:
  The network achieved a {overall.get("delivery_rate", 0):.1f}% delivery rate, indicating
  {"good stability and capacity" if overall.get("delivery_rate", 0) > 95 else "room for optimization"}.

• Latency Profile:
  Average packet delay of {overall.get("avg_delay_ms", 0):.2f} ms with variation of
  {overall.get("std_delay_ms", 0):.2f} ms suggests {"consistent" if overall.get("std_delay_ms", 0) < 5 else "variable"} network conditions.

• Path Efficiency:
  Average hop count of {overall.get("avg_hops", 0):.2f} on routed paths shows routing is
  {"efficient" if overall.get("avg_hops", 0) < 5 else "suboptimal for current topology"}.

• Primary Loss Factor:
  {"Link congestion" if loss_breakdown.get("dropped_loss", 0) > loss_breakdown.get("dropped_ttl", 0) else "TTL exhaustion" if loss_breakdown.get("dropped_ttl", 0) > 0 else "No significant loss"} 
  is the primary packet loss mechanism.

• ACL Impact:
  {loss_breakdown.get("acl_blocked", 0)} packets were ACL blocked as a policy action and are reported separately from loss.

{"=" * 80}
RECOMMENDATIONS
{"=" * 80}

• For Capacity Planning:
  Monitor Exam Server load - it handles significant traffic volume.
  Consider implementing per-flow admission control.

• For Redundancy:
  Core-to-Distribution links are critical - implement redundancy if not present.
  Consider dual paths for inter-campus connectivity.

• For Performance:
  QoS prioritization for exam traffic may reduce latency variance.
  Review VLAN segmentation for optimal load distribution.

• For Network Design:
  Consider hierarchical traffic engineering to reduce hop counts.
  Implement link aggregation on heavily loaded uplinks.

{"=" * 80}
END OF REPORT
{"=" * 80}
"""
        return report

    def generate_comparison_report(
        self, filename: str = "simulation_comparison.json"
    ) -> str:
        """
        Generate comparison report between normal and exam modes.

        Args:
            filename: Output filename

        Returns:
            Path to generated comparison file
        """
        filepath = os.path.join(self.output_dir, filename)

        normal_stats = (
            self.analyzer_normal.get_overall_stats() if self.analyzer_normal else {}
        )
        exam_stats = (
            self.analyzer_exam.get_overall_stats() if self.analyzer_exam else {}
        )

        # Calculate deltas
        deltas = {}
        if normal_stats and exam_stats:
            deltas = {
                "packet_volume_change_percent": self._calc_change_percent(
                    normal_stats.get("total_packets", 0),
                    exam_stats.get("total_packets", 0),
                ),
                "delivery_rate_change_percent": exam_stats.get("delivery_rate", 0)
                - normal_stats.get("delivery_rate", 0),
                "delay_change_ms": exam_stats.get("avg_delay_ms", 0)
                - normal_stats.get("avg_delay_ms", 0),
                "hop_count_change": exam_stats.get("avg_hops", 0)
                - normal_stats.get("avg_hops", 0),
            }

        comparison_data = {
            "timestamp": datetime.now().isoformat(),
            "normal_mode": normal_stats,
            "exam_mode": exam_stats,
            "deltas": deltas,
            "analysis": self._generate_comparison_analysis(
                normal_stats, exam_stats, deltas
            ),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(comparison_data, f, indent=2)

        print(f"[OK] Comparison report: {filepath}")
        return filepath

    def _calc_change_percent(self, before: float, after: float) -> float:
        """Calculate percentage change."""
        if before == 0:
            return 0
        return round(((after - before) / before) * 100, 2)

    def _generate_comparison_analysis(
        self, normal: Dict, exam: Dict, deltas: Dict
    ) -> Dict[str, str]:
        """Generate human-readable comparison analysis."""
        analysis = {
            "summary": "",
            "packet_volume": "",
            "delivery_rate": "",
            "latency": "",
        }

        if not normal or not exam:
            return analysis

        # Packet volume analysis
        packet_change = deltas.get("packet_volume_change_percent", 0)
        if packet_change < -20:
            analysis["packet_volume"] = (
                f"Exam mode significantly reduces traffic by {abs(packet_change):.1f}% - restriction to 2 servers"
            )
        elif packet_change < 0:
            analysis["packet_volume"] = (
                f"Exam mode reduces traffic by {abs(packet_change):.1f}%"
            )
        else:
            analysis["packet_volume"] = "Traffic volume similar between modes"

        # Delivery rate analysis
        delivery_change = deltas.get("delivery_rate_change_percent", 0)
        if delivery_change > 2:
            analysis["delivery_rate"] = (
                f"Delivery improves by {delivery_change:.1f}% in exam mode - likely due to reduced congestion"
            )
        elif delivery_change < -2:
            analysis["delivery_rate"] = (
                f"Delivery degrades by {abs(delivery_change):.1f}% in exam mode - concentration on fewer servers"
            )
        else:
            analysis["delivery_rate"] = "Delivery rate stable between modes"

        # Latency analysis
        delay_change = deltas.get("delay_change_ms", 0)
        if delay_change > 5:
            analysis["latency"] = (
                f"Latency increases by {delay_change:.1f} ms in exam mode - longer paths to concentrated servers"
            )
        elif delay_change < -5:
            analysis["latency"] = (
                f"Latency improves by {abs(delay_change):.1f} ms in exam mode"
            )
        else:
            analysis["latency"] = "Latency unchanged between modes"

        # Generate summary
        analysis["summary"] = (
            f"Exam mode produces {'lower' if packet_change < 0 else 'similar'} traffic volumes with "
            f"{'improved' if delivery_change > 0 else 'similar'} delivery rates and "
            f"{'increased' if delay_change > 0 else 'reduced'} latency."
        )

        return analysis
