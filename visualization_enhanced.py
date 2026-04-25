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
        hop_sets = self.analyzer.get_hop_distributions()
        if not hop_sets:
            print("[!] No hop data for visualization")
            return ""

        delivered = hop_sets.get("delivered", {})
        dropped = hop_sets.get("dropped", {})
        acl_blocked = hop_sets.get("acl_blocked", {})

        all_hops = sorted({*delivered.keys(), *dropped.keys(), *acl_blocked.keys()})
        if not all_hops:
            print("[!] Hop distributions are empty")
            return ""

        def _normalize(series):
            total = sum(series.values())
            return [round((series.get(h, 0) / total) * 100, 2) if total else 0 for h in all_hops]

        delivered_pct = _normalize(delivered)
        dropped_pct = _normalize(dropped)
        acl_pct = _normalize(acl_blocked)

        width = 0.25
        x = list(range(len(all_hops)))

        fig, ax = plt.subplots(figsize=(12, 6))
        b1 = ax.bar([i - width for i in x], delivered_pct, width, label="Delivered", color="#2ecc71", alpha=0.85)
        b2 = ax.bar(x, dropped_pct, width, label="Dropped (loss + TTL)", color="#e74c3c", alpha=0.85)
        b3 = ax.bar([i + width for i in x], acl_pct, width, label="ACL Blocked", color="#8e44ad", alpha=0.85)

        for bars, series in ((b1, delivered), (b2, dropped), (b3, acl_blocked)):
            for bar, hop in zip(bars, all_hops):
                count = series.get(hop, 0)
                if count:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        bar.get_height(),
                        f"{count}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        fontweight="bold",
                    )

        ax.set_xlabel("Hop Count", fontsize=12, fontweight="bold")
        ax.set_ylabel("Share of Packets (%)", fontsize=12, fontweight="bold")
        ax.set_title(f"Routed Hop Distribution ({mode.upper()} Mode)", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([str(h) for h in all_hops])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(0, max(delivered_pct + dropped_pct + acl_pct + [0]) * 1.25 + 1)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, f"path_efficiency_{mode}.png")
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
