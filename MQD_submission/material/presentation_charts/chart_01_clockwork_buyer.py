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

fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(1, 8)
business = [7, 7, 7, 7, 7, 7, 7]
consumer = [78, 13, 257, 22, 145, 8, 190]

ax.plot(x, business, color="navy", linewidth=2, marker="o", label="Business Card")
ax.plot(x, consumer, color="orange", linewidth=2, marker="s", label="Consumer Card")

ax.axhline(y=7, color="grey", linewidth=1, linestyle="--", alpha=0.6)

ax.set_xlabel("Purchase Number")
ax.set_ylabel("Days Between Purchases")
ax.set_xlim(0.5, 7.5)
ax.set_ylim(0, 280)
ax.legend(loc="upper right", frameon=False)

plt.savefig("chart_01_clockwork_buyer.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
