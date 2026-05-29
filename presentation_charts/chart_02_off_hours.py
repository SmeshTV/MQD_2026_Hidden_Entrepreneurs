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

groups = ["Before 09:00", "09:00 \u2014 19:00", "After 19:00"]
business_vals = [32, 35, 33]
consumer_vals = [6, 81, 13]

x = np.arange(len(groups))
width = 0.35

bars1 = ax.bar(x - width / 2, business_vals, width, color="navy", label="Business Cards")
bars2 = ax.bar(x + width / 2, consumer_vals, width, color="teal", label="Consumer Cards")

ax.set_xlabel("")
ax.set_ylabel("Share of Business-MCC Transactions (%)")
ax.set_xticks(x)
ax.set_xticklabels(groups)
ax.set_ylim(0, 100)
ax.legend(loc="upper right", frameon=False)

for bar in bars1:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5, f"{h}%", ha="center", va="bottom", fontsize=9)
for bar in bars2:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5, f"{h}%", ha="center", va="bottom", fontsize=9)

plt.savefig("chart_02_off_hours.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
