import matplotlib.pyplot as plt
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

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

def make_donut(ax, values, colors, labels, center_text, center_sub=""):
    wedges, texts = ax.pie(
        values,
        colors=colors,
        labels=labels,
        labeldistance=1.15,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 2},
    )
    ax.text(0, 0, center_text, ha="center", va="center", fontsize=14, fontweight="bold")
    if center_sub:
        ax.text(0, -0.12, center_sub, ha="center", va="center", fontsize=9, color="grey")
    ax.set(aspect="equal")

make_donut(
    ax1,
    [70, 30],
    ["navy", "lightgrey"],
    ["Wholesale & B2B", "Other Spending"],
    "70% Wholesale",
)
ax1.set_title("Business Card", fontsize=11, pad=10)

make_donut(
    ax2,
    [4, 96],
    ["teal", "lightgrey"],
    ["Wholesale & B2B", "Other Spending"],
    "4% Wholesale",
)
ax2.set_title("Consumer Card", fontsize=11, pad=10)

plt.tight_layout()
plt.savefig("chart_03_expense_ratio.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
