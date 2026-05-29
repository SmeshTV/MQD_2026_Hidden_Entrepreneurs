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

iters = np.arange(0, 151)
# Simulate learning curve: sharp rise then plateau
base = 0.9965 + 0.0034 * (1 - np.exp(-iters / 15))
auc = np.minimum(base, 0.999999)
auc[0] = 0.9965

ax.plot(iters, auc, color="navy", linewidth=2, label="Test AUC")

ax.axhline(y=1.0, color="grey", linewidth=1, linestyle="--", alpha=0.5)
ax.axvline(x=121, color="orange", linewidth=1.5, linestyle="--")
ax.annotate(
    "Early Stop (Iter 121)",
    xy=(121, 0.999999),
    xytext=(121, 0.9965),
    ha="center",
    fontsize=9,
    color="orange",
    arrowprops=dict(arrowstyle="->", color="orange", lw=1),
)

ax.set_xlabel("Iteration")
ax.set_ylabel("AUC")
ax.set_ylim(0.996, 1.0001)
ax.set_xlim(0, 150)
ax.legend(loc="lower right", frameon=False)

plt.tight_layout()
plt.savefig("chart_20_training_curve.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
