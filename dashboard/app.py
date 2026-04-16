"""
Green Grid — neighborhood solar dashboard.

Run with::

    streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SIM_DIR = os.path.join(ROOT, "simulation")

WEALTH_ORDER = ["LOW", "MIDDLE", "HIGH", "LUXURY"]
TYPE_ORDER = ["STUDIO", "SMALL", "LARGE"]
WEALTH_COLORS = {"LOW": "#6366f1", "MIDDLE": "#10b981", "HIGH": "#f59e0b", "LUXURY": "#ef4444"}
TYPE_COLORS = {"STUDIO": "#60a5fa", "SMALL": "#34d399", "LARGE": "#f472b6"}

st.set_page_config(
    page_title="Green Grid Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_all(data_dir: str):
    def _read(name: str, **kw):
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            return None
        return pd.read_csv(path, **kw)

    manifest_path = os.path.join(data_dir, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    return {
        "ticks": _read("ticks.csv", parse_dates=["timestamp"]),
        "system": _read("system.csv", parse_dates=["timestamp"]),
        "households": _read("households.csv"),
        "daily": _read("daily_by_household.csv", parse_dates=["date"]),
        "hourly_seg": _read("hourly_by_segment.csv"),
        "hourly_neigh": _read("hourly_neighborhood.csv"),
        "segment": _read("segment_summary.csv"),
        "adoption": _read("adoption.csv"),
        "manifest": manifest,
    }


def run_simulation(scenario: str) -> bool:
    env = os.environ.copy()
    env["GG_SCENARIO"] = scenario
    with st.spinner(f"Running simulation (scenario={scenario})…"):
        result = subprocess.run(
            [sys.executable, "simulation.py"],
            cwd=SIM_DIR,
            env=env,
            capture_output=True,
            text=True,
        )
    if result.returncode != 0:
        st.error("Simulation failed.")
        st.code(result.stderr or result.stdout)
        return False
    st.cache_data.clear()
    return True


def kpi(label, value, delta=None, help=None):
    st.metric(label, value, delta=delta, help=help)


def resample_agg(df: pd.DataFrame, freq: str, ts_col: str, agg: dict) -> pd.DataFrame:
    """Resample a tidy time-indexed frame. `agg` maps column → aggregation."""
    if df is None or df.empty:
        return df
    out = df.set_index(ts_col).resample(freq).agg(agg).reset_index()
    return out


FREQ_MAP = {
    "Hour": "h",
    "Day": "D",
    "Week": "W-MON",
    "Month": "MS",
    "Quarter": "QS",
    "Year": "YS",
}


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
def sidebar(data) -> dict:
    st.sidebar.title("⚡ Green Grid")
    mf = data["manifest"]
    if mf:
        st.sidebar.caption(
            f"Scenario: **{mf.get('scenario', '?')}**  ·  "
            f"{mf.get('n_households', '?')} houses  ·  "
            f"generated {mf.get('generated_at', '?')[:16].replace('T', ' ')}"
        )

    st.sidebar.header("Simulation")
    scenario = st.sidebar.selectbox(
        "Scenario", ["baseline", "high_adoption", "low_adoption"],
        index=["baseline", "high_adoption", "low_adoption"].index(
            mf.get("scenario", "baseline") if mf.get("scenario") in
            {"baseline", "high_adoption", "low_adoption"} else "baseline"),
    )
    run_col, _ = st.sidebar.columns([1, 1])
    if run_col.button("🔄 Run simulation", width="stretch"):
        if run_simulation(scenario):
            st.rerun()

    if data["households"] is None:
        return {}

    st.sidebar.header("Filters")
    hh = data["households"]
    types = [t for t in TYPE_ORDER if t in hh["type"].unique()]
    wealths = [w for w in WEALTH_ORDER if w in hh["wealth"].unique()]
    strategies = sorted(hh["strategy"].unique())

    sel_types = st.sidebar.multiselect("Household type", types, default=types)
    sel_wealths = st.sidebar.multiselect("Wealth level", wealths, default=wealths)
    sel_strats = st.sidebar.multiselect("Charge strategy", strategies, default=strategies)
    solar_filter = st.sidebar.radio("Solar adoption", ["All", "Only solar", "Only non-solar"], horizontal=True)
    battery_filter = st.sidebar.radio("Battery", ["All", "Only battery", "Only non-battery"], horizontal=True)

    sys_df = data["system"]
    min_d = pd.to_datetime(sys_df["timestamp"]).min().date()
    max_d = pd.to_datetime(sys_df["timestamp"]).max().date()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_d, max_d

    granularity = st.sidebar.selectbox(
        "Time granularity", list(FREQ_MAP.keys()), index=1,
    )

    return dict(
        scenario=scenario,
        sel_types=sel_types,
        sel_wealths=sel_wealths,
        sel_strats=sel_strats,
        solar_filter=solar_filter,
        battery_filter=battery_filter,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )


def apply_filters(data, f):
    hh = data["households"]
    mask = (hh["type"].isin(f["sel_types"]) &
            hh["wealth"].isin(f["sel_wealths"]) &
            hh["strategy"].isin(f["sel_strats"]))
    if f["solar_filter"] == "Only solar":
        mask &= hh["has_solar"]
    elif f["solar_filter"] == "Only non-solar":
        mask &= ~hh["has_solar"]
    if f["battery_filter"] == "Only battery":
        mask &= hh["has_battery"]
    elif f["battery_filter"] == "Only non-battery":
        mask &= ~hh["has_battery"]

    selected_ids = set(hh.loc[mask, "house_id"])
    selected_hh = hh[mask]

    ticks = data["ticks"]
    ts_mask = (
        ticks["house_id"].isin(selected_ids)
        & (ticks["timestamp"].dt.date >= f["start_date"])
        & (ticks["timestamp"].dt.date <= f["end_date"])
    )
    ft = ticks[ts_mask]

    daily = data["daily"]
    d_mask = (
        daily["house_id"].isin(selected_ids)
        & (daily["date"].dt.date >= f["start_date"])
        & (daily["date"].dt.date <= f["end_date"])
    )
    fd = daily[d_mask]

    return selected_hh, ft, fd


# ─────────────────────────────────────────────────────────────────────────────
# Tab renderers
# ─────────────────────────────────────────────────────────────────────────────
def tab_overview(sel_hh, ft, fd, f, data):
    st.subheader("Neighborhood at a glance")

    total_gen = ft["generation_kWh"].sum()
    total_load = ft["load_kWh"].sum()
    total_self = ft["self_consumption_kWh"].sum()
    total_imp = ft["grid_imports_kWh"].sum()
    total_exp = ft["grid_exports_kWh"].sum()
    import_cost = data["manifest"].get("import_cost", 0.75)
    export_cost = data["manifest"].get("export_cost", 0.90)
    cost = total_imp * import_cost
    credit = total_exp * export_cost
    balance = credit - cost
    savings = ft["tick_savings"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Households in view", f"{sel_hh.shape[0]}")
    with c2: kpi("Solar homes", f"{int(sel_hh['has_solar'].sum())}",
                 f"{(sel_hh['has_solar'].mean()*100 if len(sel_hh) else 0):.0f}%")
    with c3: kpi("Battery homes", f"{int(sel_hh['has_battery'].sum())}",
                 f"{(sel_hh['has_battery'].mean()*100 if len(sel_hh) else 0):.0f}%")
    with c4: kpi("Avg cloud cover", f"{data['system']['cloud_coverage'].mean():.2f}")

    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi("Total generation", f"{total_gen:,.0f} kWh")
    with c6: kpi("Total consumption", f"{total_load:,.0f} kWh")
    with c7: kpi("Self-consumption",
                 f"{total_self:,.0f} kWh",
                 f"{(total_self / total_load * 100 if total_load else 0):.1f}% of load")
    with c8: kpi("Net grid flow",
                 f"{(total_exp - total_imp):+,.0f} kWh",
                 f"imports {total_imp:,.0f} / exports {total_exp:,.0f}")

    c9, c10, c11 = st.columns(3)
    with c9: kpi("Import cost", f"$ {cost:,.0f}")
    with c10: kpi("Export credit", f"$ {credit:,.0f}")
    with c11: kpi("Net balance", f"$ {balance:,.0f}",
                  f"savings vs no-solar baseline: ${savings:,.0f}")

    st.markdown("#### Production vs. consumption over time")
    freq = FREQ_MAP[f["granularity"]]
    by_time = (ft.set_index("timestamp")
                  .resample(freq)
                  .agg(generation_kWh=("generation_kWh", "sum"),
                       load_kWh=("load_kWh", "sum"),
                       grid_imports_kWh=("grid_imports_kWh", "sum"),
                       grid_exports_kWh=("grid_exports_kWh", "sum"))
                  .reset_index())
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=by_time["timestamp"], y=by_time["load_kWh"],
                             mode="lines", name="Consumption", line=dict(color="#ef4444", width=2)))
    fig.add_trace(go.Scatter(x=by_time["timestamp"], y=by_time["generation_kWh"],
                             mode="lines", name="Production", line=dict(color="#10b981", width=2),
                             fill="tozeroy", fillcolor="rgba(16,185,129,0.15)"))
    fig.update_layout(height=360, hovermode="x unified",
                      yaxis_title="kWh", xaxis_title=None, margin=dict(t=20, b=30))
    st.plotly_chart(fig, width="stretch")

    c_a, c_b = st.columns(2)

    with c_a:
        st.markdown("#### Grid flow (imports vs exports)")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=by_time["timestamp"], y=by_time["grid_exports_kWh"],
                              name="Exports", marker_color="#10b981"))
        fig2.add_trace(go.Bar(x=by_time["timestamp"], y=-by_time["grid_imports_kWh"],
                              name="Imports", marker_color="#ef4444"))
        fig2.update_layout(barmode="relative", height=320, yaxis_title="kWh",
                           xaxis_title=None, margin=dict(t=20, b=30))
        st.plotly_chart(fig2, width="stretch")

    with c_b:
        st.markdown("#### Surplus vs. deficit (gen − load)")
        by_time["net"] = by_time["generation_kWh"] - by_time["load_kWh"]
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=by_time["timestamp"], y=by_time["net"], mode="lines",
            fill="tozeroy", name="Net",
            line=dict(color="#6366f1", width=2),
            fillcolor="rgba(99,102,241,0.2)",
        ))
        fig3.add_hline(y=0, line_dash="dash", line_color="rgba(0,0,0,0.3)")
        fig3.update_layout(height=320, yaxis_title="kWh",
                           xaxis_title=None, margin=dict(t=20, b=30))
        st.plotly_chart(fig3, width="stretch")


def tab_duck(sel_hh, ft, fd, f, data):
    st.subheader("Duck curve — net load by hour of day")
    st.caption(
        "The classic 'duck' shape: load stays high through the day, "
        "but midday solar pushes *net load* (what the grid has to serve) down "
        "— then demand shoots back up at dusk when the sun sets."
    )

    group_by = st.radio("Group by", ["Neighborhood total", "Household type", "Wealth level"],
                        horizontal=True)

    # Recompute on the fly from filtered ticks, so granularity + date filters
    # are respected.
    hod = (ft.assign(hour=ft["timestamp"].dt.hour)
             .groupby(["hour"], as_index=False)
             .agg(gen=("generation_kWh", "mean"),
                  load=("load_kWh", "mean")))
    hod["net"] = hod["load"] - hod["gen"]

    fig = go.Figure()
    if group_by == "Neighborhood total":
        fig.add_trace(go.Scatter(x=hod["hour"], y=hod["load"],
                                 mode="lines+markers", name="Gross load",
                                 line=dict(color="#ef4444", width=2, dash="dot")))
        fig.add_trace(go.Scatter(x=hod["hour"], y=hod["gen"],
                                 mode="lines+markers", name="Solar generation",
                                 line=dict(color="#f59e0b", width=2, dash="dot")))
        fig.add_trace(go.Scatter(x=hod["hour"], y=hod["net"],
                                 mode="lines+markers", name="Net load (the duck)",
                                 line=dict(color="#1f2937", width=4)))
    else:
        dim = "type" if group_by == "Household type" else "wealth"
        order = TYPE_ORDER if dim == "type" else WEALTH_ORDER
        palette = TYPE_COLORS if dim == "type" else WEALTH_COLORS
        grp = (ft.assign(hour=ft["timestamp"].dt.hour)
                 .groupby(["hour", dim], as_index=False)
                 .agg(gen=("generation_kWh", "mean"),
                      load=("load_kWh", "mean")))
        grp["net"] = grp["load"] - grp["gen"]
        for g in order:
            sub = grp[grp[dim] == g]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["hour"], y=sub["net"], mode="lines+markers",
                name=g, line=dict(color=palette[g], width=3),
            ))

    fig.update_layout(height=440, xaxis_title="Hour of day",
                      yaxis_title="Net load per household (kWh / tick)",
                      hovermode="x unified", margin=dict(t=20, b=30),
                      xaxis=dict(tickmode="linear", dtick=1))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(0,0,0,0.3)")
    st.plotly_chart(fig, width="stretch")

    # Peak / trough callout
    peak_hour = int(hod.loc[hod["net"].idxmax(), "hour"])
    trough_hour = int(hod.loc[hod["net"].idxmin(), "hour"])
    gen_peak_hour = int(hod.loc[hod["gen"].idxmax(), "hour"])
    c1, c2, c3 = st.columns(3)
    with c1: kpi("Peak net-load hour", f"{peak_hour:02d}:00")
    with c2: kpi("Lowest net-load hour", f"{trough_hour:02d}:00",
                 "grid pressure is lowest here")
    with c3: kpi("Peak production hour", f"{gen_peak_hour:02d}:00")


def tab_by_type(sel_hh, ft, fd, f, data):
    st.subheader("Breakdown by household type")

    seg = (fd.groupby("type", as_index=False)
             .agg(houses=("house_id", "nunique"),
                  generation_kWh=("generation_kWh", "sum"),
                  load_kWh=("load_kWh", "sum"),
                  self_consumption_kWh=("self_consumption_kWh", "sum"),
                  imports_kWh=("grid_imports_kWh", "sum"),
                  exports_kWh=("grid_exports_kWh", "sum"),
                  savings=("savings", "sum")))
    # Per-household normalization
    for col in ["generation_kWh", "load_kWh", "self_consumption_kWh",
                "imports_kWh", "exports_kWh", "savings"]:
        seg[f"{col}_per_home"] = seg[col] / seg["houses"].replace(0, 1)

    normalize = st.checkbox("Show per-household averages", value=True)
    suffix = "_per_home" if normalize else ""

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Production vs. consumption")
        plot_df = seg.melt(
            id_vars="type",
            value_vars=[f"generation_kWh{suffix}", f"load_kWh{suffix}"],
            var_name="series", value_name="kWh",
        )
        plot_df["series"] = plot_df["series"].map({
            f"generation_kWh{suffix}": "Generation",
            f"load_kWh{suffix}": "Consumption",
        })
        fig = px.bar(plot_df, x="type", y="kWh", color="series", barmode="group",
                     color_discrete_map={"Generation": "#10b981", "Consumption": "#ef4444"},
                     category_orders={"type": TYPE_ORDER})
        fig.update_layout(height=340, margin=dict(t=20, b=30))
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Hour-of-day load heatmap")
        heat = (ft.assign(hour=ft["timestamp"].dt.hour)
                  .groupby(["type", "hour"], as_index=False)
                  .agg(load=("load_kWh", "mean")))
        heat_pivot = heat.pivot(index="type", columns="hour", values="load").reindex(TYPE_ORDER)
        fig_h = px.imshow(heat_pivot, aspect="auto", color_continuous_scale="Reds",
                          labels=dict(x="Hour", y="Type", color="kWh"))
        fig_h.update_layout(height=340, margin=dict(t=20, b=30))
        st.plotly_chart(fig_h, width="stretch")

    st.markdown("##### Daily load distribution per type")
    fig_box = px.box(fd, x="type", y="load_kWh", color="type",
                     color_discrete_map=TYPE_COLORS,
                     category_orders={"type": TYPE_ORDER},
                     points=False)
    fig_box.update_layout(showlegend=False, height=340, margin=dict(t=20, b=30),
                          yaxis_title="Daily consumption (kWh)")
    st.plotly_chart(fig_box, width="stretch")

    st.markdown("##### Segment numbers")
    show_cols = ["type", "houses",
                 f"generation_kWh{suffix}", f"load_kWh{suffix}",
                 f"self_consumption_kWh{suffix}",
                 f"imports_kWh{suffix}", f"exports_kWh{suffix}",
                 f"savings{suffix}"]
    st.dataframe(
        seg[show_cols].round(1),
        hide_index=True, width="stretch",
    )


def tab_by_wealth(sel_hh, ft, fd, f, data):
    st.subheader("Breakdown by wealth level")

    seg = (fd.groupby("wealth", as_index=False)
             .agg(houses=("house_id", "nunique"),
                  generation_kWh=("generation_kWh", "sum"),
                  load_kWh=("load_kWh", "sum"),
                  self_consumption_kWh=("self_consumption_kWh", "sum"),
                  imports_kWh=("grid_imports_kWh", "sum"),
                  exports_kWh=("grid_exports_kWh", "sum"),
                  cost=("cost", "sum"),
                  savings=("savings", "sum")))
    seg["net_$"] = seg["exports_kWh"] * data["manifest"].get("export_cost", 0.9) \
                 - seg["imports_kWh"] * data["manifest"].get("import_cost", 0.75)
    seg["savings_per_home"] = seg["savings"] / seg["houses"].replace(0, 1)
    seg = seg.set_index("wealth").reindex(WEALTH_ORDER).dropna(how="all").reset_index()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Production vs. consumption (totals)")
        plot_df = seg.melt(
            id_vars="wealth",
            value_vars=["generation_kWh", "load_kWh"],
            var_name="series", value_name="kWh",
        )
        plot_df["series"] = plot_df["series"].map({
            "generation_kWh": "Generation", "load_kWh": "Consumption",
        })
        fig = px.bar(plot_df, x="wealth", y="kWh", color="series", barmode="group",
                     color_discrete_map={"Generation": "#10b981", "Consumption": "#ef4444"},
                     category_orders={"wealth": WEALTH_ORDER})
        fig.update_layout(height=340, margin=dict(t=20, b=30))
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Average savings per household")
        fig_s = px.bar(seg, x="wealth", y="savings_per_home",
                       color="wealth", color_discrete_map=WEALTH_COLORS,
                       category_orders={"wealth": WEALTH_ORDER})
        fig_s.update_layout(showlegend=False, height=340, margin=dict(t=20, b=30),
                            yaxis_title="Savings per home ($)")
        st.plotly_chart(fig_s, width="stretch")

    st.markdown("##### Wealth × Type — net $ balance heatmap")
    pivot = (fd.groupby(["type", "wealth"], as_index=False)
               .agg(imp=("grid_imports_kWh", "sum"),
                    exp=("grid_exports_kWh", "sum")))
    pivot["net_$"] = (pivot["exp"] * data["manifest"].get("export_cost", 0.9)
                      - pivot["imp"] * data["manifest"].get("import_cost", 0.75))
    heat = pivot.pivot(index="type", columns="wealth", values="net_$")
    heat = heat.reindex(index=TYPE_ORDER, columns=WEALTH_ORDER)
    fig_h = px.imshow(heat, aspect="auto", color_continuous_scale="RdYlGn",
                      color_continuous_midpoint=0,
                      labels=dict(color="$"), text_auto=".0f")
    fig_h.update_layout(height=360, margin=dict(t=20, b=30))
    st.plotly_chart(fig_h, width="stretch")

    st.markdown("##### Numbers")
    st.dataframe(seg.round(1), hide_index=True, width="stretch")


def tab_economics(sel_hh, ft, fd, f, data):
    st.subheader("Economics & savings story")

    import_cost = data["manifest"].get("import_cost", 0.75)
    export_cost = data["manifest"].get("export_cost", 0.90)
    total_imp = ft["grid_imports_kWh"].sum()
    total_exp = ft["grid_exports_kWh"].sum()
    balance = total_exp * export_cost - total_imp * import_cost
    savings = ft["tick_savings"].sum()

    c1, c2, c3 = st.columns(3)
    with c1: kpi("Neighborhood net balance", f"$ {balance:,.0f}")
    with c2: kpi("Savings vs no-solar baseline", f"$ {savings:,.0f}")
    with c3:
        load = ft["load_kWh"].sum()
        baseline_cost = load * import_cost
        kpi("Counter-factual bill (all grid)", f"$ {baseline_cost:,.0f}",
            f"effective saving rate: {(savings/baseline_cost*100 if baseline_cost else 0):.1f}%")

    st.markdown("##### Cumulative savings over time")
    freq = FREQ_MAP[f["granularity"]]
    series = (ft.set_index("timestamp")
                .resample(freq)
                .agg(savings=("tick_savings", "sum"),
                     cost=("tick_cost", "sum"))
                .reset_index())
    series["cumulative_savings"] = series["savings"].cumsum()
    series["cumulative_cost"] = series["cost"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["timestamp"], y=series["cumulative_savings"],
                             mode="lines", name="Cumulative savings",
                             fill="tozeroy", line=dict(color="#10b981", width=3),
                             fillcolor="rgba(16,185,129,0.15)"))
    fig.add_trace(go.Scatter(x=series["timestamp"], y=series["cumulative_cost"],
                             mode="lines", name="Cumulative grid cost",
                             line=dict(color="#ef4444", width=2, dash="dot")))
    fig.update_layout(height=360, hovermode="x unified", yaxis_title="$",
                      margin=dict(t=20, b=30))
    st.plotly_chart(fig, width="stretch")

    c4, c5 = st.columns(2)
    with c4:
        st.markdown("##### Per-household monthly savings distribution")
        monthly = (fd.groupby(["house_id", "type", "wealth", "has_solar"], as_index=False)
                     .agg(savings=("savings", "sum")))
        fig_h = px.histogram(monthly, x="savings", color="has_solar", nbins=30,
                             color_discrete_map={True: "#10b981", False: "#94a3b8"},
                             labels={"has_solar": "Has solar", "savings": "Savings ($)"})
        fig_h.update_layout(height=320, barmode="overlay", margin=dict(t=20, b=30))
        fig_h.update_traces(opacity=0.7)
        st.plotly_chart(fig_h, width="stretch")

    with c5:
        st.markdown("##### Winners & losers by segment")
        seg_econ = (fd.groupby(["type", "wealth"], as_index=False)
                      .agg(houses=("house_id", "nunique"),
                           savings=("savings", "sum")))
        seg_econ["savings_per_home"] = seg_econ["savings"] / seg_econ["houses"].replace(0, 1)
        seg_econ["segment"] = seg_econ["type"] + " / " + seg_econ["wealth"]
        seg_econ = seg_econ.sort_values("savings_per_home")
        fig_b = px.bar(seg_econ, x="savings_per_home", y="segment",
                       orientation="h", color="savings_per_home",
                       color_continuous_scale="RdYlGn", color_continuous_midpoint=0)
        fig_b.update_layout(height=420, margin=dict(t=20, b=30),
                            xaxis_title="Monthly savings per home ($)",
                            yaxis_title=None, coloraxis_showscale=False)
        st.plotly_chart(fig_b, width="stretch")


def tab_adoption(sel_hh, ft, fd, f, data):
    st.subheader("Solar & battery adoption")

    hh = data["households"]
    adopt = (hh.groupby(["type", "wealth"], as_index=False)
               .agg(houses=("house_id", "count"),
                    solar=("has_solar", "sum"),
                    battery=("has_battery", "sum")))
    adopt["solar_pct"] = adopt["solar"] / adopt["houses"] * 100
    adopt["battery_pct"] = adopt["battery"] / adopt["houses"] * 100

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Solar adoption rate (%) by type × wealth")
        solar_heat = adopt.pivot(index="type", columns="wealth", values="solar_pct") \
                          .reindex(index=TYPE_ORDER, columns=WEALTH_ORDER)
        fig = px.imshow(solar_heat, color_continuous_scale="YlOrBr",
                        text_auto=".0f", aspect="auto",
                        labels=dict(color="%"))
        fig.update_layout(height=360, margin=dict(t=20, b=30))
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Battery adoption rate (%) by type × wealth")
        batt_heat = adopt.pivot(index="type", columns="wealth", values="battery_pct") \
                         .reindex(index=TYPE_ORDER, columns=WEALTH_ORDER)
        fig2 = px.imshow(batt_heat, color_continuous_scale="Blues",
                         text_auto=".0f", aspect="auto",
                         labels=dict(color="%"))
        fig2.update_layout(height=360, margin=dict(t=20, b=30))
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### Adoption vs. per-home savings")
    adopt["segment"] = adopt["type"] + " / " + adopt["wealth"]
    seg_econ = (fd.groupby(["type", "wealth"], as_index=False)
                  .agg(houses=("house_id", "nunique"),
                       savings=("savings", "sum")))
    seg_econ["savings_per_home"] = seg_econ["savings"] / seg_econ["houses"].replace(0, 1)
    merged = adopt.merge(seg_econ[["type", "wealth", "savings_per_home"]],
                         on=["type", "wealth"])
    fig3 = px.scatter(merged, x="solar_pct", y="savings_per_home",
                      size="houses", color="wealth",
                      color_discrete_map=WEALTH_COLORS,
                      hover_name="segment",
                      labels={"solar_pct": "Solar adoption %",
                              "savings_per_home": "Monthly savings per home ($)"})
    fig3.update_layout(height=380, margin=dict(t=20, b=30))
    st.plotly_chart(fig3, width="stretch")


def tab_battery_grid(sel_hh, ft, fd, f, data):
    st.subheader("Battery & grid usage")

    batt_ids = set(sel_hh.loc[sel_hh["has_battery"], "house_id"])
    ft_batt = ft[ft["house_id"].isin(batt_ids)]

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Average battery SoC by hour of day")
        if ft_batt.empty:
            st.info("No battery-equipped homes in the current selection.")
        else:
            soc_by_hour = (ft_batt.assign(hour=ft_batt["timestamp"].dt.hour)
                                  .groupby(["hour", "wealth"], as_index=False)
                                  .agg(soc=("soc", "mean")))
            fig = px.line(soc_by_hour, x="hour", y="soc", color="wealth",
                          color_discrete_map=WEALTH_COLORS,
                          category_orders={"wealth": WEALTH_ORDER},
                          markers=True,
                          labels={"hour": "Hour of day", "soc": "Avg SoC (%)"})
            fig.update_layout(height=360, margin=dict(t=20, b=30),
                              xaxis=dict(tickmode="linear", dtick=2))
            st.plotly_chart(fig, width="stretch")

    with c2:
        st.markdown("##### Grid exports by hour of day")
        exp_hod = (ft.assign(hour=ft["timestamp"].dt.hour)
                     .groupby("hour", as_index=False)
                     .agg(exports=("grid_exports_kWh", "sum"),
                          imports=("grid_imports_kWh", "sum")))
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=exp_hod["hour"], y=exp_hod["exports"],
                              name="Exports", marker_color="#10b981"))
        fig2.add_trace(go.Bar(x=exp_hod["hour"], y=-exp_hod["imports"],
                              name="Imports (negative)", marker_color="#ef4444"))
        fig2.update_layout(barmode="relative", height=360,
                           margin=dict(t=20, b=30), yaxis_title="kWh",
                           xaxis=dict(title="Hour of day",
                                      tickmode="linear", dtick=2))
        st.plotly_chart(fig2, width="stretch")

    st.markdown("##### Peak demand vs. peak production — when does it happen?")
    by_hour = (ft.assign(hour=ft["timestamp"].dt.hour)
                 .groupby("hour", as_index=False)
                 .agg(load=("load_kWh", "sum"),
                      gen=("generation_kWh", "sum")))
    peak_load_h = int(by_hour.loc[by_hour["load"].idxmax(), "hour"])
    peak_gen_h = int(by_hour.loc[by_hour["gen"].idxmax(), "hour"])
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=by_hour["hour"], y=by_hour["load"],
                          name="Total load", marker_color="rgba(239,68,68,0.85)"))
    fig3.add_trace(go.Bar(x=by_hour["hour"], y=by_hour["gen"],
                          name="Total generation", marker_color="rgba(245,158,11,0.85)"))
    fig3.update_layout(barmode="group", height=360, margin=dict(t=20, b=30),
                       xaxis=dict(title="Hour of day", tickmode="linear", dtick=1),
                       yaxis_title="kWh", hovermode="x unified")
    fig3.add_annotation(x=peak_load_h, y=by_hour["load"].max(),
                        text=f"Peak load {peak_load_h:02d}:00",
                        showarrow=True, arrowhead=2, yshift=10,
                        font=dict(color="#ef4444"))
    fig3.add_annotation(x=peak_gen_h, y=by_hour["gen"].max(),
                        text=f"Peak gen {peak_gen_h:02d}:00",
                        showarrow=True, arrowhead=2, yshift=10,
                        font=dict(color="#f59e0b"))
    st.plotly_chart(fig3, width="stretch")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    data = load_all(DATA_DIR)

    if data["households"] is None or data["ticks"] is None:
        st.title("⚡ Green Grid Dashboard")
        st.warning(
            "No data available yet. Run the simulation first:\n\n"
            "```bash\n"
            "cd simulation && python simulation.py\n"
            "```\n\n"
            "or click **Run simulation** in the sidebar."
        )
        _ = sidebar(data)
        return

    f = sidebar(data)
    if not f:
        return

    st.title("⚡ Green Grid — Neighborhood Solar Dashboard")
    sel_hh, ft, fd = apply_filters(data, f)

    if sel_hh.empty or ft.empty:
        st.warning("No households match the current filters. Loosen them in the sidebar.")
        return

    tabs = st.tabs([
        "📊 Overview",
        "🦆 Duck Curve",
        "🏠 By Type",
        "💎 By Wealth",
        "💵 Economics",
        "🌞 Adoption",
        "🔋 Battery & Grid",
    ])

    with tabs[0]: tab_overview(sel_hh, ft, fd, f, data)
    with tabs[1]: tab_duck(sel_hh, ft, fd, f, data)
    with tabs[2]: tab_by_type(sel_hh, ft, fd, f, data)
    with tabs[3]: tab_by_wealth(sel_hh, ft, fd, f, data)
    with tabs[4]: tab_economics(sel_hh, ft, fd, f, data)
    with tabs[5]: tab_adoption(sel_hh, ft, fd, f, data)
    with tabs[6]: tab_battery_grid(sel_hh, ft, fd, f, data)


if __name__ == "__main__":
    main()
