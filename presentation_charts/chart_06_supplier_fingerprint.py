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

np.random.seed(42)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

# Left: Business Card Concentrated
np.random.seed(42)
x1 = np.random.uniform(1, 10, 5)
y1 = np.random.uniform(1, 10, 5)
sizes1 = [900, 700, 500, 80, 60]
ax1.scatter(x1, y1, s=sizes1, color="navy", alpha=0.7)
ax1.set_title("Business Card: Concentrated Suppliers", fontsize=11)
ax1.set_xticks([])
ax1.set_yticks([])
ax1.set_xlim(0, 11)
ax1.set_ylim(0, 11)
ax1.set_aspect("equal")

# Right: Consumer Card Spread
np.random.seed(42)
x2 = np.random.uniform(1, 10, 20)
y2 = np.random.uniform(1, 10, 20)
sizes2 = np.random.uniform(80, 120, 20)
ax2.scatter(x2, y2, s=sizes2, color="teal", alpha=0.7)
ax2.set_title("Consumer Card: Spread Across Many Merchants", fontsize=11)
ax2.set_xticks([])
ax2.set_yticks([])
ax2.set_xlim(0, 11)
ax2.set_ylim(0, 11)
ax2.set_aspect("equal")

plt.tight_layout()
plt.savefig("chart_06_supplier_fingerprint.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
