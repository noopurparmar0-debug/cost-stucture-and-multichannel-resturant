"""
Cost Structure & Multi-Channel Profitability Dashboard
SkyCity Auckland Restaurants & Bars

Run locally:   streamlit run app.py
"""

import io
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd

import streamlit as st

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Restaurant Profitability Dashboard",
    page_icon="🍽️",
    layout="wide",
)

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
CHANNELS = {
    "In-Store": {
        "revenue": "InStoreRevenue",
        "profit": "InStoreNetProfit",
        "orders": "InStoreOrders",
    },
    "Uber Eats": {
        "revenue": "UberEatsRevenue",
        "profit": "UberEatsNetProfit",
        "orders": "UberEatsOrders",
    },
    "DoorDash": {
        "revenue": "DoorDashRevenue",
        "profit": "DoorDashNetProfit",
        "orders": "DoorDashOrders",
    },
    "Self-Delivery": {
        "revenue": "SelfDeliveryRevenue",
        "profit": "SelfDeliveryNetProfit",
        "orders": "SelfDeliveryOrders",
    },
}

RATE_COLS = ["COGSRate", "OPEXRate", "CommissionRate"]
EXTRA_NUMERIC = ["DeliveryCostPerOrder", "SD_DeliveryTotalCost"]


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def show_fig(fig):
    """Render a matplotlib figure in Streamlit and free its memory."""
    st.pyplot(fig)
    plt.close(fig)


def need_columns(df, cols):
    """Return True if all columns exist, otherwise show an error."""
    missing = [c for c in cols if c not in df.columns]
    if missing:
        st.error(f"Missing columns in dataset: {missing}")
        return False
    return True


def safe_margin(profit, revenue):
    """Profit margin (%) with zero-revenue protection."""
    return np.where(revenue > 0, (profit / revenue) * 100, np.nan)


@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Convert numeric columns and normalise percentage-style rates."""
    d = df.copy()

    numeric_cols = list(RATE_COLS) + list(EXTRA_NUMERIC)
    for info in CHANNELS.values():
        numeric_cols += [info["revenue"], info["profit"], info["orders"]]

    for col in numeric_cols:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce")

    # Rates stored as 25 instead of 0.25 -> convert to decimals
    for col in RATE_COLS:
        if col in d.columns:
            valid = d[col].dropna()
            if not valid.empty and valid.median() > 1:
                d[col] = d[col] / 100

    return d


def find_default_csv():
    """Look for a CSV next to this script (useful on Streamlit Cloud)."""
    here = Path(__file__).parent
    csvs = sorted(here.glob("*.csv"))
    for p in csvs:
        if "skycity" in p.name.lower():
            return p
    return csvs[0] if csvs else None


def channel_totals(df):
    """Per-channel revenue / profit / orders / margin / profit-per-order."""
    rows = []
    for name, info in CHANNELS.items():
        rev = df[info["revenue"]].sum()
        prof = df[info["profit"]].sum()
        orders = df[info["orders"]].sum()
        rows.append(
            {
                "Channel": name,
                "Total Revenue": rev,
                "Total Net Profit": prof,
                "Total Orders": orders,
                "Profit Margin (%)": (prof / rev * 100) if rev else 0,
                "Revenue Per Order": (rev / orders) if orders else np.nan,
                "Profit Per Order": (prof / orders) if orders else np.nan,
            }
        )
    return pd.DataFrame(rows)


def add_restaurant_margins(df):
    """Add a '<Channel>_Margin' column for every channel."""
    d = df.copy()
    for name, info in CHANNELS.items():
        d[name + "_Margin"] = safe_margin(d[info["profit"]], d[info["revenue"]])
    return d


# ------------------------------------------------------------------
# SIDEBAR: DATA SOURCE + NAVIGATION
# ------------------------------------------------------------------
st.sidebar.title("🍽️ Profitability Dashboard")

uploaded = st.sidebar.file_uploader("Upload restaurant CSV", type=["csv"])

raw_df = None
if uploaded is not None:
    raw_df = load_csv(uploaded.getvalue())
else:
    default_csv = find_default_csv()
    if default_csv is not None:
        raw_df = load_csv(default_csv.read_bytes())
        st.sidebar.caption(f"Using bundled file: {default_csv.name}")

if raw_df is None:
    st.title("Cost Structure & Multi-Channel Profitability")
    st.info(
        "👈 Upload the **SkyCity Auckland Restaurants & Bars** CSV in the "
        "sidebar to begin. (Or place the CSV in the same folder as this "
        "script and it will load automatically.)"
    )
    st.stop()

df = prepare(raw_df)

PAGES = [
    "Overview & KPIs",
    "Channel Margin Analysis",
    "Cost Decomposition",
    "Commission & Delivery Impact",
    "Cuisine & Segment Profitability",
    "Volatility & Risk",
    "Calculation Validation",
    "KPI Cards",
]
page = st.sidebar.radio("Go to", PAGES)


# ------------------------------------------------------------------
# PAGE 1: OVERVIEW
# ------------------------------------------------------------------
def page_overview():
    st.title("Cost Structure & Multi-Channel Profitability")
    st.caption("SkyCity Auckland Restaurants & Bars")

    channel_cols = [c for info in CHANNELS.values() for c in info.values()]
    if not need_columns(df, channel_cols):
        return

    totals = channel_totals(df)
    total_revenue = totals["Total Revenue"].sum()
    total_profit = totals["Total Net Profit"].sum()
    total_orders = totals["Total Orders"].sum()
    margin = (total_profit / total_revenue * 100) if total_revenue else 0

    st.subheader("Overall KPIs")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", f"${total_revenue:,.2f}")
    c2.metric("Total Net Profit", f"${total_profit:,.2f}")
    c3.metric("Total Orders", f"{int(total_orders):,}")
    c4.metric("Overall Profit Margin", f"{margin:.2f}%")

    st.subheader("Dataset")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Duplicate Rows", int(df.duplicated().sum()))

    tab1, tab2, tab3 = st.tabs(["Preview", "Summary statistics", "Columns"])
    with tab1:
        st.dataframe(df.head(20))
    with tab2:
        st.dataframe(df.describe().round(2))
    with tab3:
        st.write(df.columns.tolist())


# ------------------------------------------------------------------
# PAGE 2: CHANNEL MARGIN ANALYSIS
# ------------------------------------------------------------------
def page_channel():
    st.title("Channel Margin Analysis")
    st.caption(
        "Net profit and margin per channel, and absolute profit vs margin efficiency."
    )

    channel_cols = [c for info in CHANNELS.values() for c in info.values()]
    if not need_columns(df, channel_cols):
        return

    totals = channel_totals(df)

    # KPI cards: net profit by channel
    st.subheader("Net Profit by Channel")
    cols = st.columns(4)
    for col, (_, row) in zip(cols, totals.iterrows()):
        col.metric(row["Channel"], f"${row['Total Net Profit'] / 1e6:.2f}M")

    st.subheader("Summary Table")
    st.dataframe(totals.round(2), hide_index=True)

    left, right = st.columns(2)

    with left:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(totals["Channel"], totals["Profit Margin (%)"])
        ax.set_title("Profit Margin Comparison by Channel")
        ax.set_xlabel("Sales Channel")
        ax.set_ylabel("Profit Margin (%)")
        ax.tick_params(axis="x", rotation=15)
        fig.tight_layout()
        show_fig(fig)

    with right:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(totals["Channel"], totals["Profit Per Order"])
        ax.axhline(0, linestyle="--", color="grey")
        ax.set_title("Net Profit per Order by Channel")
        ax.set_xlabel("Sales Channel")
        ax.set_ylabel("Net Profit per Order ($)")
        ax.tick_params(axis="x", rotation=15)
        fig.tight_layout()
        show_fig(fig)

    st.subheader("Absolute Profit vs Margin Efficiency")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].bar(totals["Channel"], totals["Total Net Profit"])
    axes[0].set_title("Absolute Profit by Channel")
    axes[0].set_xlabel("Sales Channel")
    axes[0].set_ylabel("Total Net Profit")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(totals["Channel"], totals["Profit Margin (%)"])
    axes[1].set_title("Margin Efficiency by Channel")
    axes[1].set_xlabel("Sales Channel")
    axes[1].set_ylabel("Profit Margin (%)")
    axes[1].tick_params(axis="x", rotation=20)

    fig.tight_layout()
    show_fig(fig)


# ------------------------------------------------------------------
# PAGE 3: COST DECOMPOSITION
# ------------------------------------------------------------------
def page_cost():
    st.title("Cost Components Decomposition")
    st.caption(
        "Revenue broken into COGS, OPEX, commission (Uber Eats / DoorDash) "
        "and delivery cost (Self-Delivery)."
    )

    if not need_columns(
        df, ["COGSRate", "OPEXRate", "CommissionRate", "SD_DeliveryTotalCost", "CuisineType"]
    ):
        return

    channel = st.selectbox("Select Channel", list(CHANNELS.keys()))
    info = CHANNELS[channel]
    rev_col, prof_col = info["revenue"], info["profit"]

    revenue = df[rev_col].sum()
    cogs = (df[rev_col] * df["COGSRate"]).sum()
    opex = (df[rev_col] * df["OPEXRate"]).sum()

    commission = 0.0
    delivery_cost = 0.0
    if channel in ["Uber Eats", "DoorDash"]:
        commission = (df[rev_col] * df["CommissionRate"]).sum()
    if channel == "Self-Delivery":
        delivery_cost = df["SD_DeliveryTotalCost"].sum()

    actual_profit = df[prof_col].sum()

    st.subheader(f"Cost Analysis: {channel}")
    summary = pd.DataFrame(
        {
            "Metric": ["Revenue", "COGS", "OPEX", "Commission", "Delivery Cost", "Net Profit"],
            "Amount": [revenue, cogs, opex, commission, delivery_cost, actual_profit],
        }
    )
    st.dataframe(summary.round(2), hide_index=True)

    # Cost components by cuisine
    cost_data = df[["CuisineType"]].copy()
    cost_data["COGS"] = df[rev_col] * df["COGSRate"]
    cost_data["OPEX"] = df[rev_col] * df["OPEXRate"]
    cost_data["Commission"] = 0.0
    cost_data["Delivery Cost"] = 0.0
    if channel in ["Uber Eats", "DoorDash"]:
        cost_data["Commission"] = df[rev_col] * df["CommissionRate"]
    if channel == "Self-Delivery":
        cost_data["Delivery Cost"] = df["SD_DeliveryTotalCost"]

    cuisine_costs = cost_data.groupby("CuisineType")[
        ["COGS", "OPEX", "Commission", "Delivery Cost"]
    ].sum()

    st.subheader("Cost Components by Cuisine Type")
    st.dataframe(cuisine_costs.round(2))

    fig, ax = plt.subplots(figsize=(12, 6))
    cuisine_costs.plot(kind="bar", ax=ax)
    ax.set_title(f"Cost Components by Cuisine Type - {channel}")
    ax.set_xlabel("Cuisine Type")
    ax.set_ylabel("Total Cost")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    show_fig(fig)

    # Waterfall
    labels = ["Revenue", "COGS", "OPEX"]
    values = [revenue, cogs, opex]
    if channel in ["Uber Eats", "DoorDash"]:
        labels.append("Commission")
        values.append(commission)
    if channel == "Self-Delivery":
        labels.append("Delivery Cost")
        values.append(delivery_cost)

    calculated_profit = revenue - sum(values[1:])

    st.subheader(f"Waterfall Chart: {channel}")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels[0], revenue)
    running = revenue
    for label, cost in zip(labels[1:], values[1:]):
        new_total = running - cost
        ax.bar(label, cost, bottom=new_total)
        running = new_total
    ax.bar("Calculated Profit", calculated_profit)
    ax.set_title(f"Waterfall Chart - {channel}")
    ax.set_xlabel("Revenue and Cost Components")
    ax.set_ylabel("Amount")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    show_fig(fig)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", f"${revenue:,.2f}")
    c2.metric("Calculated Profit", f"${calculated_profit:,.2f}")
    c3.metric("Net Profit (Dataset)", f"${actual_profit:,.2f}")


# ------------------------------------------------------------------
# PAGE 4: COMMISSION & DELIVERY IMPACT (replaces ipywidgets sliders)
# ------------------------------------------------------------------
def page_sensitivity():
    st.title("Commission & Delivery Cost Impact Analysis")
    st.caption(
        "Sensitivity of net profit to commission-rate changes and extra "
        "delivery cost per order, plus the Self-Delivery break-even point."
    )

    required = [
        "CommissionRate", "DeliveryCostPerOrder",
        "InStoreNetProfit", "UberEatsRevenue", "DoorDashRevenue",
        "UberEatsNetProfit", "DoorDashNetProfit",
        "SelfDeliveryOrders", "SelfDeliveryNetProfit",
    ]
    if not need_columns(df, required):
        return

    data = df.copy()
    for col in required:
        data[col] = data[col].fillna(0)

    c1, c2 = st.columns(2)
    with c1:
        commission_pts = st.slider(
            "Commission Change (percentage points)", -20, 20, 0, 1
        )
    with c2:
        extra_cost = st.slider("Extra Delivery Cost per Order ($)", 0.0, 10.0, 0.0, 0.5)

    # Current profit
    cur_instore = data["InStoreNetProfit"].sum()
    cur_uber = data["UberEatsNetProfit"].sum()
    cur_dd = data["DoorDashNetProfit"].sum()
    cur_sd = data["SelfDeliveryNetProfit"].sum()

    # Commission impact
    original_rate = data["CommissionRate"].clip(0, 1)

    def adjusted_profit(profit_col, rev_col, change_pct):
        new_rate = (original_rate + change_pct / 100).clip(0, 1)
        diff = new_rate - original_rate
        return (data[profit_col] - data[rev_col] * diff).sum()

    adj_uber = adjusted_profit("UberEatsNetProfit", "UberEatsRevenue", commission_pts)
    adj_dd = adjusted_profit("DoorDashNetProfit", "DoorDashRevenue", commission_pts)

    # Delivery cost impact
    total_sd_orders = data["SelfDeliveryOrders"].sum()
    adj_sd = cur_sd - total_sd_orders * extra_cost
    adj_instore = cur_instore

    # KPI cards
    st.subheader("Adjusted Profit (Key Performance Indicators)")
    k = st.columns(4)
    k[0].metric("In-Store", f"${adj_instore:,.0f}")
    k[1].metric("Uber Eats", f"${adj_uber:,.0f}", delta=f"{adj_uber - cur_uber:,.0f}")
    k[2].metric("DoorDash", f"${adj_dd:,.0f}", delta=f"{adj_dd - cur_dd:,.0f}")
    k[3].metric("Self-Delivery", f"${adj_sd:,.0f}", delta=f"{adj_sd - cur_sd:,.0f}")

    left, right = st.columns(2)

    # Commission sensitivity chart
    with left:
        changes = np.arange(-20, 21, 1)
        uber_s = [adjusted_profit("UberEatsNetProfit", "UberEatsRevenue", c) for c in changes]
        dd_s = [adjusted_profit("DoorDashNetProfit", "DoorDashRevenue", c) for c in changes]

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(changes, uber_s, label="Uber Eats", marker=".")
        ax.plot(changes, dd_s, label="DoorDash", marker=".")
        ax.axvline(commission_pts, linestyle="--", color="grey", label="Selected Change")
        ax.set_title("Commission Change vs Net Profit")
        ax.set_xlabel("Commission Change (Percentage Points)")
        ax.set_ylabel("Net Profit ($)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        show_fig(fig)

    # Delivery-cost sensitivity chart
    with right:
        costs = np.arange(0, 10.5, 0.5)
        sd_s = [cur_sd - total_sd_orders * c for c in costs]

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(costs, sd_s, marker="o", label="Self-Delivery Profit")
        ax.axhline(0, linestyle="--", color="grey", label="Break-even Profit")
        ax.axvline(extra_cost, linestyle=":", color="red", label="Selected Extra Cost")
        ax.set_title("Extra Delivery Cost vs Net Profit")
        ax.set_xlabel("Additional Cost Per Order ($)")
        ax.set_ylabel("Net Profit ($)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        show_fig(fig)

    # Four-channel comparison
    st.subheader("Four-Channel Profitability Comparison")
    comparison = pd.DataFrame(
        {
            "Channel": ["In-Store", "Uber Eats", "DoorDash", "Self-Delivery"],
            "Current Profit": [cur_instore, cur_uber, cur_dd, cur_sd],
            "Adjusted Profit": [adj_instore, adj_uber, adj_dd, adj_sd],
        }
    )
    comparison["Profit Change"] = comparison["Adjusted Profit"] - comparison["Current Profit"]
    st.dataframe(comparison.round(2), hide_index=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(comparison))
    w = 0.35
    ax.bar(x - w / 2, comparison["Current Profit"], w, label="Current Profit")
    ax.bar(x + w / 2, comparison["Adjusted Profit"], w, label="Adjusted Profit")
    ax.set_xticks(x)
    ax.set_xticklabels(comparison["Channel"])
    ax.set_title("Current vs Adjusted Profit by Channel")
    ax.set_xlabel("Sales Channel")
    ax.set_ylabel("Net Profit ($)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    show_fig(fig)

    # Break-even
    st.subheader("Self-Delivery Break-even Analysis")
    if total_sd_orders > 0:
        breakeven_extra = cur_sd / total_sd_orders
        weighted_cost = (
            data["DeliveryCostPerOrder"] * data["SelfDeliveryOrders"]
        ).sum() / total_sd_orders
        breakeven_total = weighted_cost + breakeven_extra

        b = st.columns(4)
        b[0].metric("Current SD Profit", f"${cur_sd:,.2f}")
        b[1].metric("Break-even Extra Cost / Order", f"${breakeven_extra:,.2f}")
        b[2].metric("Avg Current Delivery Cost / Order", f"${weighted_cost:,.2f}")
        b[3].metric("Break-even Total Cost / Order", f"${breakeven_total:,.2f}")

        if adj_sd > 0:
            st.success("Self-Delivery remains **profitable** under the selected cost increase.")
        elif np.isclose(adj_sd, 0):
            st.warning("Self-Delivery is at **break-even** under the selected cost increase.")
        else:
            st.error("Self-Delivery **operates at a loss** under the selected cost increase.")
    else:
        st.warning("No Self-Delivery orders found. Check the SelfDeliveryOrders column.")

    st.info(
        "In-Store profit is unchanged in this scenario. Uber Eats and DoorDash "
        "respond to commission changes; Self-Delivery responds to extra delivery cost."
    )


# ------------------------------------------------------------------
# PAGE 5: CUISINE & SEGMENT PROFITABILITY
# ------------------------------------------------------------------
def classify_margin(m):
    if pd.isna(m):
        return "Insufficient Revenue Data"
    if m >= 15:
        return "Margin-Resilient"
    if m < 0:
        return "Margin-Fragile"
    return "Moderate Margin"


def grouped_margins(data, group_col):
    agg = data.groupby(group_col, dropna=False).agg(
        InStoreRevenue=("InStoreRevenue", "sum"),
        InStoreProfit=("InStoreNetProfit", "sum"),
        UberEatsRevenue=("UberEatsRevenue", "sum"),
        UberEatsProfit=("UberEatsNetProfit", "sum"),
        DoorDashRevenue=("DoorDashRevenue", "sum"),
        DoorDashProfit=("DoorDashNetProfit", "sum"),
        SelfDeliveryRevenue=("SelfDeliveryRevenue", "sum"),
        SelfDeliveryProfit=("SelfDeliveryNetProfit", "sum"),
    ).reset_index()

    for prefix in ["InStore", "UberEats", "DoorDash", "SelfDelivery"]:
        agg[f"{prefix}Margin"] = safe_margin(agg[f"{prefix}Profit"], agg[f"{prefix}Revenue"])

    return agg[
        [group_col, "InStoreMargin", "UberEatsMargin", "DoorDashMargin", "SelfDeliveryMargin"]
    ]


def page_cuisine():
    st.title("Cuisine & Segment Profitability")
    st.caption(
        "Channel-wise margin by cuisine type and business segment (Cafe vs QSR). "
        "Identifies margin-resilient vs margin-fragile categories."
    )

    required = ["CuisineType", "Segment"] + [
        c for info in CHANNELS.values() for c in (info["revenue"], info["profit"])
    ]
    if not need_columns(df, required):
        return

    margin_cols = ["InStoreMargin", "UberEatsMargin", "DoorDashMargin", "SelfDeliveryMargin"]

    # ---- Cuisine ----
    st.subheader("Channel-wise Profit Margin by Cuisine")
    cuisine = grouped_margins(df, "CuisineType")
    st.dataframe(cuisine.round(2), hide_index=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    cuisine.set_index("CuisineType").plot(kind="bar", ax=ax)
    ax.set_title("Channel-Wise Profit Margin by Cuisine Type")
    ax.set_xlabel("Cuisine Type")
    ax.set_ylabel("Profit Margin (%)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.legend(title="Sales Channel")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    show_fig(fig)

    # ---- Segment ----
    st.subheader("Cafe vs QSR Profit Margin")
    segment = grouped_margins(df, "Segment")
    st.dataframe(segment.round(2), hide_index=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    segment.set_index("Segment").plot(kind="bar", ax=ax)
    ax.set_title("Profit Margin Comparison by Segment")
    ax.set_xlabel("Business Segment")
    ax.set_ylabel("Profit Margin (%)")
    plt.setp(ax.get_xticklabels(), rotation=0)
    ax.legend(title="Sales Channel")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    show_fig(fig)

    # ---- Resilience ----
    st.subheader("Margin Resilience Analysis")
    st.caption("Resilient: avg margin ≥ 15% · Fragile: avg margin < 0% · otherwise Moderate.")

    cuisine["AverageMargin"] = cuisine[margin_cols].mean(axis=1)
    cuisine["MarginCategory"] = cuisine["AverageMargin"].apply(classify_margin)

    segment["AverageMargin"] = segment[margin_cols].mean(axis=1)
    segment["MarginCategory"] = segment["AverageMargin"].apply(classify_margin)

    left, right = st.columns(2)
    with left:
        st.markdown("**By cuisine type**")
        st.dataframe(
            cuisine[["CuisineType", "AverageMargin", "MarginCategory"]]
            .sort_values("AverageMargin", ascending=False)
            .round(2),
            hide_index=True,
        )
    with right:
        st.markdown("**By business segment**")
        st.dataframe(
            segment[["Segment", "AverageMargin", "MarginCategory"]]
            .sort_values("AverageMargin", ascending=False)
            .round(2),
            hide_index=True,
        )


# ------------------------------------------------------------------
# PAGE 6: VOLATILITY & RISK
# ------------------------------------------------------------------
def assess_channel_risk(row):
    avg = row["Average Margin (%)"]
    std = row["Margin Std Dev (%)"]
    if pd.isna(avg):
        return "Insufficient Data"
    if avg < 0:
        return "High Risk: Negative Average Margin"
    if avg < 5:
        return "High Risk: Low Average Margin"
    if pd.isna(std):
        return "Insufficient Data"
    if std >= 15:
        return "High Variability"
    if std >= 8:
        return "Moderate Variability"
    return "Relatively Stable"


def page_risk():
    st.title("Profit Volatility & Risk Assessment")
    st.caption(
        "Margin variability across restaurants, unstable channels, "
        "and loss-prone channel strategies."
    )

    required = ["RestaurantID", "RestaurantName"] + [
        c for info in CHANNELS.values() for c in (info["revenue"], info["profit"])
    ]
    if not need_columns(df, required):
        return

    data = add_restaurant_margins(df)
    margin_cols = [ch + "_Margin" for ch in CHANNELS]

    # 1. Variability
    st.subheader("1. Margin Variability Across Restaurants")
    summary = data[margin_cols].agg(["mean", "std", "min", "max", "median"]).T
    summary = summary.rename(
        columns={
            "mean": "Average Margin (%)",
            "std": "Margin Std Dev (%)",
            "min": "Minimum Margin (%)",
            "max": "Maximum Margin (%)",
            "median": "Median Margin (%)",
        }
    )
    summary.index = [c.replace("_Margin", "") for c in summary.index]
    summary["Restaurants Analysed"] = [data[c].count() for c in margin_cols]
    st.dataframe(summary.round(2))

    fig, ax = plt.subplots(figsize=(10, 6))
    box_data = [data[ch + "_Margin"].dropna() for ch in CHANNELS]
    ax.boxplot(box_data, showmeans=True)
    ax.set_xticks(range(1, len(CHANNELS) + 1))
    ax.set_xticklabels(list(CHANNELS.keys()))
    ax.axhline(0, linestyle="--", color="grey", label="Break-even Margin")
    ax.set_title("Profit Margin Variability Across Restaurants")
    ax.set_xlabel("Sales Channel")
    ax.set_ylabel("Profit Margin (%)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    show_fig(fig)

    # 2. Channel risk
    st.subheader("2. Channel Profitability Risk Assessment")
    channel_risk = summary[
        ["Average Margin (%)", "Margin Std Dev (%)", "Minimum Margin (%)", "Maximum Margin (%)"]
    ].copy()
    channel_risk["Risk Assessment"] = channel_risk.apply(assess_channel_risk, axis=1)
    st.dataframe(channel_risk.round(2))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(channel_risk.index, channel_risk["Margin Std Dev (%)"])
    ax.set_title("Profit Margin Variability by Channel")
    ax.set_xlabel("Sales Channel")
    ax.set_ylabel("Margin Standard Deviation (%)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    show_fig(fig)

    # 3. Risk flags
    records = []
    for ch, info in CHANNELS.items():
        cd = data[["RestaurantID", "RestaurantName", info["revenue"], info["profit"], ch + "_Margin"]].copy()
        cd["Channel"] = ch
        cd = cd.rename(
            columns={
                info["revenue"]: "Revenue",
                info["profit"]: "Net Profit",
                ch + "_Margin": "Profit Margin (%)",
            }
        )
        cd = cd[cd["Revenue"] > 0].copy()
        cd["Risk Category"] = np.select(
            [
                cd["Profit Margin (%)"] < 0,
                cd["Profit Margin (%)"] < 5,
                cd["Profit Margin (%)"] < 15,
            ],
            ["Loss-Prone", "High Risk", "Moderate Risk"],
            default="Relatively Healthy",
        )
        records.append(cd)

    risk_df = pd.concat(records, ignore_index=True).sort_values("Profit Margin (%)")

    loss_prone = risk_df[risk_df["Profit Margin (%)"] < 0]
    high_risk = risk_df[risk_df["Risk Category"].isin(["Loss-Prone", "High Risk"])]

    st.subheader("3. Loss-Prone Channel Strategies")
    if loss_prone.empty:
        st.success("No loss-making restaurant-channel combinations were found.")
    else:
        st.dataframe(loss_prone.round(2), hide_index=True)

    st.subheader("4. All Loss-Prone and High-Risk Strategies")
    if high_risk.empty:
        st.success("No restaurant-channel combinations met the high-risk thresholds.")
    else:
        st.dataframe(high_risk.round(2), hide_index=True)

    # 5. Lowest 10
    if not risk_df.empty:
        st.subheader("5. Ten Lowest Profit Margins by Restaurant and Channel")
        lowest = risk_df.head(10).copy()
        lowest["Restaurant-Channel"] = lowest["RestaurantName"].astype(str) + " - " + lowest["Channel"]

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.barh(lowest["Restaurant-Channel"], lowest["Profit Margin (%)"])
        ax.axvline(0, linestyle="--", color="grey", label="Break-even Margin")
        ax.set_title("10 Lowest Profit Margins by Restaurant and Channel")
        ax.set_xlabel("Profit Margin (%)")
        ax.set_ylabel("Restaurant and Channel")
        ax.legend()
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        show_fig(fig)

    st.subheader("6. Risk Category Counts by Channel")
    st.dataframe(pd.crosstab(risk_df["Channel"], risk_df["Risk Category"]))

    # Final summary
    st.subheader("Business Summary")
    avg = channel_risk["Average Margin (%)"].dropna()
    std = channel_risk["Margin Std Dev (%)"].dropna()
    lines = []
    if not avg.empty:
        lines.append(f"- **Highest average margin channel:** {avg.idxmax()}")
        lines.append(f"- **Lowest average margin channel:** {avg.idxmin()}")
    if not std.empty:
        lines.append(f"- **Highest margin variability:** {std.idxmax()}")
    lines.append(f"- **Loss-prone restaurant-channel combinations:** {len(loss_prone)}")
    lines.append(f"- **High-risk restaurant-channel combinations:** {len(high_risk)}")
    st.markdown("\n".join(lines))


# ------------------------------------------------------------------
# PAGE 7: CALCULATION VALIDATION
# ------------------------------------------------------------------
def page_validation():
    st.title("Project Calculation Validation")
    st.caption("Provided vs estimated profit, per-order normalisation, and margin outliers.")

    required = ["RestaurantID", "RestaurantName"] + [
        c for info in CHANNELS.values() for c in info.values()
    ]
    if not need_columns(df, required):
        return

    data = df.copy()

    # ---- 1. Provided vs estimated profit ----
    st.subheader("1. Provided vs Estimated Profit")
    st.caption(
        "Assumed formulas — In-Store: Rev×(1−COGS−OPEX); Aggregators: also minus "
        "Commission; Self-Delivery: Rev×(1−COGS−OPEX) − Orders×DeliveryCostPerOrder. "
        "Confirm these against your dataset's original methodology."
    )

    cost_cols = ["COGSRate", "OPEXRate", "CommissionRate", "DeliveryCostPerOrder"]
    missing = [c for c in cost_cols if c not in data.columns]

    if missing:
        st.warning(f"Profit recalculation is not possible. Missing cost columns: {missing}")
    else:
        records = []
        for ch, info in CHANNELS.items():
            rev = data[info["revenue"]]
            prof = data[info["profit"]]
            orders = data[info["orders"]]

            if ch == "In-Store":
                est = rev * (1 - data["COGSRate"] - data["OPEXRate"])
            elif ch in ["Uber Eats", "DoorDash"]:
                est = rev * (1 - data["COGSRate"] - data["OPEXRate"] - data["CommissionRate"])
            else:
                est = rev * (1 - data["COGSRate"] - data["OPEXRate"]) - orders * data["DeliveryCostPerOrder"]

            cmp_df = pd.DataFrame(
                {"Provided Profit": prof, "Estimated Profit": est, "Difference": prof - est}
            ).dropna()

            if not cmp_df.empty:
                records.append(
                    {
                        "Channel": ch,
                        "Restaurants Compared": len(cmp_df),
                        "Provided Total Profit": cmp_df["Provided Profit"].sum(),
                        "Estimated Total Profit": cmp_df["Estimated Profit"].sum(),
                        "Total Difference": cmp_df["Difference"].sum(),
                        "Average Absolute Difference": cmp_df["Difference"].abs().mean(),
                        "Matching Rows": int((cmp_df["Difference"].abs() < 0.01).sum()),
                    }
                )

        validation = pd.DataFrame(records)
        if validation.empty:
            st.info("No valid records available for profit validation.")
        else:
            st.dataframe(validation.round(2), hide_index=True)

            fig, ax = plt.subplots(figsize=(10, 5))
            x = np.arange(len(validation))
            w = 0.35
            ax.bar(x - w / 2, validation["Provided Total Profit"], w, label="Provided Profit")
            ax.bar(x + w / 2, validation["Estimated Total Profit"], w, label="Estimated Profit")
            ax.set_xticks(x)
            ax.set_xticklabels(validation["Channel"], rotation=15)
            ax.set_title("Provided vs Estimated Profit")
            ax.set_xlabel("Sales Channel")
            ax.set_ylabel("Total Profit")
            ax.legend()
            fig.tight_layout()
            show_fig(fig)

    # ---- 2. Per-order ----
    st.subheader("2. Profit Per Order Comparison")
    records = []
    for ch, info in CHANNELS.items():
        cd = data[[info["revenue"], info["profit"], info["orders"]]].dropna()
        cd = cd[cd[info["orders"]] > 0]
        orders = cd[info["orders"]].sum()
        rev = cd[info["revenue"]].sum()
        prof = cd[info["profit"]].sum()
        records.append(
            {
                "Channel": ch,
                "Total Orders": orders,
                "Total Revenue": rev,
                "Total Net Profit": prof,
                "Revenue Per Order": rev / orders if orders > 0 else np.nan,
                "Profit Per Order": prof / orders if orders > 0 else np.nan,
            }
        )
    per_order = pd.DataFrame(records)
    st.dataframe(per_order.round(2), hide_index=True)

    plot_data = per_order.dropna(subset=["Profit Per Order"])
    if not plot_data.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(plot_data["Channel"], plot_data["Profit Per Order"])
        ax.axhline(0, linestyle="--", color="grey", label="Break-even")
        ax.set_title("Net Profit Per Order by Channel")
        ax.set_xlabel("Sales Channel")
        ax.set_ylabel("Profit Per Order")
        ax.legend()
        fig.tight_layout()
        show_fig(fig)

    # ---- 3. Outliers ----
    st.subheader("3. Extreme Profit-Margin Outliers (IQR method)")
    data = add_restaurant_margins(data)

    outlier_frames = []
    for ch in CHANNELS:
        col = ch + "_Margin"
        margins = data[col].dropna()
        if len(margins) < 4:
            st.info(f"Not enough data for outlier analysis: {ch}")
            continue

        q1, q3 = margins.quantile(0.25), margins.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        mask = (data[col] < lower) | (data[col] > upper)
        out = data.loc[mask, ["RestaurantID", "RestaurantName", col]].copy()
        out = out.rename(columns={col: "Profit Margin (%)"})
        out["Channel"] = ch
        out["Lower Limit (%)"] = lower
        out["Upper Limit (%)"] = upper
        out["Outlier Type"] = np.where(
            out["Profit Margin (%)"] < lower, "Extreme Low Margin", "Extreme High Margin"
        )
        outlier_frames.append(out)

    outliers = pd.concat(outlier_frames, ignore_index=True) if outlier_frames else pd.DataFrame()

    if outliers.empty:
        st.success("No extreme margin outliers detected.")
    else:
        outliers = outliers.sort_values("Profit Margin (%)")[
            ["RestaurantID", "RestaurantName", "Channel", "Profit Margin (%)",
             "Lower Limit (%)", "Upper Limit (%)", "Outlier Type"]
        ]
        st.dataframe(outliers.round(2), hide_index=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot([data[ch + "_Margin"].dropna() for ch in CHANNELS], showmeans=True)
    ax.set_xticks(range(1, len(CHANNELS) + 1))
    ax.set_xticklabels(list(CHANNELS.keys()))
    ax.axhline(0, linestyle="--", color="grey", label="Break-even Margin")
    ax.set_title("Profit Margin Outlier Analysis")
    ax.set_xlabel("Sales Channel")
    ax.set_ylabel("Profit Margin (%)")
    ax.legend()
    fig.tight_layout()
    show_fig(fig)

    # ---- Summary ----
    st.subheader("Final Summary")
    if not plot_data.empty:
        best = plot_data.loc[plot_data["Profit Per Order"].idxmax(), "Channel"]
        worst = plot_data.loc[plot_data["Profit Per Order"].idxmin(), "Channel"]
        st.markdown(
            f"- **Highest profit per order:** {best}\n"
            f"- **Lowest profit per order:** {worst}\n"
            f"- **Total margin outliers:** {len(outliers)}"
        )


# ------------------------------------------------------------------
# PAGE 8: KPI CARDS
# ------------------------------------------------------------------
def page_kpi():
    st.title("KPI Cards")

    required = ["CommissionRate", "DeliveryCostPerOrder"] + [
        c for info in CHANNELS.values() for c in info.values()
    ]
    if not need_columns(df, required):
        return

    data = df.copy()
    for col in required:
        data[col] = data[col].fillna(0)

    selected = st.selectbox("Channel", ["All Channels"] + list(CHANNELS.keys()))
    selected_channels = list(CHANNELS.keys()) if selected == "All Channels" else [selected]

    total_rev = total_profit = total_orders = 0.0
    commission_cost = delivery_cost = sd_profit = 0.0
    all_margins = []

    for ch in selected_channels:
        info = CHANNELS[ch]
        rev = data[info["revenue"]]
        prof = data[info["profit"]]
        orders = data[info["orders"]]

        total_rev += rev.sum()
        total_profit += prof.sum()
        total_orders += orders.sum()

        margins = (
            (prof / rev.replace(0, np.nan) * 100)
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        all_margins.extend(margins.tolist())

        if ch in ["Uber Eats", "DoorDash"]:
            commission_cost += (rev * data["CommissionRate"]).sum()
        if ch == "Self-Delivery":
            delivery_cost += (orders * data["DeliveryCostPerOrder"]).sum()
            sd_profit += prof.sum()

    profit_per_order = total_profit / total_orders if total_orders > 0 else 0
    margin = total_profit / total_rev * 100 if total_rev > 0 else 0
    commission_drag = commission_cost / total_rev * 100 if total_rev > 0 else 0
    sd_roi = sd_profit / delivery_cost * 100 if delivery_cost > 0 else np.nan
    volatility = np.std(all_margins, ddof=1) if len(all_margins) > 1 else 0

    if selected in ("Self-Delivery", "All Channels") and pd.notna(sd_roi):
        roi_text = f"{sd_roi:.2f}%"
    else:
        roi_text = "N/A"

    row1 = st.columns(3)
    row1[0].metric("Total Net Profit", f"${total_profit:,.2f}")
    row1[1].metric("Net Profit per Order", f"${profit_per_order:,.2f}")
    row1[2].metric("Channel Margin", f"{margin:.2f}%")

    row2 = st.columns(3)
    row2[0].metric("Commission Drag Index", f"{commission_drag:.2f}%")
    row2[1].metric("Self-Delivery ROI", roi_text)
    row2[2].metric("Profit Volatility Score", f"{volatility:.2f}")


# ------------------------------------------------------------------
# ROUTER
# ------------------------------------------------------------------
ROUTES = {
    "Overview & KPIs": page_overview,
    "Channel Margin Analysis": page_channel,
    "Cost Decomposition": page_cost,
    "Commission & Delivery Impact": page_sensitivity,
    "Cuisine & Segment Profitability": page_cuisine,
    "Volatility & Risk": page_risk,
    "Calculation Validation": page_validation,
    "KPI Cards": page_kpi,
}

ROUTES[page]()
