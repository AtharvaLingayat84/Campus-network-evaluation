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

    def plot_path_efficiency(self, mode: str = "normal") -> str:
        hop_counts = self.analyzer.get_hop_distribution("delivered")
        if not hop_counts:
            print("[!] No hop data for visualization")
            return ""

        hops = sorted(hop_counts.keys())
        counts = [hop_counts[h] for h in hops]

        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(hops, counts)

        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height,
                str(int(height)),
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_xlabel("Hop Count", fontsize=12, fontweight="bold")
        ax.set_ylabel("Packet Count", fontsize=12, fontweight="bold")
        ax.set_title("Routed Path Efficiency (Hop Count Distribution)", fontsize=14, fontweight="bold")
        ax.set_xticks(hops)
        ax.grid(axis="y", alpha=0.3)
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
