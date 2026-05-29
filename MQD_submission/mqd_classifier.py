import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from catboost import CatBoostClassifier, Pool, cv as catboost_cv
from sklearn.metrics import (
    ConfusionMatrixDisplay, classification_report, confusion_matrix, roc_auc_score
)
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# parquet files might be in different places depending where you run this
DATA = Path(".")
if not (DATA / "business_cards_MDQ.parquet").exists():
    DATA = Path.cwd()
if not (DATA / "business_cards_MDQ.parquet").exists():
    DATA = Path.home() / "Desktop" / "MQD"
print(f"Data dir: {DATA.resolve()}")

print(">>> Loading data...")

BIZ_COLS = [
    "transaction_date", "transaction_timestamp", "transaction_amount_kzt",
    "mcc", "merchant_id", "channel", "card_number", "tokenized", "is_recurring",
    "country",
]
CON_COLS = BIZ_COLS.copy()

biz = pd.read_parquet(DATA / "business_cards_MDQ.parquet", columns=BIZ_COLS)
con = pd.read_parquet(DATA / "consumer_cards_MDQ.parquet", columns=CON_COLS)
bus_cards = pd.read_parquet(DATA / "merchants_reference.parquet")

print(f"  Business cards: {len(biz):,} rows, {biz['card_number'].nunique():,} cards")
print(f"  Consumer cards: {len(con):,} rows, {con['card_number'].nunique():,} cards")

# label + concat
biz["label"] = 1
con["label"] = 0

cols = BIZ_COLS + ["label"]
df = pd.concat([biz[cols], con[cols]], ignore_index=True)
del biz, con

print(f"  Combined: {len(df):,} rows, {df['card_number'].nunique():,} cards")
print(f"  Label: 0={int((df['label']==0).sum()):,}, 1={int((df['label']==1).sum()):,}")

# merge merchant reference
df = df.merge(
    bus_cards[["merchant_id", "mcc", "recurring_capable", "merchant_name", "merchant_country"]],
    on=["merchant_id", "mcc"],
    how="left",
)
del bus_cards

# MCC codes tell us what a merchant sells. The idea: hidden entrepreneurs
# leave traces in wholesale/logistics/fuel/saas spending that regular
# consumers simply don't have. We split into 5 groups:
# - BUSINESS_MCCS: broad business filter (services, wholesale, shipping)
# - WHOLESALE_PROD_MCCS: actual product purchasing - core "buying stock" signal
# - LOGISTICS_MCCS + FUEL_MCCS: shipping and fleet fuel
# - SAAS_AD_MCCS: Google Ads, cloud hosting, online platforms
BUSINESS_MCCS = {
    "7311", "7372", "5968", "4816", "7379", "5734",
    "7392", "7399", "8931", "8111", "8911", "7361",
    "4812", "4814",
    "5021", "5044", "5045", "5046", "5111", "5943",
    "5099", "5199", "5131", "5137", "5139", "5169", "5172", "5193",
    "5039", "5065", "5072", "5085", "5211", "5231",
    "4214", "4215", "4225", "4011",
    "4511", "7011", "4722", "4723",
    "7394", "7512",
    "6381", "7321",
    "7333", "7338", "7298", "7299",
    "5261",
    "5122",
    "5200",
}

WHOLESALE_PROD_MCCS = {
    "5021", "5039", "5044", "5045", "5046", "5065", "5072", "5085",
    "5099", "5111", "5122", "5131", "5137", "5139", "5169", "5172",
    "5193", "5199", "5200", "5211", "5231",
}

LOGISTICS_MCCS = {"4214", "4215", "4225", "4011", "4457", "7511"}
FUEL_MCCS = {"5541", "5542", "5983"}
SAAS_AD_MCCS = {"7311", "7372", "5968", "4816", "4812", "4814", "7379", "5734"}

# feature engineering
print("\n>>> Feature engineering...")

# 1. Clockwork Buyer
# Businesses restock on schedule (every Monday, every 2 weeks).
# Consumers buy randomly. CV = std/mean of inter-purchase intervals.
# Low CV = clockwork regular = business. High CV = random = consumer.
print("  [1] Clockwork Buyer - inter-purchase CV")
df.sort_values(["card_number", "mcc", "transaction_timestamp"], inplace=True)

df["interval_hours"] = (
    df.groupby(["card_number", "mcc"])["transaction_timestamp"]
    .diff().dt.total_seconds() / 3600.0
)

cv_per_card_mcc = (
    df.dropna(subset=["interval_hours"])
    .groupby(["card_number", "mcc"])["interval_hours"]
    .agg(lambda x: x.std() / x.mean() if x.mean() > 1e-9 else np.nan)
    .rename("cv").reset_index()
)

clockwork_cv = cv_per_card_mcc.groupby("card_number")["cv"].mean().rename("clockwork_cv_mean")
clockwork_cnt = cv_per_card_mcc.dropna(subset=["cv"]).groupby("card_number")["cv"].count().rename("clockwork_mcc_count")
del cv_per_card_mcc
df.drop(columns=["interval_hours"], inplace=True)
print(f"    -> {len(clockwork_cv):,} cards")

# 2. Off-Hours Operator
# Normal people shop 9-19. Business owners place orders at 7 AM or 10 PM.
# What share of their business-MCC transactions happen off-hours?
print("  [2] Off-Hours Operator")
df["txn_hour"] = df["transaction_timestamp"].dt.hour
df["is_business_mcc"] = df["mcc"].isin(BUSINESS_MCCS)
df["is_off_hours"] = (df["txn_hour"] < 9) | (df["txn_hour"] >= 19)

biz_mcc_txns = df[df["is_business_mcc"]].groupby("card_number").size()
off_hours_biz = df[df["is_business_mcc"] & df["is_off_hours"]].groupby("card_number").size()
off_hours_ratio = (off_hours_biz / biz_mcc_txns).rename("off_hours_ratio").fillna(0.0)
off_hours_total = df[df["is_off_hours"]].groupby("card_number").size().rename("off_hours_total_count")
total_txns = df.groupby("card_number").size().rename("total_txns")
overall_off_hours_ratio = (off_hours_total / total_txns).rename("overall_off_hours_ratio")

# 3. Expense Ratio Inversion
# Consumers spend on food/clothes. Entrepreneurs spend on wholesale stock.
# wholesale_spend_ratio = wholesale / total. The log version handles skew.
print("  [3] Expense Ratio Inversion")
total_spend = df.groupby("card_number")["transaction_amount_kzt"].sum().rename("total_spend_kzt")
wholesale_spend = df[df["mcc"].isin(WHOLESALE_PROD_MCCS)].groupby("card_number")["transaction_amount_kzt"].sum().rename("wholesale_spend_kzt")
expense_ratio = (wholesale_spend / total_spend).rename("wholesale_spend_ratio").fillna(0.0)
wholesale_spend_log = np.log1p(wholesale_spend).rename("wholesale_spend_log")

# 4. Token Wholesale
# Tokenized = card saved for recurring/repeat payments. Consumers tokenize
# Netflix. Businesses tokenize wholesale suppliers. We flag tokenized
# wholesale txns above the 90th business percentile.
print("  [4] Token Wholesale")
token_wholesale = df[df["mcc"].isin(WHOLESALE_PROD_MCCS) & (df["tokenized"] == True)].copy()
if len(token_wholesale) > 0:
    biz_token = token_wholesale[token_wholesale["label"] == 1]
    p90 = biz_token["transaction_amount_kzt"].quantile(0.90)
    print(f"    -> 90th pctile (business): {p90:,.0f} KZT")
else:
    p90 = 0

token_flag = token_wholesale[token_wholesale["transaction_amount_kzt"] > p90].groupby("card_number").size().gt(0).astype(int).rename("token_wholesale_flag")
token_cnt = token_wholesale[token_wholesale["transaction_amount_kzt"] > p90].groupby("card_number").size().rename("token_wholesale_count")
del token_wholesale

# 5. Baseline Aggregations
# These simple stats turned out to be the strongest signals. tokenized_ratio
# and online_ratio are #1 and #2. Businesses are overwhelmingly online +
# tokenized. Consumers mostly pay at POS with plastic.
print("  [5] Baseline aggregations")
card_agg = df.groupby("card_number").agg(
    amount_mean=("transaction_amount_kzt", "mean"),
    amount_std=("transaction_amount_kzt", "std"),
    amount_sum=("transaction_amount_kzt", "sum"),
    amount_max=("transaction_amount_kzt", "max"),
    n_unique_mcc=("mcc", "nunique"),
    n_unique_merchants=("merchant_id", "nunique"),
    n_online=("channel", lambda x: (x == "online").sum()),
    n_pos=("channel", lambda x: (x == "POS").sum()),
    tokenized_txn_count=("tokenized", "sum"),
    recurring_count=("is_recurring", "sum"),
)
card_agg["online_ratio"] = card_agg["n_online"] / (card_agg["n_online"] + card_agg["n_pos"])
card_agg["tokenized_ratio"] = card_agg["tokenized_txn_count"] / total_txns
card_agg["n_unique_mcc_log"] = np.log1p(card_agg["n_unique_mcc"])

# 6. Supplier Fingerprint
print("  [6] Supplier Fingerprint - vendor concentration")
# A consumer visits tons of places. A business concentrates on a few
# regular suppliers. Two angles: top-3 spend share + Gini coefficient.
merchant_spend = df.groupby(["card_number", "merchant_id"])["transaction_amount_kzt"].sum().reset_index()

def _top3_share(g):
    t = g["transaction_amount_kzt"].sum()
    return g.nlargest(3, "transaction_amount_kzt")["transaction_amount_kzt"].sum() / t if t > 0 else 0.0

vendor_concentration = merchant_spend.groupby("card_number").apply(_top3_share, include_groups=False).rename("vendor_concentration")

def _merchant_gini(g):
    a = g["transaction_amount_kzt"].sort_values().values
    if len(a) == 0 or a.sum() == 0:
        return 0.0
    n = len(a)
    cs = np.cumsum(a)
    return float((2 * np.sum(cs) / cs[-1] - n - 1) / n)

merchant_gini = merchant_spend.groupby("card_number").apply(_merchant_gini, include_groups=False).rename("merchant_gini")
del merchant_spend

# 7. Last-Mile Echo
print("  [7] Last-Mile Echo - wholesale to logistics lag")
# Buy stock → ship it within days. This wholesale→logistics sequence
# is basically invisible in consumer data. Two metrics: avg lag in days,
# and share of days where both types appear.
daily_wholesale = df[df["mcc"].isin(WHOLESALE_PROD_MCCS)].groupby(["card_number", "transaction_date"])["transaction_amount_kzt"].sum().reset_index()
daily_wholesale.columns = ["card_number", "date", "wholesale_amt"]

daily_logistics = df[df["mcc"].isin(LOGISTICS_MCCS | FUEL_MCCS)].groupby(["card_number", "transaction_date"])["transaction_amount_kzt"].sum().reset_index()
daily_logistics.columns = ["card_number", "date", "logistics_amt"]

daily_merged = daily_wholesale.merge(daily_logistics, on=["card_number", "date"], how="outer").fillna(0)
daily_merged = daily_merged.sort_values(["card_number", "date"]).reset_index(drop=True)

logistics_dates_by_card = {
    cn: g["date"].values.astype("datetime64[D]")
    for cn, g in daily_logistics.groupby("card_number", sort=False)
}

def _echo_avg(group):
    cn = group.name
    w = group.loc[group["wholesale_amt"] > 0, "date"].values.astype("datetime64[D]")
    l = logistics_dates_by_card.get(cn, np.array([], dtype="datetime64[D]"))
    if len(w) == 0 or len(l) == 0:
        return 0.0
    idx = np.clip(np.searchsorted(l, w, side="left"), 0, len(l) - 1)
    lags = (l[idx] - w).astype(int)
    valid = (lags >= 0) & (lags <= 7)
    return float(lags[valid].mean()) if valid.sum() > 0 else 0.0

wholesale_to_logistics_lag = daily_merged.groupby("card_number", sort=False).apply(_echo_avg, include_groups=False).rename("wholesale_to_logistics_lag")

daily_merged["both"] = (daily_merged["wholesale_amt"] > 0) & (daily_merged["logistics_amt"] > 0)
daily_merged["any"] = (daily_merged["wholesale_amt"] > 0) | (daily_merged["logistics_amt"] > 0)

wholesale_to_logistics_count = daily_merged[daily_merged["any"]].groupby("card_number")["both"].mean().rename("wholesale_to_logistics_count")
del daily_wholesale, daily_logistics, daily_merged, logistics_dates_by_card

# 8. Round-Trip Cash Flow (redefined)
# Original paradox: cash-in → cash-out. Our data only has outgoing txns
# so we redefined it. Business owners have periodic spending "bursts"
# (top 5% days). How regular are those bursts? Low std = business.
print("  [8] Round-Trip Cash Flow - spending burst periodicity")
daily_spend = df.groupby(["card_number", "transaction_date"])["transaction_amount_kzt"].sum().reset_index()

def _burst_periodicity(g):
    a = g["transaction_amount_kzt"]
    if len(a) < 5:
        return np.nan
    t = a.quantile(0.95)
    b = g[a >= t]["transaction_date"].sort_values()
    if len(b) < 2:
        return np.nan
    d = b.diff().dt.days.dropna()
    return float(d.std()) if len(d) >= 2 else np.nan

spending_burst_periodicity = daily_spend.groupby("card_number").apply(_burst_periodicity, include_groups=False).rename("spending_burst_periodicity")
del daily_spend

# 9. Inventory Pulse
# One big bulk order, then several small top-ups (perishables, emergency).
# Ratio of small/large wholesale txns. Around 1-3 for businesses.
print("  [9] Inventory Pulse")
def _inventory_pulse(g):
    w = g[g["mcc"].isin(WHOLESALE_PROD_MCCS)]["transaction_amount_kzt"]
    if len(w) < 5:
        return np.nan
    p30, p70 = w.quantile(0.30), w.quantile(0.70)
    s, l = (w <= p30).sum(), (w >= p70).sum()
    return s / l if l > 0 else np.nan

massive_to_small_ratio = df.groupby("card_number").apply(_inventory_pulse, include_groups=False).rename("massive_to_small_ratio")

# 10. Multi-Vendor Loyalty Paradox
# Consumer: either one recurring bill (Netflix) or random shopping.
# Entrepreneur: spends at many B2B vendors but pays per invoice,
# not via recurring. b2b_volume_no_recurring captures this.
print("  [10] Multi-Vendor Loyalty Paradox")
b2b_spend = df[df["mcc"].isin(BUSINESS_MCCS)].groupby("card_number")["transaction_amount_kzt"].sum()
recurring_ratio = df.groupby("card_number")["is_recurring"].mean()
b2b_volume_no_recurring = (b2b_spend * (1 - recurring_ratio)).rename("b2b_volume_no_recurring").fillna(0.0)
loyalty_score = df.groupby("card_number")["merchant_id"].nunique().rename("merchant_nunique")
txns_per_merchant = total_txns / loyalty_score

# 11. Channel Schizophrenia
# Consumer: mostly online OR mostly in-store. Business owner: switches
# constantly - orders online, pays courier at POS, buys fuel at POS.
# alternation_rate = how often channel flips between txns
# entropy = Shannon entropy of online/POS distribution (balanced = biz)
print("  [11] Channel Schizophrenia")
df_sorted = df.sort_values(["card_number", "transaction_timestamp"])
df_sorted["prev_channel"] = df_sorted.groupby("card_number")["channel"].shift(1)
df_sorted["channel_switch"] = (df_sorted["channel"] != df_sorted["prev_channel"]) & df_sorted["prev_channel"].notna()

channel_alternation_rate = df_sorted.groupby("card_number")["channel_switch"].mean().rename("channel_alternation_rate")

def _channel_entropy(g):
    c = g.value_counts()
    p = c / c.sum()
    return float(-(p * np.log2(p + 1e-10)).sum())

channel_entropy = df_sorted.groupby("card_number")["channel"].apply(_channel_entropy).rename("channel_entropy")
del df_sorted

# 12. Cross-border Sourcing
# Entrepreneurs pay Alibaba, Google Ads, AWS. Consumers rarely do.
# card country != merchant country = cross-border. We compute ratios
# overall and specifically for SaaS/ad MCCs.
print("  [12] Cross-border Sourcing")
df["is_cross_border"] = (df["merchant_country"] != df["country"]) & df["merchant_country"].notna()
df["is_cb_saas_ad"] = df["is_cross_border"] & df["mcc"].isin(SAAS_AD_MCCS)

cb_ratio = df.groupby("card_number")["is_cross_border"].mean().rename("cb_ratio")
cb_saas_ad_ratio = df[df["mcc"].isin(SAAS_AD_MCCS)].groupby("card_number")["is_cross_border"].mean().rename("cb_saas_ad_ratio")
cb_spend = df[df["is_cross_border"]].groupby("card_number")["transaction_amount_kzt"].sum()
cb_spend_share = (cb_spend / total_spend).rename("cb_spend_share").fillna(0.0)
cb_saas_ad_count = df[df["is_cb_saas_ad"]].groupby("card_number").size().rename("cb_saas_ad_count")

# cleanup temp columns
df.drop(columns=[
    "txn_hour", "is_business_mcc", "is_off_hours", "is_cross_border",
    "is_cb_saas_ad",
], inplace=True, errors="ignore")

# All features are in separate Series indexed by card_number.
# Merge them into one table. Fill NaN with sensible defaults
# (median for skewed features, 0 for ratios, 168h for missing lag).
print("\n>>> Assembling feature matrix...")
labels = df[["card_number", "label"]].drop_duplicates("card_number").set_index("card_number")["label"]

features = pd.DataFrame(index=labels.index)
features["clockwork_cv_mean"] = clockwork_cv
features["clockwork_mcc_count"] = clockwork_cnt
features["off_hours_ratio"] = off_hours_ratio
features["overall_off_hours_ratio"] = overall_off_hours_ratio
features["off_hours_total_count"] = off_hours_total
features["wholesale_spend_ratio"] = expense_ratio
features["wholesale_spend_log"] = wholesale_spend_log
features["token_wholesale_flag"] = token_flag
features["token_wholesale_count"] = token_cnt
features["total_txns"] = total_txns
features["amount_mean"] = card_agg["amount_mean"]
features["amount_std"] = card_agg["amount_std"]
features["amount_sum"] = card_agg["amount_sum"]
features["amount_max"] = card_agg["amount_max"]
features["n_unique_mcc_log"] = card_agg["n_unique_mcc_log"]
features["n_unique_mcc"] = card_agg["n_unique_mcc"]
features["n_unique_merchants"] = card_agg["n_unique_merchants"]
features["online_ratio"] = card_agg["online_ratio"]
features["tokenized_ratio"] = card_agg["tokenized_ratio"]
features["n_online"] = card_agg["n_online"]
features["n_pos"] = card_agg["n_pos"]
features["vendor_concentration"] = vendor_concentration
features["merchant_gini"] = merchant_gini
features["wholesale_to_logistics_lag"] = wholesale_to_logistics_lag
features["wholesale_to_logistics_count"] = wholesale_to_logistics_count
features["spending_burst_periodicity"] = spending_burst_periodicity
features["massive_to_small_ratio"] = massive_to_small_ratio
features["b2b_volume_no_recurring"] = b2b_volume_no_recurring
features["txns_per_merchant"] = txns_per_merchant
features["channel_alternation_rate"] = channel_alternation_rate
features["channel_entropy"] = channel_entropy
features["cb_ratio"] = cb_ratio
features["cb_saas_ad_ratio"] = cb_saas_ad_ratio
features["cb_spend_share"] = cb_spend_share
features["cb_saas_ad_count"] = cb_saas_ad_count

# fill NaNs
features["clockwork_cv_mean"] = features["clockwork_cv_mean"].fillna(features["clockwork_cv_mean"].median())
features["clockwork_mcc_count"] = features["clockwork_mcc_count"].fillna(0).astype(int)
features["off_hours_ratio"] = features["off_hours_ratio"].fillna(0.0)
features["overall_off_hours_ratio"] = features["overall_off_hours_ratio"].fillna(0.0)
features["off_hours_total_count"] = features["off_hours_total_count"].fillna(0).astype(int)
features["wholesale_spend_ratio"] = features["wholesale_spend_ratio"].fillna(0.0)
features["wholesale_spend_log"] = features["wholesale_spend_log"].fillna(0.0)
features["token_wholesale_flag"] = features["token_wholesale_flag"].fillna(0).astype(int)
features["token_wholesale_count"] = features["token_wholesale_count"].fillna(0).astype(int)
features["online_ratio"] = features["online_ratio"].fillna(0.0)
features["tokenized_ratio"] = features["tokenized_ratio"].fillna(0.0)
features["amount_std"] = features["amount_std"].fillna(0.0)
features["vendor_concentration"] = features["vendor_concentration"].fillna(0.0)
features["merchant_gini"] = features["merchant_gini"].fillna(0.0)
features["wholesale_to_logistics_lag"] = features["wholesale_to_logistics_lag"].fillna(168.0)
features["wholesale_to_logistics_count"] = features["wholesale_to_logistics_count"].fillna(0).astype(int)
features["spending_burst_periodicity"] = features["spending_burst_periodicity"].fillna(features["spending_burst_periodicity"].median())
features["massive_to_small_ratio"] = features["massive_to_small_ratio"].fillna(features["massive_to_small_ratio"].median())
features["b2b_volume_no_recurring"] = features["b2b_volume_no_recurring"].fillna(0.0)
features["txns_per_merchant"] = features["txns_per_merchant"].fillna(1.0)
features["channel_alternation_rate"] = features["channel_alternation_rate"].fillna(0.0)
features["channel_entropy"] = features["channel_entropy"].fillna(0.0)
features["cb_ratio"] = features["cb_ratio"].fillna(0.0)
features["cb_saas_ad_ratio"] = features["cb_saas_ad_ratio"].fillna(0.0)
features["cb_spend_share"] = features["cb_spend_share"].fillna(0.0)
features["cb_saas_ad_count"] = features["cb_saas_ad_count"].fillna(0).astype(int)

before = len(features)
features = features.dropna()
after = len(features)

print(f"  Cards: {before:,} -> {after:,} after dropna")
print(f"  Features: {features.shape[1]}")
print(f"  Columns: {list(features.columns)}")

labels = labels.loc[features.index]
print(f"  Label distribution:\n{labels.value_counts().to_string()}")

# 20% holdout. Stratify keeps class ratio consistent.
X_train, X_test, y_train, y_test = train_test_split(
    features.values, labels.values, test_size=0.2, random_state=42, stratify=labels.values,
)
feature_names = list(features.columns)
print(f"  Train: {len(X_train):,}, Test: {len(X_test):,}")

# CatBoost because: native NaN handling, Ordered Boosting (less overfit),
# auto_class_weights for imbalance, and it usually beats XGB/LGBM on
# tabular data. depth=6, lr=0.1, early_stopping=50 on AUC.
print("\n>>> Training CatBoost...")
model = CatBoostClassifier(
    iterations=500, learning_rate=0.1, depth=6,
    loss_function="Logloss", eval_metric="AUC",
    auto_class_weights="Balanced", early_stopping_rounds=50,
    verbose=50, random_seed=42, task_type="CPU", allow_writing_files=False,
)
model.fit(X_train, y_train, eval_set=(X_test, y_test), use_best_model=True)

# One split could be luck. 5-fold CV proves the model actually works.
print("\n>>> 5-fold Cross-Validation...")
cv_model = CatBoostClassifier(
    iterations=200, learning_rate=0.1, depth=6,
    loss_function="Logloss", eval_metric="AUC",
    auto_class_weights="Balanced", random_seed=42,
    task_type="CPU", allow_writing_files=False, verbose=0,
)
cv_pool = Pool(features.values, labels.values, feature_names=feature_names)
cv_results = catboost_cv(cv_pool, cv_model.get_params(), fold_count=5, stratified=True, early_stopping_rounds=30, verbose_eval=False)

if "test-AUC-mean" in cv_results.columns:
    print(f"  CV AUC-ROC mean: {cv_results['test-AUC-mean'].iloc[-1]:.4f}")
    print(f"  CV AUC-ROC std:  {cv_results['test-AUC-std'].iloc[-1]:.4f}")

# AUC-ROC measures class separation. CM shows actual mistakes:
# FP = consumers called business, FN = businesses called consumer.
print("\n>>> Evaluation...")
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

auc = roc_auc_score(y_test, y_proba)
print(f"\n  AUC-ROC: {auc:.4f}")

cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(f"{'':>10} {'Pred 0':>8} {'Pred 1':>8}")
print(f"{'Actual 0':>10} {cm[0,0]:>8} {cm[0,1]:>8}")
print(f"{'Actual 1':>10} {cm[1,0]:>8} {cm[1,1]:>8}")
print(classification_report(y_test, y_pred, target_names=["Consumer", "Business"]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ConfusionMatrixDisplay.from_estimator(model, X_test, y_test, display_labels=["Consumer", "Business"], cmap="Blues")
plt.title(f"Confusion Matrix (AUC={auc:.4f})")
plt.savefig(DATA / "confusion_matrix.png", dpi=150)
print("  -> confusion_matrix.png")

# feature importance
print("\n>>> Feature Importance...")
fi_df = pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_}).sort_values("importance", ascending=False)
print("Top 10:")
for i, (_, r) in enumerate(fi_df.head(10).iterrows(), 1):
    print(f"  {i}. {r['feature']:<30s} {r['importance']:.2f}%")

plt.figure(figsize=(10, 8))
top15 = fi_df.head(15)
plt.barh(range(len(top15)), top15["importance"].values)
plt.yticks(range(len(top15)), top15["feature"].values)
plt.gca().invert_yaxis()
plt.xlabel("Importance (%)")
plt.title("Top 15 Feature Importances")
plt.tight_layout()
plt.savefig(DATA / "feature_importance.png", dpi=150)
print("  -> feature_importance.png")

# SHAP explains WHY each card scored what it did, not just WHAT matters.
# 500 sample (full set would be slow). Summary = direction, Bar = magnitude.
print("\n>>> SHAP...")
import shap

test_df = pd.DataFrame(X_test[:500], columns=feature_names)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(test_df)

plt.figure(figsize=(12, 8))
shap.summary_plot(shap_values, test_df, show=False)
plt.title("SHAP Summary")
plt.tight_layout()
plt.savefig(DATA / "shap_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print("  -> shap_summary.png")

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, test_df, plot_type="bar", show=False)
plt.title("SHAP Bar")
plt.tight_layout()
plt.savefig(DATA / "shap_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("  -> shap_bar.png")

# Score all consumer cards, pick top-100 highest business probability.
# Assign a product based on their strongest behavioral signal.
print("\n>>> Top 100 Hidden Entrepreneurs...")
consumer_mask = labels == 0
consumer_feat = features.loc[consumer_mask]
consumer_card_numbers = consumer_feat.index.values
consumer_probas = model.predict_proba(consumer_feat.values)[:, 1]

top100_idx = np.argsort(consumer_probas)[-100:][::-1]
top100_cards = consumer_card_numbers[top100_idx]
top100_scores = consumer_probas[top100_idx]

top100_df = pd.DataFrame({"card_number": top100_cards, "business_probability": top100_scores, "rank": range(1, 101)})

# Thresholds = median consumer values. High wholesale → B2B Cashback.
# Regular clockwork → Working Capital Loan. High channel switching →
# Merchant Account. None of the above → Business Credit Card.
print("  Computing target products...")
feat_consumer = features.loc[consumer_mask]
cv_th = feat_consumer["clockwork_cv_mean"].median()
ws_th = feat_consumer["wholesale_spend_ratio"].median()
sch_th = feat_consumer["channel_alternation_rate"].median()

top100_cv = feat_consumer.loc[top100_cards, "clockwork_cv_mean"]
top100_ws = feat_consumer.loc[top100_cards, "wholesale_spend_ratio"]
top100_sch = feat_consumer.loc[top100_cards, "channel_alternation_rate"]

products = []
for i in range(100):
    if top100_ws.iloc[i] > ws_th:
        products.append("B2B Cashback")
    elif top100_cv.iloc[i] > cv_th:
        products.append("Working Capital Loan")
    elif top100_sch.iloc[i] > sch_th:
        products.append("Merchant Account")
    else:
        products.append("Business Credit Card")

top100_df["recommended_product"] = products

print("\nTop 10:")
print(top100_df.head(10).to_string(index=False))

top100_df.to_csv(DATA / "top100_hidden_entrepreneurs.csv", index=False)
print(f"\n  Saved top100_hidden_entrepreneurs.csv ({len(top100_df)} records)")

print("\nScore distribution:")
for q in [0, 25, 50, 75, 90, 95, 99, 100]:
    print(f"  P{q:>3}: {np.percentile(consumer_probas, q):.4f}")
print(f"  Cards > 0.5: {(consumer_probas > 0.5).sum():,} / {len(consumer_probas):,}")

print("\nProduct distribution:")
print(top100_df["recommended_product"].value_counts().to_string())

print("\nDone.")
