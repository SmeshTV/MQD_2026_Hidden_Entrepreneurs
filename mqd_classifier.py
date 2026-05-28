"""
Mastercard Data Quest 2026 — Hidden Entrepreneur Detection
==========================================================
Genius Level: 10 Behavioral Paradoxes + Cross-border + AUC-ROC + CV + Target Product
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

from catboost import CatBoostClassifier, Pool, cv as catboost_cv
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
DATA = Path(".")

# ── 1. LOAD DATA ────────────────────────────────────────────────────────────
print("=" * 70)
print("STEP 1/4 — Loading data".center(70))
print("=" * 70)

BIZ_COLS = [
    "transaction_date", "transaction_timestamp", "transaction_amount_kzt",
    "mcc", "merchant_id", "channel", "card_number", "tokenized", "is_recurring",
    "country",
]
CON_COLS = BIZ_COLS.copy()

biz: pd.DataFrame = pd.read_parquet(DATA / "business_cards_MDQ.parquet", columns=BIZ_COLS)
con: pd.DataFrame = pd.read_parquet(DATA / "consumer_cards_MDQ.parquet", columns=CON_COLS)

bus_cards: pd.DataFrame = pd.read_parquet(DATA / "merchants_reference.parquet")

print(f"  Business  cards: {len(biz):,} rows  |  cards: {biz['card_number'].nunique():,}")
print(f"  Consumer  cards: {len(con):,} rows  |  cards: {con['card_number'].nunique():,}")

# ── 2. LABEL & CONCAT ───────────────────────────────────────────────────────
biz["label"] = 1
con["label"] = 0

cols = BIZ_COLS + ["label"]
df: pd.DataFrame = pd.concat([biz[cols], con[cols]], ignore_index=True)
del biz, con

print(f"  Combined dataset: {len(df):,} rows  |  {df['card_number'].nunique():,} cards")
print(f"  Label balance: 0 -> {int((df['label']==0).sum()):,}  |  1 -> {int((df['label']==1).sum()):,}")

# ── 3. MERGE MERCHANT REFERENCE ─────────────────────────────────────────────
df = df.merge(
    bus_cards[["merchant_id", "mcc", "recurring_capable", "merchant_name", "merchant_country"]],
    on=["merchant_id", "mcc"],
    how="left",
)
del bus_cards

# ── 4. MCC CATEGORY MAPS ────────────────────────────────────────────────────
BUSINESS_MCCS: set = {
    "7311", "7372", "5968", "4816", "7379", "5734",
    "7392", "7399", "8931", "8111", "8911", "7361",
    "7311", "4812", "4814",
    "5021", "5044", "5045", "5046", "5111", "5943",
    "5099", "5199", "5131", "5137", "5139", "5169", "5172", "5193",
    "5039", "5065", "5072", "5085", "5211", "5231",
    "4214", "4215", "4225", "4011",
    "4511", "7011", "4722", "4723",
    "7394", "7512",
    "6381", "7321",
    "7333", "7338", "7298", "7299",
    "5199", "5261",
    "5122", "5172",
    "5200",
}

WHOLESALE_PROD_MCCS: set = {
    "5021", "5039", "5044", "5045", "5046", "5065", "5072", "5085",
    "5099", "5111", "5122", "5131", "5137", "5139", "5169", "5172",
    "5193", "5199", "5200", "5211", "5231",
}

LOGISTICS_MCCS: set = {
    "4214", "4215", "4225", "4011", "4457", "7511",
}

FUEL_MCCS: set = {"5541", "5542", "5983"}

SAAS_AD_MCCS: set = {
    "7311",  # Advertising
    "7372",  # IT services
    "5968",  # Subscriptions
    "4816",  # Network services
    "4812",  # Telecom equipment
    "4814",  # Telecom services
    "7379",  # Computer maintenance
    "5734",  # Software
}

# ── 5. FEATURE ENGINEERING ──────────────────────────────────────────────────
print("=" * 70)
print("STEP 2/4 — Feature Engineering".center(70))
print("=" * 70)

# --- 5a. Clockwork Buyer ────────────────────────────────────────────────────
print("  [5a] Clockwork Buyer — computing inter-purchase CV per (card, MCC)...")

df.sort_values(["card_number", "mcc", "transaction_timestamp"], inplace=True)

df["interval_hours"] = (
    df.groupby(["card_number", "mcc"])["transaction_timestamp"]
    .diff()
    .dt.total_seconds() / 3600.0
)

cv_per_card_mcc = (
    df.dropna(subset=["interval_hours"])
    .groupby(["card_number", "mcc"])["interval_hours"]
    .agg(lambda x: x.std() / x.mean() if x.mean() > 1e-9 else np.nan)
    .rename("cv")
    .reset_index()
)

clockwork_cv = (
    cv_per_card_mcc.groupby("card_number")["cv"]
    .mean()
    .rename("clockwork_cv_mean")
)

clockwork_cnt = (
    cv_per_card_mcc.dropna(subset=["cv"])
    .groupby("card_number")["cv"]
    .count()
    .rename("clockwork_mcc_count")
)

del cv_per_card_mcc
df.drop(columns=["interval_hours"], inplace=True)
print(f"    -> clockwork features computed for {len(clockwork_cv):,} cards")

# --- 5b. Off-Hours Operator ─────────────────────────────────────────────────
print("  [5b] Off-Hours Operator — computing off-hours biz-MCC txn fraction...")

df["txn_hour"] = df["transaction_timestamp"].dt.hour
df["is_business_mcc"] = df["mcc"].isin(BUSINESS_MCCS)
df["is_off_hours"] = (df["txn_hour"] < 9) | (df["txn_hour"] >= 19)

biz_mcc_txns = df[df["is_business_mcc"]].groupby("card_number").size()
off_hours_biz = (
    df[df["is_business_mcc"] & df["is_off_hours"]]
    .groupby("card_number")
    .size()
)

off_hours_ratio = (off_hours_biz / biz_mcc_txns).rename("off_hours_ratio").fillna(0.0)

off_hours_total = (
    df[df["is_off_hours"]]
    .groupby("card_number")
    .size()
    .rename("off_hours_total_count")
)

total_txns = df.groupby("card_number").size().rename("total_txns")
overall_off_hours_ratio = (off_hours_total / total_txns).rename("overall_off_hours_ratio")

print(f"    -> off-hours features computed")

# --- 5c. Expense Ratio Inversion ────────────────────────────────────────────
print("  [5c] Expense Ratio Inversion — computing wholesale spend share...")

total_spend = (
    df.groupby("card_number")["transaction_amount_kzt"].sum().rename("total_spend_kzt")
)

wholesale_spend = (
    df[df["mcc"].isin(WHOLESALE_PROD_MCCS)]
    .groupby("card_number")["transaction_amount_kzt"]
    .sum()
    .rename("wholesale_spend_kzt")
)

expense_ratio = (wholesale_spend / total_spend).rename("wholesale_spend_ratio").fillna(0.0)
wholesale_spend_log = np.log1p(wholesale_spend).rename("wholesale_spend_log")

print(f"    -> expense ratio features computed")

# --- 5d. Token Wholesale ────────────────────────────────────────────────────
print("  [5d] Token Wholesale — computing high-value tokenised wholesale flag...")

token_wholesale = df[
    df["mcc"].isin(WHOLESALE_PROD_MCCS) & (df["tokenized"] == True)
].copy()

if len(token_wholesale) > 0:
    biz_token = token_wholesale[token_wholesale["label"] == 1]
    p90 = biz_token["transaction_amount_kzt"].quantile(0.90)
    print(f"    -> 90th percentile (from business cards): {p90:,.0f} KZT")
else:
    p90 = 0

token_flag = (
    token_wholesale[token_wholesale["transaction_amount_kzt"] > p90]
    .groupby("card_number")
    .size()
    .gt(0)
    .astype(int)
    .rename("token_wholesale_flag")
)

token_cnt = (
    token_wholesale[token_wholesale["transaction_amount_kzt"] > p90]
    .groupby("card_number")
    .size()
    .rename("token_wholesale_count")
)

del token_wholesale
print(f"    -> token wholesale features computed")

# --- 5e. Baseline Aggregations ──────────────────────────────────────────────
print("  [5e] Baseline aggregations...")

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

card_agg["online_ratio"] = card_agg["n_online"] / (
    card_agg["n_online"] + card_agg["n_pos"]
)
card_agg["tokenized_ratio"] = card_agg["tokenized_txn_count"] / total_txns
card_agg["n_unique_mcc_log"] = np.log1p(card_agg["n_unique_mcc"])

# ── 5f. SUPPLIER FINGERPRINT ────────────────────────────────────────────────
print("  [5f] Supplier Fingerprint — vendor concentration...")

merchant_spend = df.groupby(["card_number", "merchant_id"])["transaction_amount_kzt"].sum().reset_index()

def _top3_share(g):
    total = g["transaction_amount_kzt"].sum()
    if total == 0:
        return 0.0
    top3 = g.nlargest(3, "transaction_amount_kzt")["transaction_amount_kzt"].sum()
    return top3 / total

vendor_concentration = (
    merchant_spend.groupby("card_number")
    .apply(_top3_share, include_groups=False)
    .rename("vendor_concentration")
)

def _merchant_gini(g):
    amounts = g["transaction_amount_kzt"].sort_values().values
    if len(amounts) == 0 or amounts.sum() == 0:
        return 0.0
    n = len(amounts)
    cumsum = np.cumsum(amounts)
    return float((2 * np.sum(cumsum) / cumsum[-1] - n - 1) / n)

merchant_gini = (
    merchant_spend.groupby("card_number")
    .apply(_merchant_gini, include_groups=False)
    .rename("merchant_gini")
)

del merchant_spend
print(f"    -> supplier fingerprint features computed")

# ── 5g. LAST-MILE ECHO ──────────────────────────────────────────────────────
print("  [5g] Last-Mile Echo — wholesale→logistics/fuel lag...")

# Aggregate to daily level first (much fewer rows than raw transactions)
daily_wholesale = (
    df[df["mcc"].isin(WHOLESALE_PROD_MCCS)]
    .groupby(["card_number", "transaction_date"])["transaction_amount_kzt"]
    .sum().reset_index()
)
daily_wholesale.columns = ["card_number", "date", "wholesale_amt"]

daily_logistics = (
    df[df["mcc"].isin(LOGISTICS_MCCS | FUEL_MCCS)]
    .groupby(["card_number", "transaction_date"])["transaction_amount_kzt"]
    .sum().reset_index()
)
daily_logistics.columns = ["card_number", "date", "logistics_amt"]

# Full outer join on card + date, fill zeros
daily_merged = daily_wholesale.merge(
    daily_logistics, on=["card_number", "date"], how="outer"
).fillna(0)
daily_merged = daily_merged.sort_values(["card_number", "date"]).reset_index(drop=True)

# Build dict: card_number -> sorted array of dates with logistics txns
logistics_dates_by_card = {
    cn: g["date"].values.astype("datetime64[D]")
    for cn, g in daily_logistics.groupby("card_number", sort=False)
}

def _daily_echo_avg(group):
    cn = group.name
    w_dates = group.loc[group["wholesale_amt"] > 0, "date"].values.astype("datetime64[D]")
    l_dates = logistics_dates_by_card.get(cn, np.array([], dtype="datetime64[D]"))
    if len(w_dates) == 0 or len(l_dates) == 0:
        return 0.0
    idx = np.searchsorted(l_dates, w_dates, side="left")
    idx = np.clip(idx, 0, len(l_dates) - 1)
    lags = (l_dates[idx] - w_dates).astype(int)
    valid = (lags >= 0) & (lags <= 7)
    if valid.sum() == 0:
        return 0.0
    return float(lags[valid].mean())

avg_echo_lag = (
    daily_merged.groupby("card_number", sort=False)
    .apply(_daily_echo_avg, include_groups=False)
    .rename("wholesale_to_logistics_lag")
)

# Cross-ratio: share of wholesale days that also have logistics or vice versa
daily_merged["both"] = (daily_merged["wholesale_amt"] > 0) & (daily_merged["logistics_amt"] > 0)
daily_merged["any"] = (daily_merged["wholesale_amt"] > 0) | (daily_merged["logistics_amt"] > 0)

cross_ratio = (
    daily_merged[daily_merged["any"]]
    .groupby("card_number")["both"]
    .mean()
    .rename("wholesale_logistics_cross_ratio")
)

wholesale_to_logistics_lag = avg_echo_lag
wholesale_to_logistics_count = cross_ratio

del daily_wholesale, daily_logistics, daily_merged, logistics_dates_by_card
print(f"    -> last-mile echo features computed")

# ── 5h. ROUND-TRIP CASH FLOW (Redefined) ────────────────────────────────────
print("  [5h] Round-Trip Cash Flow — spending burst periodicity...")

daily_spend = df.groupby(["card_number", "transaction_date"])["transaction_amount_kzt"].sum().reset_index()

def _burst_periodicity(g):
    amounts = g["transaction_amount_kzt"]
    if len(amounts) < 5:
        return np.nan
    threshold = amounts.quantile(0.95)
    burst_days = g[amounts >= threshold]["transaction_date"].sort_values()
    if len(burst_days) < 2:
        return np.nan
    intervals = burst_days.diff().dt.days.dropna()
    if len(intervals) < 2:
        return np.nan
    return float(intervals.std())

spending_burst_periodicity = (
    daily_spend.groupby("card_number")
    .apply(_burst_periodicity, include_groups=False)
    .rename("spending_burst_periodicity")
)

del daily_spend
print(f"    -> round-trip cash flow feature computed")

# ── 5i. INVENTORY PULSE ─────────────────────────────────────────────────────
print("  [5i] Inventory Pulse — massive purchase followed by small ones...")

def _inventory_pulse(g):
    wholesale = g[g["mcc"].isin(WHOLESALE_PROD_MCCS)]
    if len(wholesale) < 5:
        return np.nan
    amounts = wholesale["transaction_amount_kzt"]
    p30 = amounts.quantile(0.30)
    p70 = amounts.quantile(0.70)
    small = (amounts <= p30).sum()
    large = (amounts >= p70).sum()
    return small / large if large > 0 else np.nan

massive_to_small_ratio = (
    df.groupby("card_number")
    .apply(_inventory_pulse, include_groups=False)
    .rename("massive_to_small_ratio")
)

print(f"    -> inventory pulse feature computed")

# ── 5j. MULTI-VENDOR LOYALTY PARADOX ────────────────────────────────────────
print("  [5j] Multi-Vendor Loyalty Paradox — B2B volume without recurring...")

b2b_spend = (
    df[df["mcc"].isin(BUSINESS_MCCS)]
    .groupby("card_number")["transaction_amount_kzt"]
    .sum()
)

recurring_ratio = df.groupby("card_number")["is_recurring"].mean()

loyalty_score = (
    df.groupby("card_number")["merchant_id"]
    .nunique()
    .rename("merchant_nunique")
)

txns_per_merchant = total_txns / loyalty_score

b2b_volume_no_recurring = (b2b_spend * (1 - recurring_ratio)).rename("b2b_volume_no_recurring")
b2b_volume_no_recurring = b2b_volume_no_recurring.fillna(0.0)

print(f"    -> multi-vendor loyalty paradox features computed")

# ── 5k. CHANNEL SCHIZOPHRENIA ───────────────────────────────────────────────
print("  [5k] Channel Schizophrenia — channel switching patterns...")

df_sorted = df.sort_values(["card_number", "transaction_timestamp"])
df_sorted["prev_channel"] = df_sorted.groupby("card_number")["channel"].shift(1)
df_sorted["channel_switch"] = (
    (df_sorted["channel"] != df_sorted["prev_channel"])
    & df_sorted["prev_channel"].notna()
)

channel_alternation_rate = (
    df_sorted.groupby("card_number")["channel_switch"]
    .mean()
    .rename("channel_alternation_rate")
)

# Channel entropy
def _channel_entropy(g):
    counts = g.value_counts()
    probs = counts / counts.sum()
    return float(-(probs * np.log2(probs + 1e-10)).sum())

channel_entropy = (
    df_sorted.groupby("card_number")["channel"]
    .apply(_channel_entropy)
    .rename("channel_entropy")
)

del df_sorted
print(f"    -> channel schizophrenia features computed")

# ── 5l. CROSS-BORDER SOURCING ───────────────────────────────────────────────
print("  [5l] Cross-border Sourcing — international transactions...")

df["merchant_country_filled"] = df["merchant_country"].fillna(df["country"])

df["is_cross_border"] = (df["merchant_country"] != df["country"]) & df["merchant_country"].notna()

df["is_cb_saas_ad"] = df["is_cross_border"] & df["mcc"].isin(SAAS_AD_MCCS)

cb_ratio = (
    df.groupby("card_number")["is_cross_border"]
    .mean()
    .rename("cb_ratio")
)

cb_saas_ad_ratio = (
    df[df["mcc"].isin(SAAS_AD_MCCS)]
    .groupby("card_number")["is_cross_border"]
    .mean()
    .rename("cb_saas_ad_ratio")
)

cb_spend = (
    df[df["is_cross_border"]]
    .groupby("card_number")["transaction_amount_kzt"]
    .sum()
)

cb_spend_share = (cb_spend / total_spend).rename("cb_spend_share").fillna(0.0)

cb_saas_ad_count = (
    df[df["is_cb_saas_ad"]]
    .groupby("card_number")
    .size()
    .rename("cb_saas_ad_count")
)

print(f"    -> cross-border sourcing features computed")

# Cleanup temp columns
df.drop(columns=[
    "txn_hour", "is_business_mcc", "is_off_hours", "is_cross_border",
    "is_cb_saas_ad", "merchant_country_filled",
], inplace=True, errors="ignore")

# ── 6. ASSEMBLE FINAL FEATURE MATRIX ────────────────────────────────────────
print("=" * 70)
print("STEP 3/4 — Assembling feature matrix".center(70))
print("=" * 70)

labels = df[["card_number", "label"]].drop_duplicates("card_number").set_index("card_number")["label"]

features = pd.DataFrame(index=labels.index)

# Clockwork Buyer
features["clockwork_cv_mean"] = clockwork_cv
features["clockwork_mcc_count"] = clockwork_cnt

# Off-Hours Operator
features["off_hours_ratio"] = off_hours_ratio
features["overall_off_hours_ratio"] = overall_off_hours_ratio
features["off_hours_total_count"] = off_hours_total

# Expense Ratio Inversion
features["wholesale_spend_ratio"] = expense_ratio
features["wholesale_spend_log"] = wholesale_spend_log

# Token Wholesale
features["token_wholesale_flag"] = token_flag
features["token_wholesale_count"] = token_cnt

# Additional aggregations
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

# Supplier Fingerprint
features["vendor_concentration"] = vendor_concentration
features["merchant_gini"] = merchant_gini

# Last-Mile Echo
features["wholesale_to_logistics_lag"] = wholesale_to_logistics_lag
features["wholesale_to_logistics_count"] = wholesale_to_logistics_count

# Round-Trip Cash Flow
features["spending_burst_periodicity"] = spending_burst_periodicity

# Inventory Pulse
features["massive_to_small_ratio"] = massive_to_small_ratio

# Multi-Vendor Loyalty Paradox
features["b2b_volume_no_recurring"] = b2b_volume_no_recurring
features["txns_per_merchant"] = txns_per_merchant

# Channel Schizophrenia
features["channel_alternation_rate"] = channel_alternation_rate
features["channel_entropy"] = channel_entropy

# Cross-border Sourcing
features["cb_ratio"] = cb_ratio
features["cb_saas_ad_ratio"] = cb_saas_ad_ratio
features["cb_spend_share"] = cb_spend_share
features["cb_saas_ad_count"] = cb_saas_ad_count

# Fill NaN values
features["clockwork_cv_mean"] = features["clockwork_cv_mean"].fillna(
    features["clockwork_cv_mean"].median()
)
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
features["spending_burst_periodicity"] = features["spending_burst_periodicity"].fillna(
    features["spending_burst_periodicity"].median()
)
features["massive_to_small_ratio"] = features["massive_to_small_ratio"].fillna(
    features["massive_to_small_ratio"].median()
)
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

print(f"  Cards before dropna: {before:,}  |  after dropna: {after:,}")
print(f"  Features: {features.shape[1]}")
print(f"  Feature columns: {list(features.columns)}")

labels = labels.loc[features.index]

print(f"  Label distribution:\n{labels.value_counts().to_string()}")

# ── 7. TRAIN / TEST SPLIT ───────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    features.values,
    labels.values,
    test_size=0.2,
    random_state=42,
    stratify=labels.values,
)

feature_names = list(features.columns)
print(f"  Train size: {len(X_train):,}  |  Test size: {len(X_test):,}")

# ── 8. TRAIN CATBOOST ──────────────────────────────────────────────────────
print("=" * 70)
print("STEP 4/4 — Training CatBoost".center(70))
print("=" * 70)

model = CatBoostClassifier(
    iterations=500,
    learning_rate=0.1,
    depth=6,
    loss_function="Logloss",
    eval_metric="AUC",
    auto_class_weights="Balanced",
    early_stopping_rounds=50,
    verbose=50,
    random_seed=42,
    task_type="CPU",
    allow_writing_files=False,
)

model.fit(
    X_train,
    y_train,
    eval_set=(X_test, y_test),
    use_best_model=True,
)

# ── 9. CROSS-VALIDATION ─────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CROSS-VALIDATION (5-fold AUC-ROC)".center(70))
print("=" * 70)

cv_model = CatBoostClassifier(
    iterations=200,
    learning_rate=0.1,
    depth=6,
    loss_function="Logloss",
    eval_metric="AUC",
    auto_class_weights="Balanced",
    random_seed=42,
    task_type="CPU",
    allow_writing_files=False,
    verbose=0,
)

cv_pool = Pool(features.values, labels.values, feature_names=feature_names)
cv_results = catboost_cv(
    cv_pool,
    cv_model.get_params(),
    fold_count=5,
    stratified=True,
    early_stopping_rounds=30,
    verbose_eval=False,
)

if "test-AUC-mean" in cv_results.columns:
    print(f"  CV AUC-ROC mean:  {cv_results['test-AUC-mean'].iloc[-1]:.4f}")
    print(f"  CV AUC-ROC std:   {cv_results['test-AUC-std'].iloc[-1]:.4f}")
else:
    print(f"  CV columns: {cv_results.columns.tolist()}")
    print(f"  CV AUC-ROC: see logloss-based metrics above")

# ── 10. EVALUATION ──────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("EVALUATION".center(70))
print("=" * 70)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# PRIMARY METRIC: AUC-ROC
auc = roc_auc_score(y_test, y_proba)
print(f"\n  PRIMARY METRIC — AUC-ROC: {auc:.4f}")

# SECONDARY: Confusion Matrix (jury requirement)
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix (secondary):")
print(f"{'':>10} {'Pred 0':>8} {'Pred 1':>8}")
print(f"{'Actual 0':>10} {cm[0,0]:>8} {cm[0,1]:>8}")
print(f"{'Actual 1':>10} {cm[1,0]:>8} {cm[1,1]:>8}")

print("\n" + classification_report(y_test, y_pred, target_names=["Consumer", "Business"]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ConfusionMatrixDisplay.from_estimator(
    model, X_test, y_test,
    display_labels=["Consumer", "Business"],
    cmap="Blues",
)
plt.title(f"Confusion Matrix — Hidden Entrepreneurs (AUC = {auc:.4f})")
plt.savefig(DATA / "confusion_matrix.png", dpi=150)
print("  -> Saved confusion_matrix.png")

# ── 11. FEATURE IMPORTANCE ──────────────────────────────────────────────────
print("\n" + "-" * 70)
print("Feature Importance (top 20):")
print("-" * 70)

importance = model.get_feature_importance(prettified=True)
if importance is not None:
    print(importance.head(20).to_string(index=False))

fi_df = pd.DataFrame({
    "feature": feature_names,
    "importance": model.feature_importances_,
}).sort_values("importance", ascending=False)

print("\nTop 10 features by importance:")
for i, (_, row) in enumerate(fi_df.head(10).iterrows(), 1):
    print(f"  {i:2d}. {row['feature']:<30s}  {row['importance']:.2f}%")

plt.figure(figsize=(10, 8))
top15 = fi_df.head(15)
plt.barh(range(len(top15)), top15["importance"].values)
plt.yticks(range(len(top15)), top15["feature"].values)
plt.gca().invert_yaxis()
plt.xlabel("Importance (%)")
plt.title("Top 15 Feature Importances")
plt.tight_layout()
plt.savefig(DATA / "feature_importance.png", dpi=150)
print("  -> Saved feature_importance.png")

# ── 12. TOP-100 HIDDEN ENTREPRENEURS ────────────────────────────────────────
print("\n" + "=" * 70)
print("TOP 100 HIDDEN ENTREPRENEURS".center(70))
print("=" * 70)

consumer_mask = labels == 0
consumer_feat = features.loc[consumer_mask]
consumer_card_numbers = consumer_feat.index.values

consumer_probas = model.predict_proba(consumer_feat.values)[:, 1]

top100_idx = np.argsort(consumer_probas)[-100:][::-1]
top100_cards = consumer_card_numbers[top100_idx]
top100_scores = consumer_probas[top100_idx]

top100_df = pd.DataFrame({
    "card_number": top100_cards,
    "business_probability": top100_scores,
    "rank": range(1, 101),
})

# ── 13. BUSINESS LOGIC: TARGET PRODUCT ──────────────────────────────────────
print("  Computing target product recommendations...")

feat_consumer = features.loc[consumer_mask]

cv_threshold = feat_consumer["clockwork_cv_mean"].median()
ws_threshold = feat_consumer["wholesale_spend_ratio"].median()
sch_threshold = feat_consumer["channel_alternation_rate"].median()

top100_cv = feat_consumer.loc[top100_cards, "clockwork_cv_mean"]
top100_ws = feat_consumer.loc[top100_cards, "wholesale_spend_ratio"]
top100_sch = feat_consumer.loc[top100_cards, "channel_alternation_rate"]

products = []
for i, card in enumerate(top100_cards):
    if top100_ws.iloc[i] > ws_threshold:
        products.append("B2B Cashback")
    elif top100_cv.iloc[i] > cv_threshold:
        products.append("Working Capital Loan")
    elif top100_sch.iloc[i] > sch_threshold:
        products.append("Merchant Account")
    else:
        products.append("Business Credit Card")

top100_df["recommended_product"] = products

print("\nTop 10 Hidden Entrepreneurs:")
print(top100_df.head(10).to_string(index=False))

top100_df.to_csv(DATA / "top100_hidden_entrepreneurs.csv", index=False)
print(f"\n  -> Saved top100_hidden_entrepreneurs.csv ({len(top100_df)} records)")

print(f"\nConsumer card score distribution:")
for q in [0, 25, 50, 75, 90, 95, 99, 100]:
    print(f"  P{q:>3}: {np.percentile(consumer_probas, q):.4f}")
print(f"  Cards with prob > 0.5: {(consumer_probas > 0.5).sum():,} / {len(consumer_probas):,}")

print("\nProduct recommendation distribution:")
print(top100_df["recommended_product"].value_counts().to_string())

print("\n" + "=" * 70)
print("DONE — Genius Level Classification complete.".center(70))
print("=" * 70)
