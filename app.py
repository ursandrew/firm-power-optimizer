"""
FIRM POWER OPTIMIZATION TOOL v2.1
==================================
Styled to match Energy Modeling Optimizer with SJ logo
Fixed: StreamlitDuplicateElementId error with unique button keys
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
    chart_cf_vs_bess,
    chart_dispatch_profile,
    build_summary_table
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Firm Power Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Complete CSS fix for all dark mode elements
st.markdown("""
<style>
    /* ========== FORCE LIGHT THEME EVERYWHERE ========== */
    
    /* Main app and sidebar backgrounds */
    .stApp {
        background-color: #f5f7fa !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
    }
    
    /* Top header bar (above title) */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
    }
    
    /* All text dark */
    .stApp, .stApp * {
        color: #262730 !important;
    }
    
    /* ========== SIDEBAR INPUT FIELDS ========== */
    
    /* Text areas */
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] .stTextArea textarea,
    section[data-testid="stSidebar"] .stTextArea > div > div {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* Number inputs */
    section[data-testid="stSidebar"] input[type="number"],
    section[data-testid="stSidebar"] .stNumberInput input,
    section[data-testid="stSidebar"] .stNumberInput > div > div > input {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* Number input +/- buttons */
    section[data-testid="stSidebar"] .stNumberInput button,
    section[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #f0f2f6 !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* Text inputs */
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] input[type="text"] {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* ========== FILE UPLOADER ========== */
    
    section[data-testid="stSidebar"] .stFileUploader,
    section[data-testid="stSidebar"] .stFileUploader > div,
    section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] {
        background-color: #f0f2f6 !important;
        border: 2px dashed #d0d0d0 !important;
    }
    
    section[data-testid="stSidebar"] .stFileUploader section {
        background-color: #f0f2f6 !important;
    }
    
    section[data-testid="stSidebar"] .stFileUploader button {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
    }
    
    /* ========== EXPANDER HEADERS ========== */
    
    section[data-testid="stSidebar"] .streamlit-expanderHeader,
    section[data-testid="stSidebar"] details summary {
        background-color: #e8eaf0 !important;
        color: #262730 !important;
        border: 1px solid #d0d0d0 !important;
        border-radius: 4px !important;
    }
    
    section[data-testid="stSidebar"] details {
        border: none !important;
    }
    
    /* ========== ENSURE ALL BUTTONS ARE LIGHT ========== */
    
    section[data-testid="stSidebar"] button {
        background-color: #f0f2f6 !important;
        color: #262730 !important;
    }
    
    section[data-testid="stSidebar"] button:hover {
        background-color: #e0e2e6 !important;
    }
    
    /* ========== FIX SELECTBOXES/DROPDOWNS ========== */
    
    .stSelectbox > div > div {
        background-color: #ffffff !important;
        color: #262730 !important;
    }
    
    /* ========== FIX DATAFRAME TABLE ========== */
    
    .stDataFrame {
        background-color: #ffffff !important;
    }
    
    .stDataFrame table {
        background-color: #ffffff !important;
    }
    
    .stDataFrame th {
        background-color: #f0f2f6 !important;
        color: #262730 !important;
    }
    
    .stDataFrame td {
        background-color: #ffffff !important;
        color: #262730 !important;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SJ LOGO + HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="display:flex;align-items:center;justify-content:center;gap:14px;margin-bottom:4px">
    <svg width="52" height="52" viewBox="0 0 52 52" xmlns="http://www.w3.org/2000/svg">
        <rect width="52" height="52" rx="0" fill="#0047AB"/>
        <text x="18" y="38" font-family="Arial,sans-serif" font-size="32"
              font-weight="bold" fill="white" text-anchor="middle">S</text>
        <text x="36" y="37" font-family="Arial,sans-serif" font-size="18"
              font-weight="bold" fill="white" text-anchor="middle">J</text>
        <circle cx="38" cy="16" r="4" fill="#E63946"/>
    </svg>
    <p style="font-size:2.2rem;font-weight:bold;color:#1976D2;margin:0">
        Firm Power Optimization Tool
    </p>
</div>
""", unsafe_allow_html=True)
st.caption("Hybrid Renewable Energy System: PV + Wind + Hydro + BESS")

st.markdown("---")

# Session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - ORGANIZED BY COMPONENT
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔧 System Configuration")
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════
    # SOLAR PV SECTION
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("☀️ SOLAR PV", expanded=False):
        st.markdown("**Capacity Range**")
        pv_case_input = st.text_area(
            "PV Cases (Label: MW per line)",
            value="1000 MW PV: 1000\n500 MW PV: 500",
            height=80,
            help="Define multiple PV capacity cases for sensitivity analysis"
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
        
        st.markdown("**Generation Profile Upload**")
        pv_file = st.file_uploader(
            "Upload PV Profile (8760 hours)",
            type=['csv', 'xlsx'],
            key='pv_profile',
            help="Hourly PV generation profile in MW"
        )
        if pv_file:
            st.success(f"✓ {pv_file.name}")
        
        pv_ref_mw = st.number_input(
            "Profile Reference Capacity (MW)",
            value=1000.0,
            min_value=1.0,
            help="The MW capacity your uploaded profile represents"
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    # WIND SECTION
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("💨 WIND", expanded=False):
        wind_capacity = st.number_input(
            "Wind Capacity (MW)",
            value=1104.0,
            min_value=0.0,
            step=50.0,
            help="Total installed wind capacity"
        )
        
        st.markdown("**Generation Profile Upload**")
        wind_file = st.file_uploader(
            "Upload Wind Profile (8760 hours)",
            type=['csv', 'xlsx'],
            key='wind_profile',
            help="Hourly wind generation profile in MW"
        )
        if wind_file:
            st.success(f"✓ {wind_file.name}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # HYDRO SECTION
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("💧 HYDRO", expanded=False):
        hydro_mw = st.number_input(
            "Hydro Baseload (MW)",
            value=250.0,
            min_value=0.0,
            max_value=1000.0,
            step=50.0,
            help="Constant 24/7 hydro firm output"
        )
        st.caption("ℹ️ Run-of-river hydro provides continuous baseload (Tier 2 threshold)")
    
    # ══════════════════════════════════════════════════════════════════════════
    # BESS SECTION
    # ══════════════════════════════════════════════════════════════════════════
    with st.expander("🔋 BATTERY STORAGE", expanded=False):
        st.markdown("**BESS Capacity Sweep**")
        bess_input = st.text_input(
            "BESS Sizes (MWh, comma-separated)",
            value="500, 1000, 1500, 2000, 2250, 2500, 3000, 3500",
            help="Define BESS energy capacity scenarios to analyze"
        )
        try:
            bess_sizes = [float(x.strip()) for x in bess_input.split(',') if x.strip()]
        except ValueError:
            bess_sizes = [500, 1000, 1500, 2000, 2250, 2500, 3000, 3500]
            st.error("Invalid - using defaults")
        
        st.markdown("**BESS Parameters**")
        col1, col2 = st.columns(2)
        with col1:
            bess_pwr_mw = st.number_input("Max Power (MW)", value=500, min_value=50, max_value=2000, step=50)
            bess_chg = st.number_input("Charge Eff (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5) / 100
        with col2:
            bess_dis = st.number_input("Discharge Eff (%)", value=90.0, min_value=50.0, max_value=100.0, step=0.5) / 100
    
    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM PARAMETERS
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    with st.expander("⚙️ SYSTEM PARAMETERS", expanded=False):
        elec_mw = st.number_input(
            "Firm Power Target (MW)",
            value=500,
            min_value=50,
            max_value=2000,
            step=50,
            help="Electrolyzer / firm load target (Tier 1 threshold)"
        )
        h2_factor = st.number_input(
            "H₂ Conversion (kWh/kg)",
            value=50.0,
            min_value=30.0,
            max_value=80.0,
            step=1.0,
            help="Energy required per kg of hydrogen"
        )

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_home, tab_run, tab_results, tab_dispatch = st.tabs([
    "🏠 Home",
    "▶️ Run Analysis", 
    "📊 Results",
    "📈 Dispatch Details"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: HOME - SHOW SEARCH SPACE
# ══════════════════════════════════════════════════════════════════════════════
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
        """)  
    
    
    # ══════════════════════════════════════════════════════════════════════════
    # SEARCH SPACE DISPLAY
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔍 System Overview")
    
    pv_options = len(pv_cases)
    wind_options = 1  # Fixed wind capacity
    hydro_options = 1  # Fixed hydro
    bess_options = len(bess_sizes)
    total_combinations = pv_options * bess_options
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Solar PV Scenarios", pv_options, f"{min(pv_cases.values()):.0f}-{max(pv_cases.values()):.0f} MW")
    with col2:
        st.metric("Wind Capacity", f"{wind_capacity:.0f} MW")
    with col3:
        st.metric("Hydro Baseload", f"{hydro_mw:.0f} MW")
    with col4:
        st.metric("Battery Sizes Tested", bess_options, f"{min(bess_sizes):.0f}-{max(bess_sizes):.0f} MWh")
    
    st.info(f"**Total Analysis Cases:** {total_combinations:,} scenarios "
            f"({pv_options} solar scenarios × {bess_options} battery sizes)")
    
    st.success(f"☀️ Solar PV + 💨 Wind + 💧 Hydro + 🔋 Battery Storage")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: RUN - RUN BUTTON MOVED HERE
# ══════════════════════════════════════════════════════════════════════════════
with tab_run:
    st.header("⚙️ Run Analysis")
    
    # Display configuration summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Power Target", f"{elec_mw} MW")
    with col2:
        st.metric("Hydro Baseload", f"{hydro_mw} MW")
    with col3:
        st.metric("Solar Scenarios", len(pv_cases))
    with col4:
        st.metric("Battery Sizes", len(bess_sizes))
    
    st.markdown("**Solar PV capacity scenarios:**")
    for lbl, mw in pv_cases.items():
        st.write(f"- {lbl}: {mw:,.0f} MW")
    
    st.markdown(f"**Battery storage sizes to test:** {', '.join([f'{int(b):,} MWh' for b in bess_sizes])}")
    
    st.markdown("---")
    
    # Validation
    can_run = (pv_file is not None) and (wind_file is not None)
    if not can_run:
        st.warning("⚠️ Please upload Solar PV and Wind generation profiles in the sidebar to begin analysis")
    
    # RUN BUTTON
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        run_btn = st.button(
            "▶️ RUN ANALYSIS",
            type="primary",
            disabled=not can_run,
            use_container_width=True,
            key="run_analysis_btn"
        )
    
    if run_btn:
        try:
            def read_profile(f):
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                num_cols = df.select_dtypes(include=[np.number]).columns
                series = df[num_cols[1]] if len(num_cols) > 1 else df[num_cols[0]]
                return series.values[:8760].astype(float)
            
            with st.spinner("📊 Reading profiles..."):
                pv_raw = read_profile(pv_file)
                wind_raw = read_profile(wind_file)
            
            st.success(f"✓ PV: {len(pv_raw):,} hrs | Max: {pv_raw.max():.1f} MW | Mean: {pv_raw.mean():.1f} MW")
            st.success(f"✓ Wind: {len(wind_raw):,} hrs | Max: {wind_raw.max():.1f} MW | Mean: {wind_raw.mean():.1f} MW")
            
            cfg = SystemConfig(
                electrolyzer_capacity_mw=elec_mw,
                hydro_power_mw=hydro_mw,
                bess_max_power_mw=bess_pwr_mw,
                bess_charge_eff=bess_chg,
                bess_discharge_eff=bess_dis,
                h2_conversion_factor=h2_factor,
                wind_capacity_mw=wind_capacity,
            )
            
            total_runs = len(bess_sizes) * len(pv_cases)
            pbar = st.progress(0)
            status = st.empty()
            run_count = [0]
            
            def progress_cb(idx, total, bess_sz):
                run_count[0] += 1
                pct = int(run_count[0] / total_runs * 100)
                pbar.progress(pct)
                status.text(f"⚙️ Testing battery size {int(bess_sz):,} MWh... ({run_count[0]}/{total_runs})")
            
            pv_results = run_pv_sensitivity(
                pv_raw, wind_raw, bess_sizes, cfg,
                pv_cases, pv_ref_mw, progress_cb
            )
            
            status.text("📊 Running baseline scenario (no battery)...")
            baseline = {}
            for lbl, pv_mw in pv_cases.items():
                scale = pv_mw / pv_ref_mw
                _, summary = run_dispatch(pv_raw * scale, wind_raw, 0.0, cfg)
                baseline[f"{int(pv_mw)} MW"] = summary
            
            pbar.progress(100)
            status.text("✅ Analysis complete!")
            
            st.session_state.pv_results = pv_results
            st.session_state.baseline = baseline
            st.session_state.analysis_complete = True
            st.session_state.hourly_cache = {
                lbl: data['hourly'] for lbl, data in pv_results.items()
            }
            
            st.success(f"✅ **Analysis Complete!** {total_runs} scenarios processed")
            st.balloons()
            st.info("👉 Navigate to **📊 Results** or **📈 Dispatch** tabs to view results")
            
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: RESULTS - ONLY 2 ESSENTIAL CHARTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    if not st.session_state.analysis_complete:
        st.info("ℹ️ Please complete the analysis in the **Run Analysis** tab first")
    else:
        pv_results = st.session_state.pv_results
        baseline = st.session_state.baseline
        
        st.header("📊 Analysis Results")
        
        # Best case summary
        for lbl, data in pv_results.items():
            df = data['summary']
            best = df.loc[df['firm_cf_pct'].idxmax()]
            st.markdown(
                f"**{lbl}** — Best Performance: **{best['firm_cf_pct']:.2f}%** capacity factor "
                f"with {int(best['bess_size_mwh']):,} MWh battery | "
                f"Energy Curtailed: {best['curtailment_pct']:.2f}%"
            )
        
        st.markdown("---")
        
        # ══════════════════════════════════════════════════════════════════════
        # CHART: System Performance vs Battery Size
        # ══════════════════════════════════════════════════════════════════════
        st.subheader("📈 System Performance vs Battery Size")
        st.caption("How capacity factor improves with larger battery storage for different solar capacities")
        fig_cf = chart_cf_vs_bess(pv_results)
        st.plotly_chart(fig_cf, use_container_width=True, key='chart_cf_vs_bess')
        
        st.markdown("---")
        
        # Summary table with light background
        st.subheader("📋 Detailed Results Table")
        summary_tbl = build_summary_table(pv_results)
        st.dataframe(
            summary_tbl,
            use_container_width=True,
            hide_index=True,
            key='summary_table'
        )
        
        st.markdown("---")
        
        # Excel export
        st.subheader("📥 Download Results")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("📥 Prepare Excel", type="primary", use_container_width=True, key="prepare_excel_btn"):
                with st.spinner("Building Excel report..."):
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='openpyxl') as writer:
                        summary_tbl.to_excel(writer, sheet_name='Summary', index=False)
                        
                        # Export 500 MWh hourly for all PV cases
                        hourly_cache = st.session_state.get('hourly_cache', {})
                        for pv_label in hourly_cache.keys():
                            if 500.0 in hourly_cache[pv_label]:
                                df_500 = hourly_cache[pv_label][500.0]
                                sheet_name = f"{pv_label.replace(' ', '_')}_500MWh"[:31]
                                df_500.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        # Export full summary per PV case
                        for pv_lbl, data in pv_results.items():
                            sheet = pv_lbl[:28].replace(' ', '_')
                            data['summary'].to_excel(writer, sheet_name=sheet, index=False)
                    
                    out.seek(0)
                    st.session_state['excel_ready'] = out
                    st.success("✅ Excel report ready for download")
        
        if 'excel_ready' in st.session_state:
            col1b, col2b, col3b = st.columns([2, 1, 2])
            with col2b:
                st.download_button(
                    "⬇️ Download Excel",
                    data=st.session_state['excel_ready'],
                    file_name="firm_power_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary",
                    key="download_excel_btn"
                )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: DISPATCH PROFILES
# ══════════════════════════════════════════════════════════════════════════════
with tab_dispatch:
    if not st.session_state.analysis_complete:
        st.info("ℹ️ Please complete the analysis in the **Run Analysis** tab first")
    else:
        st.header("📈 Hourly Dispatch Profiles")
        
        hourly_cache = st.session_state.get('hourly_cache', {})
        if not hourly_cache:
            st.warning("No hourly data available")
        else:
            col1, col2 = st.columns(2)
            with col1:
                pv_choice = st.selectbox(
                    "Solar PV Scenario:",
                    list(hourly_cache.keys()),
                    key='dispatch_pv_choice'
                )
            with col2:
                bess_choice = st.selectbox(
                    "Battery Size:",
                    sorted(hourly_cache[pv_choice].keys()),
                    format_func=lambda x: f"{int(x):,} MWh",
                    key='dispatch_bess_choice'
                )
            
            hourly_df = hourly_cache[pv_choice][bess_choice]
            typical, low = get_representative_days(hourly_df)
            
            st.subheader("📅 Typical Day Profile")
            fig_typ = chart_dispatch_profile(
                typical,
                f"Typical Day — {pv_choice} | {int(bess_choice):,} MWh Battery",
                elec_mw
            )
            st.plotly_chart(fig_typ, use_container_width=True, key='chart_dispatch_typical')
            st.caption("Representative day with median renewable energy generation")
            
            st.markdown("---")
            
            st.subheader("⚠️ Challenging Day Profile")
            fig_low = chart_dispatch_profile(
                low,
                f"Challenging Day — {pv_choice} | {int(bess_choice):,} MWh Battery",
                elec_mw
            )
            st.plotly_chart(fig_low, use_container_width=True, key='chart_dispatch_low')
            st.caption("Day with low renewable energy generation (10th percentile) — shows system limitations")
            
            st.markdown("---")
            
            # Operational stats
            st.subheader("⚡ Operating Statistics")
            mode_counts = hourly_df['Operation_Mode'].value_counts()
            met = {
                'FIRM': mode_counts.get('FIRM', 0),
                'SUPPLEMENTAL': mode_counts.get('SUPPLEMENTAL', 0),
                'SHUTDOWN': mode_counts.get('SHUTDOWN', 0),
            }
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Full Power Hours", f"{met['FIRM']:,}", f"{met['FIRM']/8760*100:.1f}%")
            with c2:
                st.metric("Reduced Power Hours", f"{met['SUPPLEMENTAL']:,}", f"{met['SUPPLEMENTAL']/8760*100:.1f}%")
            with c3:
                st.metric("Standby Hours", f"{met['SHUTDOWN']:,}", f"{met['SHUTDOWN']/8760*100:.1f}%")
            with c4:
                cf_avg = hourly_df['Capacity_Factor_%'].mean()
                st.metric("Average Capacity Factor", f"{cf_avg:.2f}%")

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#999;font-size:0.9rem">'
    'Firm Power Optimization Tool v2.1 | HSO Team | '
    'Powered by Python + Streamlit'
    '</div>',
    unsafe_allow_html=True
)
