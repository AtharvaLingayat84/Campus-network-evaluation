"""Professional campus topology diagram renderer.

Creates a clean, hierarchical architecture diagram with orthogonal links,
consistent color coding, and grouped VLAN access nodes.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


PALETTE = {
    "bg": "#F8FAFC",
    "panel": "#FFFFFF",
    "panel_border": "#CBD5E1",
    "text": "#0F172A",
    "muted": "#475569",
    "edge": "#334155",
    "internet": "#D32F2F",
    "core": "#F59E0B",
    "distribution": "#1565C0",
    "server": "#6A1B9A",
    "access": "#2E7D32",
    "layer_line": "#E2E8F0",
}


def _floor_label(campus: str, floor: int, vlan: int) -> str:
    return f"{campus}_F{floor}\nVLAN {vlan}"


def _build_nodes(network) -> Dict[str, Dict[str, str]]:
    nodes: Dict[str, Dict[str, str]] = {
        "INTERNET": {"label": "INTERNET", "layer": 0, "group": "internet"},
        "ISR4331": {"label": "ISR4331", "layer": 1, "group": "core"},
        "ASA_FW": {"label": "ASA_FW", "layer": 2, "group": "internet"},
        "CORE_RTR": {"label": "CORE_RTR", "layer": 3, "group": "core"},
        "CORE_SW": {"label": "CORE_SW", "layer": 4, "group": "core"},
    }

    for campus_name, campus_cfg in network.CAMPUSES.items():
        dist_name = f"DIST_{campus_name}"
        nodes[dist_name] = {"label": dist_name, "layer": 5, "group": "distribution"}

        for idx, vlan in enumerate(campus_cfg["vlans"], start=1):
            floor_name = f"{campus_name}_F{idx}"
            nodes[floor_name] = {
                "label": _floor_label(campus_name, idx, vlan),
                "layer": 6,
                "group": "access",
            }

    for server_name in network.SERVERS_INFO:
        nodes[server_name] = {"label": server_name, "layer": 5, "group": "server"}

    return nodes


def _orthogonal_path(x1: float, y1: float, x2: float, y2: float):
    mid_y = (y1 + y2) / 2
    return [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]


def render_campus_topology(network, save_path: str = "campus_topology.png", dpi: int = 300) -> str:
    nodes = _build_nodes(network)

    # Fixed, symmetrical layer positions with generous vertical spacing.
    positions: Dict[str, Tuple[float, float]] = {
        "INTERNET": (0.0, 0.0),
        "ISR4331": (0.0, -2.0),
        "ASA_FW": (0.0, -4.0),
        "CORE_RTR": (0.0, -6.0),
        "CORE_SW": (0.0, -8.0),
    }

    positions["DIST_MAIN"] = (-3.4, -10.4)
    positions["DIST_CAMPUS2"] = (3.4, -10.4)
    positions["EXAM_SERVER"] = (-1.3, -10.4)
    positions["EMAIL_SERVER"] = (0.0, -10.4)
    positions["CLOUD_SERVER"] = (1.3, -10.4)

    main_xs = [-7.2, -5.2, -3.2, -1.2, 1.2, 3.2, 5.2, 7.2]
    campus2_xs = [-5.0, -1.7, 1.7, 5.0]

    for idx, x in enumerate(main_xs, start=1):
        positions[f"MAIN_F{idx}"] = (x, -13.0)
    for idx, x in enumerate(campus2_xs, start=1):
        positions[f"CAMPUS2_F{idx}"] = (x, -13.0)

    edges = [
        ("INTERNET", "ISR4331"),
        ("ISR4331", "ASA_FW"),
        ("ASA_FW", "CORE_RTR"),
        ("CORE_RTR", "CORE_SW"),
        ("CORE_SW", "DIST_MAIN"),
        ("CORE_SW", "DIST_CAMPUS2"),
        ("CORE_SW", "EXAM_SERVER"),
        ("CORE_SW", "EMAIL_SERVER"),
        ("CORE_SW", "CLOUD_SERVER"),
    ]

    for idx in range(1, 9):
        edges.append(("DIST_MAIN", f"MAIN_F{idx}"))
    for idx in range(1, 5):
        edges.append(("DIST_CAMPUS2", f"CAMPUS2_F{idx}"))

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig, ax = plt.subplots(figsize=(24, 14))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["bg"])

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (-9.6, -14.2), 19.2, 15.5,
            boxstyle="round,pad=0.4,rounding_size=0.2",
            facecolor=PALETTE["panel"],
            edgecolor=PALETTE["panel_border"],
            linewidth=1.4,
            zorder=0,
        )
    )

    # Layer labels
    layer_titles = {
        0: "Internet",
        1: "Edge / Security",
        2: "Firewall",
        3: "Core Router",
        4: "Core Switch",
        5: "Distribution",
        6: "Access",
    }
    layer_y = {0: 0.0, 1: -2.0, 2: -4.0, 3: -6.0, 4: -8.0, 5: -10.4, 6: -13.0}
    for layer, title in layer_titles.items():
        ax.text(-9.8, layer_y[layer], title, ha="right", va="center", fontsize=10.5, fontweight="bold", color=PALETTE["muted"])
        ax.axhline(layer_y[layer], color=PALETTE["layer_line"], lw=1.0, zorder=0)

    # Orthogonal connectors, drawn behind nodes.
    for src, dst in edges:
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        path = _orthogonal_path(x1, y1, x2, y2)
        ax.plot([p[0] for p in path], [p[1] for p in path], color=PALETTE["edge"], lw=2.0, alpha=0.35, zorder=1)

    # Draw circular nodes only, with labels outside and below each node.
    style_map = {
        "internet": PALETTE["internet"],
        "core": PALETTE["core"],
        "distribution": PALETTE["distribution"],
        "server": PALETTE["server"],
        "access": PALETTE["access"],
    }

    node_size = 1800
    circle_radius = 0.52
    label_offset = 0.72

    for name, data in nodes.items():
        x, y = positions[name]
        ax.scatter(
            [x],
            [y],
            s=node_size,
            c=style_map[data["group"]],
            marker="o",
            edgecolors="white",
            linewidths=1.8,
            zorder=3,
        )
        ax.text(
            x,
            y - label_offset,
            data["label"],
            ha="center",
            va="top",
            fontsize=10 if data["layer"] < 6 else 9,
            fontweight="bold",
            color=PALETTE["text"],
            zorder=4,
            clip_on=False,
        )

    legend_items = [
        mpatches.Patch(color=PALETTE["internet"], label="Internet / Firewall"),
        mpatches.Patch(color=PALETTE["core"], label="Core Devices"),
        mpatches.Patch(color=PALETTE["distribution"], label="Distribution"),
        mpatches.Patch(color=PALETTE["server"], label="Servers"),
        mpatches.Patch(color=PALETTE["access"], label="End-user VLANs"),
    ]
    ax.legend(handles=legend_items, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=10)

    ax.text(
        0.5,
        1.01,
        "Hierarchical campus architecture with grouped VLAN access layer",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=11,
        color=PALETTE["muted"],
    )
    ax.set_title("Campus Network Topology", fontsize=22, fontweight="bold", color=PALETTE["text"], pad=16)
    ax.set_xlim(-10.2, 10.2)
    ax.set_ylim(-15.1, 1.1)
    ax.axis("off")
    fig.subplots_adjust(left=0.06, right=0.82, top=0.93, bottom=0.07)
    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return save_path
