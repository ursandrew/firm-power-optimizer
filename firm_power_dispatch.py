"""
FIRM POWER DISPATCH ENGINE
==========================
Direct Python translation of VBA BESS Sensitivity Analysis
Three-Tier Dispatch: 500 MW Firm | 250 MW Supplemental | 0 MW Shutdown

System: 250 MW Hydro (24/7) + Variable PV + Variable Wind + BESS
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemConfig:
    """System configuration parameters."""
    electrolyzer_capacity_mw: float = 500.0    # Firm power target
    hydro_power_mw: float = 250.0              # Constant 24/7 hydro baseload
    bess_max_power_mw: float = 500.0           # BESS max charge/discharge power
    bess_charge_eff: float = 0.9               # Charging efficiency
    bess_discharge_eff: float = 0.9            # Discharge efficiency
    pv_capacity_mw: float = 500.0              # PV installed capacity (for scaling profiles)
    wind_capacity_mw: float = 1104.0           # Wind installed capacity (for scaling profiles)
    h2_conversion_factor: float = 50.0         # kWh per kg H2 (50 kWh/kg)


def run_dispatch(
    pv_profile: np.ndarray,
    wind_profile: np.ndarray,
    bess_size_mwh: float,
    config: SystemConfig
) -> tuple[pd.DataFrame, dict]:
    """
    Run single BESS scenario dispatch simulation.
    
    Args:
        pv_profile:   8760 hourly PV generation values in MW (actual, not normalised)
        wind_profile: 8760 hourly Wind generation values in MW (actual, not normalised)
        bess_size_mwh: BESS energy capacity in MWh
        config: SystemConfig parameters
    
    Returns:
        hourly_df:  8760-row DataFrame with all dispatch columns
        summary:    Dict of performance metrics (mirrors VBA summary block)
    """
    n_hours = len(pv_profile)
    assert len(wind_profile) == n_hours, "PV and Wind profiles must be same length"

    # ── Pre-allocate output arrays ──────────────────────────────────────────
    arr = {
        'Hour':                         np.zeros(n_hours, dtype=int),
        'PV_MW':                        np.zeros(n_hours),
        'Wind_MW':                      np.zeros(n_hours),
        'Renewable_MW':                 np.zeros(n_hours),
        'Hydro_MW':                     np.zeros(n_hours),
        'Net_Available_MW':             np.zeros(n_hours),
        'Electrolyzer_MW':              np.zeros(n_hours),
        'PV_to_Elec_MW':               np.zeros(n_hours),
        'Wind_to_Elec_MW':             np.zeros(n_hours),
        'Hydro_to_Elec_MW':            np.zeros(n_hours),
        'BESS_to_Elec_MW':             np.zeros(n_hours),
        'BESS_Charge_Before_Eff_MWh':  np.zeros(n_hours),
        'BESS_Charge_After_Eff_MWh':   np.zeros(n_hours),
        'BESS_Charge_Loss_MWh':        np.zeros(n_hours),
        'BESS_Discharge_Before_Eff_MWh': np.zeros(n_hours),
        'BESS_Discharge_After_Eff_MWh':  np.zeros(n_hours),
        'BESS_Discharge_Loss_MWh':     np.zeros(n_hours),
        'BESS_SOC_pct':                np.zeros(n_hours),
        'BESS_Capacity_MWh':           np.zeros(n_hours),
        'Curtailment_MW':              np.zeros(n_hours),
        'H2_Production_kg_per_h':      np.zeros(n_hours),
        'Capacity_Factor_pct':         np.zeros(n_hours),
        'Operation_Mode':              np.empty(n_hours, dtype=object),
    }

    # ── Config shortcuts ────────────────────────────────────────────────────
    elec_cap   = config.electrolyzer_capacity_mw
    hydro_mw   = config.hydro_power_mw
    bess_pwr   = config.bess_max_power_mw
    chg_eff    = config.bess_charge_eff
    dis_eff    = config.bess_discharge_eff
    bess_max   = bess_size_mwh
    bess_enabled = bess_max > 0

    # BESS starts full (matches VBA initialisation: bess_capacity = bess_max_capacity)
    bess_capacity = bess_max if bess_enabled else 0.0
    if not bess_enabled:
        bess_max = 1e-6  # avoid div-by-zero

    # ── Performance counters ────────────────────────────────────────────────
    total_energy_mwh        = 0.0
    hours_full              = 0
    hours_partial           = 0
    hours_shutdown          = 0
    h2_from_full            = 0.0
    h2_from_partial         = 0.0
    total_charge_loss       = 0.0
    total_discharge_loss    = 0.0
    total_curtailment       = 0.0
    total_renewable_generated = 0.0

    # ── Hourly loop (mirrors VBA row_change loop) ────────────────────────────
    for h in range(n_hours):
        pv_raw  = float(pv_profile[h])
        wind_raw = float(wind_profile[h])

        # Clamp negative PV (night hours in raw data show -1.29 MW)
        net_pv  = max(0.0, pv_raw)
        renewable = net_pv + wind_raw

        total_renewable_generated += renewable

        # Reset hourly
        curtailment = 0.0
        bess_in_before = bess_in_after = bess_charge_loss = 0.0
        bess_out_before = bess_out_after = bess_discharge_loss = 0.0
        pv_to_elec = wind_to_elec = hydro_to_elec = bess_to_elec = 0.0

        # ── Assess whether FIRM tier is achievable ──────────────────────────
        hydro_to_elec = min(elec_cap, hydro_mw)
        power_shortfall = elec_cap - hydro_to_elec

        bess_available_discharge = bess_capacity if bess_enabled else 0.0
        combined_power = hydro_to_elec + renewable + (bess_available_discharge * dis_eff)

        if combined_power >= elec_cap:
            # ══════════════════════════════════════════════
            # TIER 1: FIRM (500 MW)
            # ══════════════════════════════════════════════
            if renewable >= power_shortfall:
                # Renewables cover the shortfall; split PV/Wind proportionally
                if renewable > 0:
                    pv_to_elec   = (net_pv / renewable) * power_shortfall
                    wind_to_elec = (wind_raw / renewable) * power_shortfall

                electrolyzer_mw = elec_cap
                remaining = renewable - power_shortfall

                if bess_enabled and remaining > 0 and bess_capacity < bess_max:
                    bess_available_space = bess_max - bess_capacity
                    bess_in_before = min(remaining, bess_pwr, bess_available_space / chg_eff)
                    bess_in_after  = bess_in_before * chg_eff
                    bess_charge_loss = bess_in_before - bess_in_after
                    bess_capacity  += bess_in_after
                    curtailment = remaining - bess_in_before
                else:
                    curtailment = remaining

            else:
                # BESS must cover the remaining shortfall after all renewables used
                pv_to_elec   = net_pv
                wind_to_elec = wind_raw
                additional_shortfall = power_shortfall - renewable

                if bess_enabled:
                    bess_out_before = min(additional_shortfall / dis_eff, bess_capacity)
                    bess_out_after  = bess_out_before * dis_eff
                    bess_discharge_loss = bess_out_before - bess_out_after
                    bess_capacity  -= bess_out_before
                    bess_to_elec    = bess_out_after

                electrolyzer_mw = elec_cap
                curtailment = 0.0

            operation_mode = "FIRM"
            hours_full += 1
            h2_from_full += (electrolyzer_mw * 1000 / config.h2_conversion_factor)

        elif hydro_mw >= 250.0:
            # ══════════════════════════════════════════════
            # TIER 2: SUPPLEMENTAL (250 MW from Hydro only)
            # ══════════════════════════════════════════════
            electrolyzer_mw = 250.0
            hydro_to_elec   = 250.0
            pv_to_elec = wind_to_elec = bess_to_elec = 0.0

            # Charge BESS with all available renewables during this tier
            if bess_enabled and renewable > 0 and bess_capacity < bess_max:
                bess_available_space = bess_max - bess_capacity
                bess_in_before = min(renewable, bess_pwr, bess_available_space / chg_eff)
                bess_in_after  = bess_in_before * chg_eff
                bess_charge_loss = bess_in_before - bess_in_after
                bess_capacity  += bess_in_after
                curtailment = renewable - bess_in_before
            else:
                curtailment = renewable

            operation_mode = "SUPPLEMENTAL"
            hours_partial += 1
            h2_from_partial += (electrolyzer_mw * 1000 / config.h2_conversion_factor)

        else:
            # ══════════════════════════════════════════════
            # TIER 3: SHUTDOWN (0 MW)
            # ══════════════════════════════════════════════
            electrolyzer_mw = 0.0
            hydro_to_elec = pv_to_elec = wind_to_elec = bess_to_elec = 0.0

            total_available = hydro_mw + renewable
            if bess_enabled and total_available > 0 and bess_capacity < bess_max:
                bess_available_space = bess_max - bess_capacity
                bess_in_before = min(total_available, bess_pwr, bess_available_space / chg_eff)
                bess_in_after  = bess_in_before * chg_eff
                bess_charge_loss = bess_in_before - bess_in_after
                bess_capacity  += bess_in_after
                curtailment = total_available - bess_in_before
            else:
                curtailment = total_available

            operation_mode = "SHUTDOWN"
            hours_shutdown += 1

        # ── Accumulate losses ──────────────────────────────────────────────
        total_charge_loss    += bess_charge_loss
        total_discharge_loss += bess_discharge_loss
        total_curtailment    += curtailment
        total_energy_mwh     += electrolyzer_mw

        # ── Derived metrics ────────────────────────────────────────────────
        bess_soc = (bess_capacity / bess_max) * 100 if bess_max > 1e-5 else 0.0
        h2_prod  = electrolyzer_mw * 1000 / config.h2_conversion_factor
        cf       = (electrolyzer_mw / elec_cap) * 100 if elec_cap > 0 else 0.0

        # ── Store in arrays ────────────────────────────────────────────────
        arr['Hour'][h]                          = h
        arr['PV_MW'][h]                         = pv_raw
        arr['Wind_MW'][h]                       = wind_raw
        arr['Renewable_MW'][h]                  = renewable
        arr['Hydro_MW'][h]                      = hydro_mw
        arr['Net_Available_MW'][h]              = electrolyzer_mw
        arr['Electrolyzer_MW'][h]               = electrolyzer_mw
        arr['PV_to_Elec_MW'][h]                 = pv_to_elec
        arr['Wind_to_Elec_MW'][h]               = wind_to_elec
        arr['Hydro_to_Elec_MW'][h]              = hydro_to_elec
        arr['BESS_to_Elec_MW'][h]               = bess_to_elec
        arr['BESS_Charge_Before_Eff_MWh'][h]    = bess_in_before
        arr['BESS_Charge_After_Eff_MWh'][h]     = bess_in_after
        arr['BESS_Charge_Loss_MWh'][h]          = bess_charge_loss
        arr['BESS_Discharge_Before_Eff_MWh'][h] = bess_out_before
        arr['BESS_Discharge_After_Eff_MWh'][h]  = bess_out_after
        arr['BESS_Discharge_Loss_MWh'][h]       = bess_discharge_loss
        arr['BESS_SOC_pct'][h]                  = bess_soc
        arr['BESS_Capacity_MWh'][h]             = bess_capacity
        arr['Curtailment_MW'][h]                = curtailment
        arr['H2_Production_kg_per_h'][h]        = h2_prod
        arr['Capacity_Factor_pct'][h]           = cf
        arr['Operation_Mode'][h]                = operation_mode

    # ── Summary metrics (mirrors VBA "HYBRID PERFORMANCE METRICS") ──────────
    overall_cf    = (total_energy_mwh / (elec_cap * n_hours)) * 100
    firm_cf       = (hours_full / n_hours) * 100
    utilization   = ((hours_full + hours_partial) / n_hours) * 100
    supplemental  = overall_cf - firm_cf
    curtail_pct   = (total_curtailment / total_renewable_generated * 100) if total_renewable_generated > 0 else 0.0

    # Operating hours (hours where electrolyzer > 0)
    operating_hours = hours_full + hours_partial

    # Days with full 24h operation (all 24 hours of day at FIRM tier)
    hourly_df = pd.DataFrame(arr)
    hourly_df['Day'] = hourly_df['Hour'] // 24
    days_24h = hourly_df.groupby('Day')['Operation_Mode'].apply(
        lambda x: (x == 'FIRM').all()
    ).sum()

    summary = {
        'bess_size_mwh':            bess_size_mwh,
        'overall_cf_pct':           round(overall_cf, 2),
        'firm_cf_pct':              round(firm_cf, 2),
        'supplemental_cf_pct':      round(supplemental, 2),
        'utilization_pct':          round(utilization, 2),
        'hours_full_capacity':      hours_full,
        'hours_partial_capacity':   hours_partial,
        'hours_shutdown':           hours_shutdown,
        'operating_hours':          operating_hours,
        'days_full_24h':            int(days_24h),
        'total_energy_mwh':         round(total_energy_mwh, 1),
        'h2_from_full_kg':          round(h2_from_full, 1),
        'h2_from_partial_kg':       round(h2_from_partial, 1),
        'total_h2_kg':              round(h2_from_full + h2_from_partial, 1),
        'total_renewable_gen_mwh':  round(total_renewable_generated, 1),
        'total_curtailment_mwh':    round(total_curtailment, 1),
        'curtailment_pct':          round(curtail_pct, 2),
        'total_charge_loss_mwh':    round(total_charge_loss, 1),
        'total_discharge_loss_mwh': round(total_discharge_loss, 1),
    }

    return hourly_df, summary


def run_bess_sensitivity(
    pv_profile: np.ndarray,
    wind_profile: np.ndarray,
    bess_sizes: list,
    config: SystemConfig,
    progress_callback=None
) -> tuple[pd.DataFrame, dict]:
    """
    Run sensitivity sweep across multiple BESS sizes.
    
    Returns:
        summary_df:   One row per BESS size with all KPIs
        hourly_data:  Dict {bess_size_mwh: hourly_df}
    """
    results = []
    hourly_data = {}

    for idx, bess_size in enumerate(bess_sizes):
        if progress_callback:
            progress_callback(idx, len(bess_sizes), bess_size)

        hourly_df, summary = run_dispatch(pv_profile, wind_profile, bess_size, config)
        results.append(summary)
        hourly_data[bess_size] = hourly_df

    summary_df = pd.DataFrame(results)
    return summary_df, hourly_data


def run_pv_sensitivity(
    pv_profile_1000mw: np.ndarray,
    wind_profile: np.ndarray,
    bess_sizes: list,
    config: SystemConfig,
    pv_cases: dict = None,
    progress_callback=None
) -> dict:
    """
    Run BESS sensitivity for multiple PV capacity cases.
    Replicates the "500 MW PV vs 1000 MW PV" comparison in the slides.
    
    Args:
        pv_profile_1000mw: Full resolution 1000 MW PV profile
        wind_profile:       Full wind profile
        pv_cases:           Dict {label: mw_capacity} e.g. {"1000 MW PV": 1000, "500 MW PV": 500}
    
    Returns:
        Dict {pv_label: summary_df}
    """
    if pv_cases is None:
        pv_cases = {"1000 MW PV": 1000.0, "500 MW PV": 500.0}

    pv_results = {}
    for label, pv_mw in pv_cases.items():
        # Scale profile proportionally
        scale = pv_mw / 1000.0  # assumes pv_profile_1000mw is normalised to 1000 MW
        scaled_pv = pv_profile_1000mw * scale

        cfg = SystemConfig(
            electrolyzer_capacity_mw=config.electrolyzer_capacity_mw,
            hydro_power_mw=config.hydro_power_mw,
            bess_max_power_mw=config.bess_max_power_mw,
            bess_charge_eff=config.bess_charge_eff,
            bess_discharge_eff=config.bess_discharge_eff,
            pv_capacity_mw=pv_mw,
            wind_capacity_mw=config.wind_capacity_mw,
        )

        summary_df, hourly_data = run_bess_sensitivity(
            scaled_pv, wind_profile, bess_sizes, cfg, progress_callback
        )
        pv_results[label] = {
            'summary': summary_df,
            'hourly':  hourly_data
        }

    return pv_results


def get_representative_days(hourly_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract representative typical day and low-renewable day for dispatch charts.
    Matches the two dispatch profile slides (slides 152 & 153).
    """
    df = hourly_df.copy()
    df['Day'] = df['Hour'] // 24
    df['Hour_of_Day'] = df['Hour'] % 24

    # Typical day: day with median renewable generation
    daily_renewable = df.groupby('Day')['Renewable_MW'].sum()
    median_day = daily_renewable.sort_values().index[len(daily_renewable) // 2]
    typical_day = df[df['Day'] == median_day].copy()

    # Low renewable day: day closest to 10th percentile renewable (not absolute minimum)
    p10_value = daily_renewable.quantile(0.10)
    low_day = (daily_renewable - p10_value).abs().idxmin()
    low_renewable_day = df[df['Day'] == low_day].copy()

    return typical_day, low_renewable_day
