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

fig, ax = plt.subplots(figsize=(7, 6))

data = np.array([[15996, 4], [5, 4995]])
labels = np.array([["TN", "FP"], ["FN", "TP"]])

ax.imshow(data, cmap="Blues", aspect="auto")

ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(["Consumer", "Business"])
ax.set_yticklabels(["Consumer", "Business"])
ax.set_xlabel("Predicted", fontsize=10)
ax.set_ylabel("Actual", fontsize=10)
ax.xaxis.set_label_position("top")
ax.xaxis.tick_top()

for i in range(2):
    for j in range(2):
        val = data[i, j]
        lbl = labels[i, j]
        ax.text(j, i, str(val), ha="center", va="center", fontsize=18, fontweight="bold", color="black")
        ax.text(j, i + 0.25, lbl, ha="center", va="center", fontsize=9, color="grey")

plt.tight_layout()
plt.savefig("chart_22_confusion_matrix.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
