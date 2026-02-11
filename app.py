"""
FIRM POWER OPTIMIZATION TOOL
=============================
Streamlit app - Python translation of VBA BESS Sensitivity Analysis
Finschhafen Green Energy Hub - Technical Assessment

Author: HSO Team
Version: 1.0
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.graph_objects as go

from firm_power_dispatch import (
    SystemConfig, run_dispatch, run_bess_sensitivity,
    run_pv_sensitivity, get_representative_days
)
from firm_power_charts import (
    chart_dispatch_profile, chart_cf_vs_bess, chart_days_vs_bess,
    chart_curtailment_vs_bess, chart_baseline_without_bess,
    chart_cf_vs_firm_power, build_summary_table
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Firm Power Optimization Tool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '<p style="font-size:2.2rem;font-weight:bold;color:#1a237e;text-align:center">'
    '⚡ Firm Power Optimization Tool</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p style="text-align:center;color:#666">BESS Sensitivity Analysis | '
    'Three-Tier Dispatch | Hydro + PV + Wind + BESS</p>',
    unsafe_allow_html=True
)
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'pv_results' not in st.session_state:
    st.session_state.pv_results = None
if 'baseline_results' not in st.session_state:
    st.session_state.baseline_results = None

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ System Configuration")

    # ── Profiles upload ──────────────────────────────────────────────────────
    st.subheader("📁 Generation Profiles")
    pv_file   = st.file_uploader("PV Profile (MW, 8760 hrs)", type=['csv', 'xlsx'], key='pv_upload')
    wind_file = st.file_uploader("Wind Profile (MW, 8760 hrs)", type=['csv', 'xlsx'], key='wind_upload')

    if pv_file:
        st.success(f"✓ PV: {pv_file.name}")
    if wind_file:
        st.success(f"✓ Wind: {wind_file.name}")

    st.markdown("---")

    # ── System parameters ────────────────────────────────────────────────────
    st.subheader("🏗️ System Parameters")

    col1, col2 = st.columns(2)
    with col1:
        electrolyzer_mw = st.number_input(
            "Firm Power Target (MW)", value=500, min_value=50, max_value=2000, step=50,
            help="Electrolyzer / firm load target in MW (Tier 1 threshold)"
        )
        hydro_mw = st.number_input(
            "Hydro Baseload (MW)", value=250, min_value=0, max_value=1000, step=50,
            help="Constant 24/7 hydro firm output (Tier 2 threshold)"
        )
    with col2:
        bess_power_mw = st.number_input(
            "BESS Max Power (MW)", value=500, min_value=50, max_value=2000, step=50
        )
        h2_factor = st.number_input(
            "H₂ Conversion (kWh/kg)", value=50.0, min_value=30.0, max_value=80.0, step=1.0,
            help="Energy required per kg of hydrogen"
        )

    col3, col4 = st.columns(2)
    with col3:
        bess_chg_eff = st.number_input(
            "Charge Eff (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5
        ) / 100
    with col4:
        bess_dis_eff = st.number_input(
            "Discharge Eff (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5
        ) / 100

    st.markdown("---")

    # ── BESS sensitivity sweep ───────────────────────────────────────────────
    st.subheader("🔋 BESS Sensitivity Sweep")
    st.caption("Define BESS sizes to analyse (comma-separated, MWh)")
    bess_input = st.text_input(
        "BESS Sizes (MWh)",
        value="500, 1000, 1500, 2000, 2200, 2250, 2500, 3000, 3500"
    )
    try:
        bess_sizes = [float(x.strip()) for x in bess_input.split(',') if x.strip()]
    except ValueError:
        bess_sizes = [500, 1000, 1500, 2000, 2250, 2500, 3000, 3500]
        st.error("Invalid BESS sizes — using defaults")

    st.markdown("---")

    # ── PV sensitivity cases ─────────────────────────────────────────────────
    st.subheader("☀️ PV Capacity Cases")
    st.caption("Scale the uploaded PV profile to different capacities")

    pv_case_input = st.text_area(
        "PV Cases (Label: MW per line)",
        value="1000 MW PV: 1000\n500 MW PV: 500",
        height=80
    )
    pv_cases = {}
    for line in pv_case_input.strip().splitlines():
        if ':' in line:
            label, mw = line.split(':', 1)
            try:
                pv_cases[label.strip()] = float(mw.strip())
            except ValueError:
                pass
    if not pv_cases:
        pv_cases = {"1000 MW PV": 1000.0, "500 MW PV": 500.0}

    # Reference capacity for profile normalisation
    pv_reference_mw = st.number_input(
        "Profile Reference Capacity (MW)",
        value=1000.0, min_value=1.0,
        help="The MW capacity your uploaded PV profile represents (used for scaling)"
    )

    st.markdown("---")

    # ── Run button ───────────────────────────────────────────────────────────
    can_run = pv_file is not None and wind_file is not None
    if not can_run:
        st.warning("Upload PV and Wind profiles to enable analysis")

    run_button = st.button(
        "▶️ RUN ANALYSIS", type="primary",
        disabled=not can_run, use_container_width=True
    )

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_home, tab_run, tab_results, tab_dispatch = st.tabs([
    "🏠 Home", "⚙️ Run", "📊 Results", "📈 Dispatch Profiles"
])

# ── TAB 1: HOME ──────────────────────────────────────────────────────────────
with tab_home:
    st.header("Firm Power Optimization Tool")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 🎯 Purpose
        Assess how Battery Energy Storage System (BESS) sizing affects firm power 
        delivery from a hybrid renewable system with:
        - **Hydro**: Constant 250 MW baseload (run-of-river, 24/7)
        - **PV**: Variable (sensitivity across 500–1,000 MW)
        - **Wind**: Variable (1,104 MW offshore + onshore)
        - **BESS**: Sensitivity sweep (500–3,500 MWh)

        ### 📐 Three-Tier Dispatch Logic
        | Tier | Condition | Output |
        |------|-----------|--------|
        | **FIRM** | Hydro + RE + BESS ≥ Target | Full firm power |
        | **SUPPLEMENTAL** | Hydro ≥ 250 MW | Hydro baseload only |
        | **SHUTDOWN** | Hydro < 250 MW | Zero output |
        """)

    with col2:
        st.markdown("""
        ### 📊 Outputs Generated
        - Overall Capacity Factor % vs BESS size
        - Days with full 24-hour firm output vs BESS size
        - Curtailment % vs BESS size
        - Typical & low-renewable day dispatch profiles
        - Baseline performance without BESS
        - H₂ production estimates
        - Full hourly dispatch download (Excel)

        ### 📁 Required Inputs
        | File | Format | Description |
        |------|--------|-------------|
        | PV Profile | CSV/XLSX | 8,760 hourly MW values |
        | Wind Profile | CSV/XLSX | 8,760 hourly MW values |
        """)

    st.info("Upload profiles in the sidebar and click **RUN ANALYSIS** to begin.")

# ── TAB 2: RUN ───────────────────────────────────────────────────────────────
with tab_run:
    st.header("⚙️ Run Configuration")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Firm Power Target", f"{electrolyzer_mw} MW")
    with col2:
        st.metric("Hydro Baseload", f"{hydro_mw} MW")
    with col3:
        st.metric("BESS Scenarios", f"{len(bess_sizes)}")
    with col4:
        st.metric("PV Cases", f"{len(pv_cases)}")

    st.markdown("**BESS sizes to sweep:**")
    st.write(", ".join([f"{int(b):,} MWh" for b in bess_sizes]))

    st.markdown("**PV capacity cases:**")
    for label, mw in pv_cases.items():
        st.write(f"- {label}: {mw:,.0f} MW")

    st.markdown("---")

    if run_button:
        if not can_run:
            st.error("❌ Upload both PV and Wind profiles first.")
        else:
            try:
                # ── Read profiles ────────────────────────────────────────────
                def read_profile(uploaded_file):
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    # Take second column if it exists (first may be hour index)
                    num_cols = df.select_dtypes(include=[np.number]).columns
                    series = df[num_cols[1]] if len(num_cols) > 1 else df[num_cols[0]]
                    return series.values[:8760].astype(float)

                with st.spinner("Reading profiles..."):
                    pv_raw   = read_profile(pv_file)
                    wind_raw = read_profile(wind_file)

                st.success(f"✓ PV profile: {len(pv_raw):,} hours | "
                           f"Max: {pv_raw.max():.1f} MW | Mean: {pv_raw.mean():.1f} MW")
                st.success(f"✓ Wind profile: {len(wind_raw):,} hours | "
                           f"Max: {wind_raw.max():.1f} MW | Mean: {wind_raw.mean():.1f} MW")

                # ── Base config ──────────────────────────────────────────────
                base_config = SystemConfig(
                    electrolyzer_capacity_mw=electrolyzer_mw,
                    hydro_power_mw=hydro_mw,
                    bess_max_power_mw=bess_power_mw,
                    bess_charge_eff=bess_chg_eff,
                    bess_discharge_eff=bess_dis_eff,
                    h2_conversion_factor=h2_factor,
                )

                total_runs = len(bess_sizes) * len(pv_cases)
                progress_bar = st.progress(0)
                status_text  = st.empty()
                run_count    = [0]

                def progress_cb(idx, total, bess_sz):
                    run_count[0] += 1
                    pct = int(run_count[0] / total_runs * 100)
                    progress_bar.progress(pct)
                    status_text.text(f"Running BESS {int(bess_sz):,} MWh... ({run_count[0]}/{total_runs})")

                # ── Run PV sensitivity sweep ─────────────────────────────────
                pv_results = run_pv_sensitivity(
                    pv_profile_1000mw=pv_raw,
                    wind_profile=wind_raw,
                    bess_sizes=bess_sizes,
                    config=base_config,
                    pv_cases=pv_cases,
                    progress_callback=progress_cb
                )

                # ── Baseline (no BESS) ───────────────────────────────────────
                status_text.text("Running baseline (no BESS)...")
                baseline_results = {}
                for label, pv_mw in pv_cases.items():
                    scale = pv_mw / pv_reference_mw
                    scaled_pv = pv_raw * scale
                    _, summary = run_dispatch(scaled_pv, wind_raw, 0.0, base_config)
                    baseline_results[f"{int(pv_mw)} MW"] = summary

                progress_bar.progress(100)
                status_text.text("✅ Analysis complete!")

                st.session_state.pv_results     = pv_results
                st.session_state.baseline_results = baseline_results
                st.session_state.analysis_complete = True
                st.session_state.hourly_data_cache = {
                    label: data['hourly'] for label, data in pv_results.items()
                }

                st.success(f"✅ Analysis complete! {total_runs} scenarios processed.")
                st.balloons()
                st.info("👉 Navigate to **Results** or **Dispatch Profiles** tabs.")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)

# ── TAB 3: RESULTS ───────────────────────────────────────────────────────────
with tab_results:
    if not st.session_state.analysis_complete:
        st.info("ℹ️ Run analysis first.")
    else:
        pv_results      = st.session_state.pv_results
        baseline_results = st.session_state.baseline_results

        st.header("📊 Analysis Results")

        # ── KPI row: best case per PV scenario ──────────────────────────────
        for label, data in pv_results.items():
            df = data['summary']
            best = df.loc[df['overall_cf_pct'].idxmax()]
            st.markdown(f"**{label}** — Best: {best['overall_cf_pct']:.2f}% CF "
                        f"@ {int(best['bess_size_mwh']):,} MWh BESS | "
                        f"Firm: {best['firm_cf_pct']:.2f}% | "
                        f"Curtailment: {best['curtailment_pct']:.2f}%")

        st.markdown("---")

        # ── Chart 1: Baseline without BESS ───────────────────────────────────
        st.subheader("📊 Baseline Performance: Without BESS")
        if baseline_results:
            fig_base = chart_baseline_without_bess(baseline_results)
            st.plotly_chart(fig_base, use_container_width=True)
        st.markdown("---")

        # ── Chart 2: CF % vs BESS ────────────────────────────────────────────
        st.subheader("📈 BESS Sensitivity: Capacity Factor % vs BESS Size")
        metric_choice = st.selectbox(
            "Select metric:", ['overall_cf_pct', 'firm_cf_pct'], 
            format_func=lambda x: {'overall_cf_pct': 'Overall CF %', 'firm_cf_pct': 'Firm CF %'}[x]
        )
        fig_cf = chart_cf_vs_bess(pv_results, metric=metric_choice)
        st.plotly_chart(fig_cf, use_container_width=True)
        st.markdown("---")

        # ── Chart 3: Days with 24h full output ──────────────────────────────
        st.subheader("📅 Days of High Performance vs BESS Size")
        fig_days = chart_days_vs_bess(pv_results)
        st.plotly_chart(fig_days, use_container_width=True)
        st.markdown("---")

        # ── Chart 4: Curtailment ─────────────────────────────────────────────
        st.subheader("✂️ Curtailment Analysis")
        fig_curt = chart_curtailment_vs_bess(pv_results)
        st.plotly_chart(fig_curt, use_container_width=True)
        st.markdown("---")

        # ── Summary table ────────────────────────────────────────────────────
        st.subheader("📋 Full Results Table")
        summary_table = build_summary_table(pv_results)
        st.dataframe(summary_table, use_container_width=True, hide_index=True)
        st.markdown("---")

        # ── Excel export ─────────────────────────────────────────────────────
        st.subheader("📥 Download Results")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("📥 Prepare Excel", type="primary", use_container_width=True):
                with st.spinner("Building Excel..."):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        summary_table.to_excel(writer, sheet_name='Summary', index=False)
                        for pv_label, data in pv_results.items():
                            sheet = pv_label[:28].replace(' ', '_').replace('/', '_')
                            data['summary'].to_excel(writer, sheet_name=sheet, index=False)
                    output.seek(0)
                    st.session_state['excel_ready'] = output

        if 'excel_ready' in st.session_state:
            col1b, col2b, col3b = st.columns([2, 1, 2])
            with col2b:
                st.download_button(
                    "⬇️ Download Excel",
                    data=st.session_state['excel_ready'],
                    file_name="firm_power_sensitivity.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, type="secondary"
                )

# ── TAB 4: DISPATCH PROFILES ─────────────────────────────────────────────────
with tab_dispatch:
    if not st.session_state.analysis_complete:
        st.info("ℹ️ Run analysis first.")
    else:
        st.header("📈 Dispatch Profiles")

        hourly_cache = st.session_state.get('hourly_data_cache', {})
        if not hourly_cache:
            st.warning("No hourly data available.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                pv_choice = st.selectbox("PV Case:", list(hourly_cache.keys()))
            with col2:
                bess_choice = st.selectbox(
                    "BESS Size (MWh):",
                    sorted(hourly_cache[pv_choice].keys()),
                    format_func=lambda x: f"{int(x):,} MWh"
                )

            hourly_df = hourly_cache[pv_choice][bess_choice]
            hourly_df['Hour_of_Day'] = hourly_df['Hour'] % 24

            typical_day, low_day = get_representative_days(hourly_df)

            # Config needed for secondary axis label
            firm_mw = electrolyzer_mw

            st.subheader("📅 Typical Day (Median Renewable)")
            fig_typ = chart_dispatch_profile(
                typical_day, 
                f"Typical Daily Dispatch Profile — {pv_choice} | {int(bess_choice):,} MWh BESS",
                firm_power_mw=firm_mw
            )
            st.plotly_chart(fig_typ, use_container_width=True)
            st.caption("Median renewable generation day selected from 365 daily totals.")

            st.markdown("---")

            st.subheader("⚠️ Low Renewable Period")
            fig_low = chart_dispatch_profile(
                low_day,
                f"Low Renewable Period — {pv_choice} | {int(bess_choice):,} MWh BESS",
                firm_power_mw=firm_mw
            )
            st.plotly_chart(fig_low, use_container_width=True)
            st.caption("10th percentile renewable generation day — shows system limitation during extended low-resource periods.")

            st.markdown("---")

            # ── Operational breakdown for selected scenario ──────────────────
            st.subheader("⚡ Operational Breakdown")
            mode_counts = hourly_df['Operation_Mode'].value_counts()
            total_h = len(hourly_df)

            met = {
                'FIRM':         mode_counts.get('FIRM', 0),
                'SUPPLEMENTAL': mode_counts.get('SUPPLEMENTAL', 0),
                'SHUTDOWN':     mode_counts.get('SHUTDOWN', 0),
            }

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("FIRM Hours", f"{met['FIRM']:,}",
                          f"{met['FIRM']/total_h*100:.1f}%")
            with c2:
                st.metric("SUPPLEMENTAL Hours", f"{met['SUPPLEMENTAL']:,}",
                          f"{met['SUPPLEMENTAL']/total_h*100:.1f}%")
            with c3:
                st.metric("SHUTDOWN Hours", f"{met['SHUTDOWN']:,}",
                          f"{met['SHUTDOWN']/total_h*100:.1f}%")
            with c4:
                cf_val = (hourly_df['Capacity_Factor_pct'].mean())
                st.metric("Overall CF", f"{cf_val:.2f}%")

            # Pie chart of operational modes
            fig_pie = go.Figure(go.Pie(
                labels=list(met.keys()),
                values=list(met.values()),
                marker_colors=['#1a237e', '#FF8F00', '#B71C1C'],
                textinfo='label+percent',
                hole=0.35,
            ))
            fig_pie.update_layout(
                title='Hours by Operation Mode',
                height=350,
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            # ── Hourly data export ───────────────────────────────────────────
            st.markdown("---")
            st.subheader("📥 Download Hourly Dispatch")
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("📥 Prepare Hourly Excel", key='hourly_dl', use_container_width=True):
                    with st.spinner("Building hourly Excel..."):
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='openpyxl') as writer:
                            hourly_df.to_excel(
                                writer,
                                sheet_name=f"BESS_{int(bess_choice)}",
                                index=False
                            )
                        out.seek(0)
                        st.session_state['hourly_excel'] = out

            if 'hourly_excel' in st.session_state:
                col1b, col2b, col3b = st.columns([2, 1, 2])
                with col2b:
                    st.download_button(
                        "⬇️ Download Hourly",
                        data=st.session_state['hourly_excel'],
                        file_name=f"dispatch_{pv_choice.replace(' ', '_')}_{int(bess_choice)}MWh.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True, type="secondary"
                    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#999">'
    'Firm Power Optimization Tool v1.0 | HSO Team | '
    'Three-Tier Dispatch: FIRM → SUPPLEMENTAL → SHUTDOWN'
    '</div>',
    unsafe_allow_html=True
)
