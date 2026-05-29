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

categories = ["Tokenized Ratio", "Online Ratio", "Amount Mean (normalized)", "Unique Merchants (normalized)"]
business_vals = [0.75, 0.80, 0.85, 0.72]
consumer_vals = [0.08, 0.30, 0.18, 0.28]

y = np.arange(len(categories))
height = 0.35

bars1 = ax.barh(y + height / 2, business_vals, height, color="navy", label="Business Cards")
bars2 = ax.barh(y - height / 2, consumer_vals, height, color="teal", label="Consumer Cards")

ax.set_yticks(y)
ax.set_yticklabels(categories)
ax.set_xlabel("Relative Score")
ax.set_xlim(0, 1.0)
ax.legend(loc="upper right", frameon=False)

for bar in bars1:
    w = bar.get_width()
    ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2, f"{w:.2f}", va="center", fontsize=9)
for bar in bars2:
    w = bar.get_width()
    ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2, f"{w:.2f}", va="center", fontsize=9)

plt.tight_layout()
plt.savefig("chart_05_baseline_comparison.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
