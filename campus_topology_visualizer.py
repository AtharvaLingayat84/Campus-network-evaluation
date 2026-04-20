import os
import matplotlib.pyplot as plt

PALETTE = {
    "bg": "#FFFFFF",
    "edge": "#94A3B8",
    "text": "#0F172A",
    "internet": "#DC2626",
    "core": "#F59E0B",
    "distribution": "#2563EB",
    "server": "#7C3AED",
    "access": "#16A34A",
}

def render_clean_topology(save_path="campus_topology.png", dpi=300):

    fig, ax = plt.subplots(figsize=(22, 12))
    ax.set_facecolor(PALETTE["bg"])
    fig.patch.set_facecolor(PALETTE["bg"])

    # ---------------------------
    # NODE POSITIONS (FIXED GRID)
    # ---------------------------

    positions = {
        "INTERNET": (0, 0),
        "ISR4331": (0, -1.5),
        "ASA": (0, -3),
        "CORE_RTR": (0, -4.5),
        "CORE_SW": (0, -6),

        "DIST_MAIN": (-4, -8),
        "DIST_C2": (6, -8),

        "EXAM": (-1.5, -8),
        "EMAIL": (0, -8),
        "CLOUD": (1.5, -8),
    }

    # MAIN CAMPUS (8 evenly spaced)
    main_x = [-9, -7, -5, -3, -1, 1, 3, 5]
    for i in range(8):
        positions[f"C1_{i+1}"] = (main_x[i], -11)

    # CAMPUS 2 (RIGHT SIDE ONLY)
    c2_x = [6, 8, 10, 12]
    for i in range(4):
        positions[f"C2_{i+1}"] = (c2_x[i], -11)

    # ---------------------------
    # ORTHOGONAL EDGE FUNCTION
    # ---------------------------

    def draw_orthogonal(a, b):
        x1, y1 = positions[a]
        x2, y2 = positions[b]

        mid_y = (y1 + y2) / 2

        ax.plot([x1, x1], [y1, mid_y], color=PALETTE["edge"], lw=1.2)
        ax.plot([x1, x2], [mid_y, mid_y], color=PALETTE["edge"], lw=1.2)
        ax.plot([x2, x2], [mid_y, y2], color=PALETTE["edge"], lw=1.2)

    # ---------------------------
    # EDGES (NO CROSSING)
    # ---------------------------

    core_chain = [
        ("INTERNET", "ISR4331"),
        ("ISR4331", "ASA"),
        ("ASA", "CORE_RTR"),
        ("CORE_RTR", "CORE_SW"),
    ]

    for a, b in core_chain:
        draw_orthogonal(a, b)

    draw_orthogonal("CORE_SW", "DIST_MAIN")
    draw_orthogonal("CORE_SW", "DIST_C2")

    draw_orthogonal("CORE_SW", "EXAM")
    draw_orthogonal("CORE_SW", "EMAIL")
    draw_orthogonal("CORE_SW", "CLOUD")

    for i in range(8):
        draw_orthogonal("DIST_MAIN", f"C1_{i+1}")

    for i in range(4):
        draw_orthogonal("DIST_C2", f"C2_{i+1}")

    # ---------------------------
    # NODE DRAW
    # ---------------------------

    def draw_node(name, group):
        x, y = positions[name]

        color_map = {
            "internet": PALETTE["internet"],
            "core": PALETTE["core"],
            "distribution": PALETTE["distribution"],
            "server": PALETTE["server"],
            "access": PALETTE["access"],
        }

        ax.scatter(
            x, y,
            s=1400,
            color=color_map[group],
            edgecolors="black",
            linewidths=1.2
        )

        ax.text(
            x, y - 0.6,
            name,
            ha="center",
            va="top",
            fontsize=9,
            color=PALETTE["text"],
            fontweight="bold"
        )

    # DRAW ALL
    for n, g in [
        ("INTERNET","internet"),("ISR4331","core"),("ASA","internet"),
        ("CORE_RTR","core"),("CORE_SW","core"),
        ("DIST_MAIN","distribution"),("DIST_C2","distribution"),
        ("EXAM","server"),("EMAIL","server"),("CLOUD","server")
    ]:
        draw_node(n, g)

    for i in range(8):
        draw_node(f"C1_{i+1}", "access")

    for i in range(4):
        draw_node(f"C2_{i+1}", "access")

    ax.set_title("Campus Network Topology", fontsize=18, fontweight="bold")

    ax.set_xlim(-12, 14)
    ax.set_ylim(-13.5, 1)

    ax.axis("off")

    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi)
    plt.close()

    return save_path