"""Visualization Module - Enhanced Charts
======================================

Generates detailed visualizations for network analysis using Matplotlib only.
"""

from __future__ import annotations

import os
from typing import Any

import matplotlib.pyplot as plt


class EnhancedVisualizations:
    def __init__(self, analyzer: Any, output_dir: str = "./output", dpi: int = 300):
        self.analyzer = analyzer
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)

    def plot_vlan_traffic(self, mode: str = "normal") -> str:
        vlan_stats = self.analyzer.get_vlan_statistics()
        if not vlan_stats:
            print("[!] No VLAN data for visualization")
            return ""

        vlan_stats = sorted(vlan_stats, key=lambda x: x["vlan"])
        vlans = [str(v["vlan"]) for v in vlan_stats]
        delivered = [v["packets_delivered"] for v in vlan_stats]
        lost = [v["packets_lost"] for v in vlan_stats]

        x = list(range(len(vlans)))
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(x, delivered, 0.6, label="Delivered", color="#2ecc71", alpha=0.8)
        ax.bar(x, lost, 0.6, bottom=delivered, label="Lost", color="#e74c3c", alpha=0.8)
        ax.set_xlabel("VLAN", fontsize=12, fontweight="bold")
        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title(f"Per-VLAN Traffic Volume ({mode.upper()} Mode)", fontsize=14, fontweight="bold")
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

    def plot_path_efficiency(self) -> str:
        hop_dist = self.analyzer.get_hop_distribution()
        if not hop_dist:
            return ""

        hops = list(hop_dist.keys())
        counts = list(hop_dist.values())
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(hops, counts, color="#3498db", alpha=0.8, edgecolor="black", linewidth=1)

        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(), f"{int(count)}", ha="center", va="bottom", fontweight="bold")

        ax.set_xlabel("Hop Count", fontsize=12, fontweight="bold")
        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title("Network Path Efficiency (Hop Count Distribution)", fontsize=14, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
        plt.xticks(hops)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, "path_efficiency.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()
        print(f"[OK] Visualization: {filepath}")
        return filepath

    def plot_communication_heatmap(self) -> str:
        comm_matrix = self.analyzer.get_device_pair_communication()
        if not comm_matrix:
            return ""

        # Top communicators by outgoing packet count
        top_devices = sorted(((src, sum(dests.values())) for src, dests in comm_matrix.items()), key=lambda x: x[1], reverse=True)[:15]
        top_names = [name for name, _ in top_devices]
        filtered = [name for name in top_names if name in comm_matrix]
        if not filtered:
            return ""

        matrix = [[comm_matrix.get(r, {}).get(c, 0) for c in filtered] for r in filtered]

        fig, ax = plt.subplots(figsize=(14, 12))
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
        ax.set_xticks(list(range(len(filtered))))
        ax.set_yticks(list(range(len(filtered))))
        ax.set_xticklabels(filtered, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(filtered, fontsize=8)
        ax.set_title("Device Pair Communication Matrix (Top 15 Communicators)", fontsize=14, fontweight="bold", pad=15)
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("Packet Count", rotation=270, labelpad=20)

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, "communication_heatmap.png")
        plt.savefig(filepath, dpi=self.dpi)
        plt.close()
        print(f"[OK] Visualization: {filepath}")
        return filepath
