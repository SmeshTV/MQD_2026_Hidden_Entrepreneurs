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

fig, ax = plt.subplots(figsize=(8, 4))

categories = ["Business Card", "Consumer Card"]
values = [2940000, 37500]

bars = ax.barh(categories, values, color=["navy", "teal"])

ax.set_xlabel("B2B Volume Without Recurring (KZT)")

for bar, v in zip(bars, values):
    ax.text(bar.get_width() + 30000, bar.get_y() + bar.get_height() / 2,
            f"{v:,}", va="center", fontsize=10)

# Annotation: 80x difference
mid_y = 0.5
max_w = max(values)
ax.annotate(
    "80\u00d7 difference",
    xy=(values[1] + max_w * 0.1, 0),
    xytext=(values[1] + max_w * 0.1, 1),
    fontsize=9,
    color="orange",
    ha="center",
    arrowprops=dict(arrowstyle="<->", color="orange", lw=1.5),
)

plt.tight_layout()
plt.savefig("chart_10_b2b_no_recurring.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
