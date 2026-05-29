import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "none",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.spines.bottom": False,
    "axes.grid": False,
    "font.family": "DejaVu Sans",
    "font.size": 10,
})

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5))

def draw_sequence(ax, seq, label, color_map):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(-0.5, 0.5, label, ha="right", va="center", fontsize=9, color="dimgrey")
    n = len(seq)
    w = 0.85
    for i, s in enumerate(seq):
        x0 = i + 0.075
        rect = mpatches.FancyBboxPatch(
            (x0, 0.1), w, 0.8,
            boxstyle="round,pad=0.05",
            facecolor=color_map[s],
            edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(x0 + w / 2, 0.5, s, ha="center", va="center", fontsize=7, color="white", fontweight="bold")

seq1 = ["ONLINE", "POS", "ONLINE", "POS", "ONLINE", "POS", "ONLINE", "POS", "ONLINE", "POS"]
seq2 = ["ONLINE"] * 7 + ["POS"] * 3

color_map = {"ONLINE": "navy", "POS": "teal"}
draw_sequence(ax1, seq1, "Business Card (alternation rate = 0.70)", color_map)
draw_sequence(ax2, seq2, "Consumer Card (alternation rate = 0.15)", color_map)

plt.tight_layout()
plt.savefig("chart_11_channel_schizophrenia.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
