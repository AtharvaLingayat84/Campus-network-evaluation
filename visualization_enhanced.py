"""
Visualization Module - Enhanced Charts
======================================
Generates 8 new detailed visualizations for network analysis:
1. Per-VLAN Traffic Volume
2. Device Type Performance
3. Traffic Type Distribution
4. Delay Distribution by VLAN
5. Packet Loss Root Cause Breakdown
6. Network Path Efficiency (Hop Count Distribution)
7. Temporal Analysis (Cumulative Delivery Over Time)
8. Device Pair Communication Heatmap
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import os
from typing import Any, Dict, List, Optional


class EnhancedVisualizations:
    """Generate enhanced visualizations from network analyzer results."""

    def __init__(self, analyzer: Any, output_dir: str = "./output", dpi: int = 300):
        """
        Initialize visualization generator.

        Args:
            analyzer: NetworkAnalyzer instance with analysis results
            output_dir: Directory to save visualizations
            dpi: Resolution for saved images
        """
        self.analyzer = analyzer
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)

    def plot_vlan_traffic(self, mode: str = "normal") -> str:
        """
        Chart 1: Per-VLAN Traffic Volume
        Stacked bar chart showing packet count per VLAN.
        """
        vlan_stats = self.analyzer.get_vlan_statistics()

        if len(vlan_stats) == 0:
            print("[!] No VLAN data for visualization")
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))

        vlans = vlan_stats["vlan"].astype(str)
        packets = vlan_stats["packets_total"]
        delivered = vlan_stats["packets_delivered"]
        lost = vlan_stats["packets_lost"]

        x = np.arange(len(vlans))
        width = 0.6

        ax.bar(x, delivered, width, label="Delivered", color="#2ecc71", alpha=0.8)
        ax.bar(
            x, lost, width, bottom=delivered, label="Lost", color="#e74c3c", alpha=0.8
        )

        ax.set_xlabel("VLAN", fontsize=12, fontweight="bold")
        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title(
            f"Per-VLAN Traffic Volume ({mode.upper()} Mode)",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(vlans, rotation=45)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        filepath = os.path.join(self.output_dir, f"vlan_traffic_{mode}.png")
        plt.tight_layout()
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_device_performance(self) -> str:
        """
        Chart 2: Device Type Performance
        Grouped bar chart comparing delivery rates across device types.
        """
        df = self.analyzer.df

        if len(df) == 0:
            return ""

        # Group by device type (source)
        device_types = {}
        for device_type in df["src_type"].unique():
            type_packets = df[df["src_type"] == device_type]
            delivered = len(type_packets[type_packets["status"] == "delivered"])
            total = len(type_packets)
            delivery_rate = (delivered / total * 100) if total > 0 else 0
            device_types[device_type] = {
                "delivery_rate": delivery_rate,
                "packets": total,
            }

        if not device_types:
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))

        types = list(device_types.keys())
        rates = [device_types[t]["delivery_rate"] for t in types]

        colors = [
            "#2ecc71" if r > 95 else "#f39c12" if r > 85 else "#e74c3c" for r in rates
        ]
        bars = ax.bar(
            types, rates, color=colors, alpha=0.8, edgecolor="black", linewidth=1.5
        )

        # Add value labels on bars
        for bar, rate in zip(bars, rates):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{rate:.1f}%",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_ylabel("Delivery Rate (%)", fontsize=12, fontweight="bold")
        ax.set_title("Device Type Performance", fontsize=14, fontweight="bold")
        ax.set_ylim([0, 105])
        ax.grid(axis="y", alpha=0.3)
        ax.axhline(
            y=95,
            color="gray",
            linestyle="--",
            linewidth=1,
            alpha=0.7,
            label="95% Target",
        )
        ax.legend()

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, "device_performance.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_traffic_distribution(self) -> str:
        """
        Chart 3: Traffic Type Distribution
        Pie chart showing percentage breakdown by destination.
        """
        traffic_stats = self.analyzer.get_traffic_type_statistics()

        if not traffic_stats:
            return ""

        labels = list(traffic_stats.keys())
        sizes = [traffic_stats[t]["packets"] for t in labels]

        # Filter out zero-packet destinations
        filtered_labels = [l for l, s in zip(labels, sizes) if s > 0]
        filtered_sizes = [s for s in sizes if s > 0]

        if not filtered_sizes:
            return ""

        fig, ax = plt.subplots(figsize=(10, 8))

        colors = ["#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]
        wedges, texts, autotexts = ax.pie(
            filtered_sizes,
            labels=filtered_labels,
            autopct="%1.1f%%",
            colors=colors[: len(filtered_sizes)],
            startangle=90,
            textprops={"fontsize": 11},
        )

        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")

        ax.set_title(
            "Traffic Type Distribution", fontsize=14, fontweight="bold", pad=20
        )

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, "traffic_distribution.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_delay_distribution(self, mode: str = "normal") -> str:
        """
        Chart 4: Delay Distribution by VLAN
        Box plots showing delay statistics per VLAN.
        """
        df = self.analyzer.df

        if len(df) == 0:
            return ""

        # Get all VLANs
        all_vlans = sorted(set(df["src_vlan"].dropna()) | set(df["dst_vlan"].dropna()))

        delay_data = []
        vlan_labels = []

        for vlan in all_vlans:
            if pd.isna(vlan):
                continue
            vlan_packets = df[(df["src_vlan"] == vlan) | (df["dst_vlan"] == vlan)]
            if len(vlan_packets) > 0:
                delay_data.append(vlan_packets["delay_ms"].dropna().values)
                vlan_labels.append(f"VLAN {int(vlan)}")

        if not delay_data:
            return ""

        fig, ax = plt.subplots(figsize=(14, 6))

        bp = ax.boxplot(delay_data, labels=vlan_labels, patch_artist=True)

        # Color the boxes
        for patch in bp["boxes"]:
            patch.set_facecolor("#3498db")
            patch.set_alpha(0.7)

        ax.set_ylabel("Delay (ms)", fontsize=12, fontweight="bold")
        ax.set_title(
            f"Delay Distribution by VLAN ({mode.upper()} Mode)",
            fontsize=14,
            fontweight="bold",
        )
        ax.grid(axis="y", alpha=0.3)

        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, f"delay_distribution_{mode}.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_loss_breakdown(self, mode: str = "normal") -> str:
        """
        Chart 5: Packet Loss Root Cause Breakdown
        Stacked bar chart showing loss reasons.
        """
        loss_breakdown = self.analyzer.get_loss_breakdown()

        if not loss_breakdown:
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))

        reasons = [
            "delivered",
            "link_loss",
            "ttl_exceeded",
            "acl_blocked",
            "timeout",
            "other",
        ]
        labels = [
            "Delivered",
            "Link Loss",
            "TTL Exceeded",
            "ACL Blocked",
            "Timeout",
            "Other",
        ]
        colors = ["#2ecc71", "#e74c3c", "#f39c12", "#9b59b6", "#e67e22", "#95a5a6"]

        counts = [loss_breakdown.get(r, 0) for r in reasons]

        x = np.arange(1)
        width = 0.5
        bottom = 0

        for count, label, color in zip(counts, labels, colors):
            ax.bar(x, count, width, bottom=bottom, label=label, color=color, alpha=0.8)

            # Add count label
            if count > 0:
                ax.text(
                    0,
                    bottom + count / 2,
                    str(int(count)),
                    ha="center",
                    va="center",
                    fontweight="bold",
                    color="white",
                    fontsize=10,
                )

            bottom += count

        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title(
            f"Packet Loss Root Cause Breakdown ({mode.upper()} Mode)",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xticks([])
        ax.legend(loc="upper right")
        ax.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"loss_breakdown_{mode}.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_path_efficiency(self) -> str:
        """
        Chart 6: Network Path Efficiency (Hop Count Distribution)
        Histogram showing actual vs. expected hop counts.
        """
        hop_dist = self.analyzer.get_hop_distribution()

        if not hop_dist:
            return ""

        fig, ax = plt.subplots(figsize=(12, 6))

        hops = list(hop_dist.keys())
        counts = list(hop_dist.values())

        bars = ax.bar(
            hops, counts, color="#3498db", alpha=0.8, edgecolor="black", linewidth=1
        )

        # Add count labels on bars
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(count)}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_xlabel("Hop Count", fontsize=12, fontweight="bold")
        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title(
            "Network Path Efficiency (Hop Count Distribution)",
            fontsize=14,
            fontweight="bold",
        )
        ax.grid(axis="y", alpha=0.3)

        plt.xticks(hops)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, "path_efficiency.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_temporal_analysis(self) -> str:
        """
        Chart 7: Temporal Analysis
        Line chart showing cumulative packets delivered over 60-second timeline.
        """
        df_normal = self.analyzer.df

        if len(df_normal) == 0:
            return ""

        # Get delivered packets sorted by timestamp
        delivered = df_normal[df_normal["status"] == "delivered"].copy()
        delivered = delivered.sort_values("timestamp")

        if len(delivered) == 0:
            return ""

        # Calculate cumulative delivery
        cumulative = np.arange(1, len(delivered) + 1)
        timestamps = delivered["timestamp"].values

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(
            timestamps,
            cumulative,
            linewidth=2.5,
            color="#2ecc71",
            marker="",
            label="Cumulative Delivery",
        )
        ax.fill_between(timestamps, cumulative, alpha=0.3, color="#2ecc71")

        ax.set_xlabel("Time (seconds)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Cumulative Packets Delivered", fontsize=12, fontweight="bold")
        ax.set_title(
            "Temporal Analysis: Cumulative Packet Delivery Over Time",
            fontsize=14,
            fontweight="bold",
        )
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, "temporal_analysis.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_communication_heatmap(self) -> str:
        """
        Chart 8: Communication Heatmap (Optional)
        Dense matrix heatmap showing packet volume between device pairs.
        Note: May be slow with 250+ devices, only showing top communicators.
        """
        comm_matrix = self.analyzer.get_device_pair_communication()

        if not comm_matrix:
            return ""

        # Convert to DataFrame
        df = pd.DataFrame(comm_matrix).fillna(0)

        # Limit to top communicators to avoid huge heatmap
        top_devices = []
        for src, dests in comm_matrix.items():
            total_out = sum(dests.values())
            top_devices.append((src, total_out))

        top_devices = sorted(top_devices, key=lambda x: x[1], reverse=True)[:15]
        top_device_names = [d[0] for d in top_devices]

        # Filter matrix to top devices
        filtered_matrix = df.loc[
            df.index.isin(top_device_names), df.columns.isin(top_device_names)
        ]

        if len(filtered_matrix) == 0:
            return ""

        fig, ax = plt.subplots(figsize=(14, 12))

        im = ax.imshow(filtered_matrix.values, cmap="YlOrRd", aspect="auto")

        ax.set_xticks(np.arange(len(filtered_matrix.columns)))
        ax.set_yticks(np.arange(len(filtered_matrix.index)))
        ax.set_xticklabels(filtered_matrix.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(filtered_matrix.index, fontsize=8)

        ax.set_title(
            "Device Pair Communication Matrix (Top 15 Communicators)",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Packet Count", rotation=270, labelpad=20)

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, "communication_heatmap.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()

        print(f"[OK] Visualization: {filepath}")
        return filepath
