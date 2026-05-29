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

fig, ax = plt.subplots(figsize=(8, 5))

folds = ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"]
values = [0.999999, 0.999998, 0.999999, 0.999998, 0.999999]

bars = ax.bar(folds, values, color="navy")

ax.axhline(y=1.0, color="orange", linewidth=1.5, linestyle="--")
ax.text(4.4, 1.00001, "Perfect AUC = 1.0", fontsize=9, color="orange", ha="right")

ax.set_ylabel("AUC Score")
ax.set_ylim(0.9998, 1.0001)

for bar, v in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.00001,
            f"{v:.4f}", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("chart_21_cross_validation.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
