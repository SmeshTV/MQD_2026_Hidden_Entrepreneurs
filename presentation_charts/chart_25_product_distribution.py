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

fig, ax = plt.subplots(figsize=(8, 6))

values = [72, 24, 4]
colors = ["navy", "teal", "orange"]
labels = ["B2B Cashback Card\n72%", "Business Credit Card\n24%", "Working Capital Loan\n4%"]

wedges, texts = ax.pie(
    values,
    colors=colors,
    labels=labels,
    labeldistance=1.25,
    startangle=90,
    counterclock=False,
    wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 2},
)

ax.text(0, 0, "Top 100\nCards", ha="center", va="center", fontsize=14, fontweight="bold")
ax.set(aspect="equal")

plt.tight_layout()
plt.savefig("chart_25_product_distribution.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
