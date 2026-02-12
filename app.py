"""
FIRM POWER OPTIMIZATION TOOL
=============================
Streamlit app - VBA BESS Sensitivity Analysis (Python translation)
Finschhafen Green Energy Hub - Technical Assessment

v1.1 - Clean terminology: "Capacity Factor" only (internally = firm_cf_pct)
v1.1 - Export hourly dispatch for 500 MWh BESS across all PV cases
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

from firm_power_dispatch import (
    SystemConfig, run_dispatch, run_bess_sensitivity,
    run_pv_sensitivity, get_representative_days
)
from firm_power_charts import (
    chart_dispatch_profile, chart_cf_vs_bess, chart_days_vs_bess,
    chart_curtailment_vs_bess, chart_baseline_without_bess,
    build_summary_table
)

st.set_page_config(
    page_title="Firm Power Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '<p style="font-size:2.2rem;font-weight:bold;color:#1565C0;text-align:center">'
    '⚡ Firm Power Optimization Tool</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p style="text-align:center;color:#666">BESS Sensitivity Analysis | '
    'Three-Tier Dispatch: FIRM → SUPPLEMENTAL → SHUTDOWN</p>',
    unsafe_allow_html=True
)
st.markdown("---")

# Session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("📁 Generation Profiles")
    pv_file   = st.file_uploader("PV Profile (MW, 8760 hrs)", type=['csv', 'xlsx'], key='pv')
    wind_file = st.file_uploader("Wind Profile (MW, 8760 hrs)", type=['csv', 'xlsx'], key='wind')
    if pv_file:
        st.success(f"✓ {pv_file.name}")
    if wind_file:
        st.success(f"✓ {wind_file.name}")

    st.markdown("---")
    st.subheader("🏗️ System Parameters")
    col1, col2 = st.columns(2)
    with col1:
        elec_mw = st.number_input("Firm Power (MW)", value=500, min_value=50, max_value=2000, step=50)
        hydro_mw = st.number_input("Hydro (MW)", value=250, min_value=0, max_value=1000, step=50)
    with col2:
        bess_pwr_mw = st.number_input("BESS Power (MW)", value=500, min_value=50, max_value=2000, step=50)
        h2_factor = st.number_input("H₂ (kWh/kg)", value=50.0, min_value=30.0, max_value=80.0, step=1.0)

    col3, col4 = st.columns(2)
    with col3:
        bess_chg = st.number_input("Charge (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5) / 100
    with col4:
        bess_dis = st.number_input("Discharge (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5) / 100

    st.markdown("---")
    st.subheader("🔋 BESS Sensitivity")
    bess_input = st.text_input("BESS Sizes (MWh, comma-separated)", value="500, 1000, 1500, 2000, 2250, 2500, 3000, 3500")
    try:
        bess_sizes = [float(x.strip()) for x in bess_input.split(',') if x.strip()]
    except ValueError:
        bess_sizes = [500, 1000, 1500, 2000, 2250, 2500, 3000, 3500]
        st.error("Invalid input - using defaults")

    st.markdown("---")
    st.subheader("☀️ PV Capacity Cases")
    pv_case_input = st.text_area("PV Cases (Label: MW per line)", value="1000 MW PV: 1000\n500 MW PV: 500", height=80)
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

    pv_ref_mw = st.number_input("Profile Reference (MW)", value=1000.0, min_value=1.0, help="The MW capacity your uploaded PV profile represents")

    st.markdown("---")
    can_run = pv_file is not None and wind_file is not None
    if not can_run:
        st.warning("Upload profiles to enable analysis")
    run_btn = st.button("▶️ RUN ANALYSIS", type="primary", disabled=not can_run, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_home, tab_run, tab_results, tab_dispatch = st.tabs(["🏠 Home", "⚙️ Run", "📊 Results", "📈 Dispatch"])

with tab_home:
    st.header("Firm Power Optimization Tool")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 🎯 Purpose
        Assess Battery Energy Storage sizing for firm power delivery from hybrid renewable system:
        - **Hydro**: 250 MW baseload (24/7)
        - **PV**: Variable (500–1,000 MW sensitivity)
        - **Wind**: Variable (~1,104 MW)
        - **BESS**: Sensitivity sweep (500–3,500 MWh)

        ### 📐 Three-Tier Dispatch
        | Tier | Condition | Output |
        |------|-----------|--------|
        | **FIRM** | Hydro+RE+BESS ≥ Target | Full firm power |
        | **SUPPLEMENTAL** | Hydro ≥ 250 MW | Hydro only |
        | **SHUTDOWN** | Hydro < 250 MW | Zero |
        """)
    with col2:
        st.markdown("""
        ### 📊 Outputs
        - Capacity Factor % vs BESS size
        - Days with 24h full operation vs BESS
        - Curtailment % vs BESS size
        - Typical & low-renewable dispatch profiles
        - Baseline performance (no BESS)
        - Full hourly dispatch download

        ### 📁 Required Inputs
        | File | Format |
        |------|--------|
        | PV Profile | CSV/XLSX, 8760 hrs |
        | Wind Profile | CSV/XLSX, 8760 hrs |
        """)
    st.info("Configure in sidebar → Run Analysis")

with tab_run:
    st.header("⚙️ Run Configuration")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Firm Power", f"{elec_mw} MW")
    with col2:
        st.metric("Hydro", f"{hydro_mw} MW")
    with col3:
        st.metric("BESS Scenarios", len(bess_sizes))
    with col4:
        st.metric("PV Cases", len(pv_cases))

    st.markdown(f"**BESS sweep:** {', '.join([f'{int(b):,} MWh' for b in bess_sizes])}")
    st.markdown("**PV cases:**")
    for lbl, mw in pv_cases.items():
        st.write(f"- {lbl}: {mw:,.0f} MW")
    st.markdown("---")

    if run_btn:
        try:
            def read_profile(f):
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                num_cols = df.select_dtypes(include=[np.number]).columns
                series = df[num_cols[1]] if len(num_cols) > 1 else df[num_cols[0]]
                return series.values[:8760].astype(float)

            with st.spinner("Reading profiles..."):
                pv_raw   = read_profile(pv_file)
                wind_raw = read_profile(wind_file)
            st.success(f"✓ PV: {len(pv_raw):,} hrs | Max: {pv_raw.max():.1f} MW")
            st.success(f"✓ Wind: {len(wind_raw):,} hrs | Max: {wind_raw.max():.1f} MW")

            cfg = SystemConfig(
                electrolyzer_capacity_mw=elec_mw,
                hydro_power_mw=hydro_mw,
                bess_max_power_mw=bess_pwr_mw,
                bess_charge_eff=bess_chg,
                bess_discharge_eff=bess_dis,
                h2_conversion_factor=h2_factor,
            )

            total_runs = len(bess_sizes) * len(pv_cases)
            pbar = st.progress(0)
            status = st.empty()
            run_count = [0]

            def progress_cb(idx, total, bess_sz):
                run_count[0] += 1
                pct = int(run_count[0] / total_runs * 100)
                pbar.progress(pct)
                status.text(f"Running BESS {int(bess_sz):,} MWh... ({run_count[0]}/{total_runs})")

            pv_results = run_pv_sensitivity(
                pv_raw, wind_raw, bess_sizes, cfg, pv_cases, pv_ref_mw, progress_cb
            )

            status.text("Running baseline (no BESS)...")
            baseline = {}
            for lbl, pv_mw in pv_cases.items():
                scale = pv_mw / pv_ref_mw
                _, summary = run_dispatch(pv_raw * scale, wind_raw, 0.0, cfg)
                baseline[f"{int(pv_mw)} MW"] = summary

            pbar.progress(100)
            status.text("✅ Complete!")

            st.session_state.pv_results = pv_results
            st.session_state.baseline = baseline
            st.session_state.analysis_complete = True
            st.session_state.hourly_cache = {lbl: data['hourly'] for lbl, data in pv_results.items()}

            st.success(f"✅ {total_runs} scenarios processed")
            st.balloons()
            st.info("👉 Go to **Results** or **Dispatch** tabs")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)

with tab_results:
    if not st.session_state.analysis_complete:
        st.info("Run analysis first")
    else:
        pv_results = st.session_state.pv_results
        baseline   = st.session_state.baseline

        st.header("📊 Results")

        # Best case per PV scenario
        for lbl, data in pv_results.items():
            df = data['summary']
            best = df.loc[df['firm_cf_pct'].idxmax()]
            st.markdown(f"**{lbl}** — Best: **{best['firm_cf_pct']:.2f}% CF** @ {int(best['bess_size_mwh']):,} MWh BESS | Curtailment: {best['curtailment_pct']:.2f}%")
        st.markdown("---")

        # Chart 1: Baseline
        st.subheader("📊 Baseline Performance: Without BESS")
        if baseline:
            st.plotly_chart(chart_baseline_without_bess(baseline), use_container_width=True)
        st.markdown("---")

        # Chart 2: CF vs BESS
        st.subheader("📈 Capacity Factor vs BESS Size")
        st.plotly_chart(chart_cf_vs_bess(pv_results), use_container_width=True)
        st.markdown("---")

        # Chart 3: Days
        st.subheader("📅 Days of High Performance vs BESS Size")
        st.plotly_chart(chart_days_vs_bess(pv_results), use_container_width=True)
        st.markdown("---")

        # Chart 4: Curtailment
        st.subheader("✂️ Curtailment Analysis")
        st.plotly_chart(chart_curtailment_vs_bess(pv_results), use_container_width=True)
        st.markdown("---")

        # Summary table
        st.subheader("📋 Summary Table")
        summary_tbl = build_summary_table(pv_results)
        st.dataframe(summary_tbl, use_container_width=True, hide_index=True)
        st.markdown("---")

        # Excel export
        st.subheader("📥 Download Results")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("📥 Prepare Excel", type="primary", use_container_width=True):
                with st.spinner("Building Excel..."):
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='openpyxl') as writer:
                        summary_tbl.to_excel(writer, sheet_name='Summary', index=False)
                        
                        # Export 500 MWh hourly dispatch for ALL PV cases
                        hourly_cache = st.session_state.get('hourly_cache', {})
                        for pv_label in hourly_cache.keys():
                            if 500.0 in hourly_cache[pv_label]:
                                df_500 = hourly_cache[pv_label][500.0]
                                sheet_name = f"{pv_label.replace(' ', '_')}_500MWh"[:31]
                                df_500.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Also export each PV case's full summary
                        for pv_lbl, data in pv_results.items():
                            sheet = pv_lbl[:28].replace(' ', '_').replace('/', '_')
                            data['summary'].to_excel(writer, sheet_name=sheet, index=False)
                    out.seek(0)
                    st.session_state['excel_ready'] = out

        if 'excel_ready' in st.session_state:
            col1b, col2b, col3b = st.columns([2, 1, 2])
            with col2b:
                st.download_button(
                    "⬇️ Download Excel",
                    data=st.session_state['excel_ready'],
                    file_name="firm_power_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, type="secondary"
                )

with tab_dispatch:
    if not st.session_state.analysis_complete:
        st.info("Run analysis first")
    else:
        st.header("📈 Dispatch Profiles")
        hourly_cache = st.session_state.get('hourly_cache', {})
        if not hourly_cache:
            st.warning("No hourly data")
        else:
            col1, col2 = st.columns(2)
            with col1:
                pv_choice = st.selectbox("PV Case:", list(hourly_cache.keys()))
            with col2:
                bess_choice = st.selectbox("BESS Size (MWh):", sorted(hourly_cache[pv_choice].keys()), format_func=lambda x: f"{int(x):,} MWh")

            hourly_df = hourly_cache[pv_choice][bess_choice]
            typical, low = get_representative_days(hourly_df)

            st.subheader("📅 Typical Day")
            fig_typ = chart_dispatch_profile(typical, f"Typical Day — {pv_choice} | {int(bess_choice):,} MWh BESS", elec_mw)
            st.plotly_chart(fig_typ, use_container_width=True)
            st.caption("Median renewable generation day")
            st.markdown("---")

            st.subheader("⚠️ Low Renewable Period")
            fig_low = chart_dispatch_profile(low, f"Low Renewable Period — {pv_choice} | {int(bess_choice):,} MWh BESS", elec_mw)
            st.plotly_chart(fig_low, use_container_width=True)
            st.caption("10th percentile renewable day — shows system limitation")
            st.markdown("---")

            # Operational breakdown
            st.subheader("⚡ Operational Breakdown")
            mode_counts = hourly_df['Operation_Mode'].value_counts()
            met = {
                'FIRM': mode_counts.get('FIRM', 0),
                'SUPPLEMENTAL': mode_counts.get('SUPPLEMENTAL', 0),
                'SHUTDOWN': mode_counts.get('SHUTDOWN', 0),
            }
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("FIRM Hours", f"{met['FIRM']:,}", f"{met['FIRM']/8760*100:.1f}%")
            with c2:
                st.metric("SUPPLEMENTAL", f"{met['SUPPLEMENTAL']:,}", f"{met['SUPPLEMENTAL']/8760*100:.1f}%")
            with c3:
                st.metric("SHUTDOWN", f"{met['SHUTDOWN']:,}", f"{met['SHUTDOWN']/8760*100:.1f}%")
            with c4:
                cf_avg = hourly_df['Capacity_Factor_%'].mean()
                st.metric("Avg CF", f"{cf_avg:.2f}%")

st.markdown("---")
st.markdown('<div style="text-align:center;color:#999">Firm Power Optimization Tool v1.1 | HSO Team</div>', unsafe_allow_html=True)
