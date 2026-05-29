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

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))

days = np.arange(1, 91)

# Top: Business Card
spike_days_biz = [7, 14, 21, 28, 35, 42, 49, 56]
biz_spend = np.random.uniform(5, 15, 90)
for d in spike_days_biz:
    if d <= 90:
        biz_spend[d - 1] = 500 + np.random.uniform(-20, 20)

ax1.plot(days, biz_spend, color="navy", linewidth=1)
ax1.set_ylabel("Daily Spend (KZT thousands)")
ax1.set_ylim(0, 550)
ax1.set_title("Business Card: Regular Spending Bursts", fontsize=11, loc="left")

# Bottom: Consumer Card
spike_days_con = [3, 27, 61, 88]
spike_vals_con = [200, 450, 180, 380]
con_spend = np.random.uniform(5, 15, 90)
for d, v in zip(spike_days_con, spike_vals_con):
    if d <= 90:
        con_spend[d - 1] = v + np.random.uniform(-10, 10)

ax2.plot(days, con_spend, color="teal", linewidth=1)
ax2.set_xlabel("Day")
ax2.set_ylabel("Daily Spend (KZT thousands)")
ax2.set_ylim(0, 550)
ax2.set_title("Consumer Card: Irregular Spending Bursts", fontsize=11, loc="left")

plt.tight_layout()
plt.savefig("chart_08_burst_periodicity.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
