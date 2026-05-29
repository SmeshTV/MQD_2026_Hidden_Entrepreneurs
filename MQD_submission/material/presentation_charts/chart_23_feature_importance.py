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

fig, ax = plt.subplots(figsize=(10, 8))

features = [
    "tokenized_ratio",
    "online_ratio",
    "b2b_volume_no_recurring",
    "channel_alternation_rate",
    "vendor_concentration",
    "wholesale_spend_ratio",
    "cb_spend_share",
    "txns_per_merchant",
    "total_txns",
    "amount_sum",
    "cb_saas_ad_count",
    "channel_entropy",
    "n_unique_merchants",
    "n_unique_mcc",
    "merchant_gini",
]
values = [26.3, 20.3, 12.0, 9.2, 3.7, 3.1, 2.9, 2.6, 2.5, 2.5, 1.9, 1.9, 1.8, 1.2, 1.2]

colors = ["navy"] * 4 + ["teal"] * 11

bars = ax.barh(features[::-1], values[::-1], color=colors[::-1])

ax.set_xlabel("Feature Importance (%)")
ax.set_xlim(0, 30)

for bar, v in zip(bars, values[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{v}%", va="center", fontsize=9)

plt.tight_layout()
plt.savefig("chart_23_feature_importance.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
