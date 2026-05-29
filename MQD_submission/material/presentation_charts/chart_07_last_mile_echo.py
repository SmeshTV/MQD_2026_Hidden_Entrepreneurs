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

fig, ax = plt.subplots(figsize=(10, 4))

# Draw horizontal timeline
ax.axhline(y=0, color="grey", linewidth=2, zorder=1)

events = [
    (0, "Wholesale\nPurchase", "navy", True),
    (2, "Logistics\nPayment", "teal", False),
    (15, "Wholesale\nPurchase", "navy", True),
    (18, "Logistics\nPayment", "teal", False),
    (30, "Wholesale\nPurchase", "navy", True),
    (32, "Logistics\nPayment", "teal", False),
]

for x, label, color, large in events:
    size = 120 if large else 80
    ax.scatter(x, 0, s=size, color=color, zorder=3, edgecolors="white", linewidth=1)
    ax.annotate(
        label,
        (x, 0),
        xytext=(x, -0.45),
        ha="center",
        va="top",
        fontsize=8,
        color="dimgrey",
    )

# Arrows between wholesale-logistics pairs
arrow_pairs = [(0, 2), (15, 18), (30, 32)]
for x1, x2 in arrow_pairs:
    mid = (x1 + x2) / 2
    ax.annotate(
        "",
        xy=(x2, 0.15),
        xytext=(x1, 0.15),
        arrowprops=dict(
            arrowstyle="->",
            color="orange",
            lw=1.5,
            connectionstyle="arc3,rad=0.3",
        ),
    )
    ax.text(mid, 0.3, "2\u20133 days", ha="center", va="bottom", fontsize=8, color="orange")

ax.set_xlim(-2, 36)
ax.set_ylim(-0.8, 0.8)
ax.axis("off")

plt.savefig("chart_07_last_mile_echo.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
