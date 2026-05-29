import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "none",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
    "axes.grid": False,
    "font.family": "DejaVu Sans",
    "font.size": 10,
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

x = np.arange(1, 9)

# Left: Business Card
biz_vals = np.array([1000, 50, 30, 800, 40, 20, 1200, 60])
biz_colors = ["navy" if v > 200 else "teal" for v in biz_vals]
ax1.bar(x, biz_vals, color=biz_colors)
ax1.set_title("Business Card: Large Restock + Small Top-Ups", fontsize=10)
ax1.set_xlabel("Transaction #")
ax1.set_ylabel("Amount (KZT thousands)")
ax1.set_xticks(x)

# Right: Consumer Card
con_vals = np.array([45, 62, 38, 71, 55, 48, 66, 42])
ax2.bar(x, con_vals, color="grey")
ax2.set_title("Consumer Card: No Inventory Structure", fontsize=10)
ax2.set_xlabel("Transaction #")
ax2.set_ylabel("Amount (KZT thousands)")
ax2.set_xticks(x)

plt.tight_layout()
plt.savefig("chart_09_inventory_pulse.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
