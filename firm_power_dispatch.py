"""
FIRM POWER DISPATCH ENGINE v1.2
================================
Fixed: run_pv_sensitivity() signature - added pv_reference_mw parameter
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """System configuration - mirrors VBA Input sheet."""
    electrolyzer_capacity_mw: float = 500.0
    hydro_power_mw: float = 250.0
    bess_max_power_mw: float = 500.0
    bess_charge_eff: float = 0.9
    bess_discharge_eff: float = 0.9
    pv_capacity_mw: float = 1000.0
    wind_capacity_mw: float = 1104.0
    h2_conversion_factor: float = 50.0


def run_dispatch(pv_profile, wind_profile, bess_size_mwh, config):
    """
    Run single BESS scenario - exact VBA translation.
    Returns: (hourly_df, summary_dict)
    """
    n_hours = len(pv_profile)
    assert len(wind_profile) == n_hours

    # Pre-allocate 23 columns (matching VBA)
    Hour = np.zeros(n_hours, dtype=int)
    PV_MW = np.zeros(n_hours)
    Wind_MW = np.zeros(n_hours)
    Renewable_MW = np.zeros(n_hours)
    Hydro_MW = np.zeros(n_hours)
    Net_Available_MW = np.zeros(n_hours)
    Electrolyzer_MW = np.zeros(n_hours)
    PV_to_Elec_MW = np.zeros(n_hours)
    Wind_to_Elec_MW = np.zeros(n_hours)
    Hydro_to_Elec_MW = np.zeros(n_hours)
    BESS_to_Elec_MW = np.zeros(n_hours)
    BESS_Charge_Before_Eff = np.zeros(n_hours)
    BESS_Charge_After_Eff = np.zeros(n_hours)
    BESS_Charge_Loss = np.zeros(n_hours)
    BESS_Discharge_Before_Eff = np.zeros(n_hours)
    BESS_Discharge_After_Eff = np.zeros(n_hours)
    BESS_Discharge_Loss = np.zeros(n_hours)
    BESS_SOC_pct = np.zeros(n_hours)
    BESS_Capacity_MWh = np.zeros(n_hours)
    Curtailment_MW = np.zeros(n_hours)
    H2_Production_kg = np.zeros(n_hours)
    Capacity_Factor_pct = np.zeros(n_hours)
    Operation_Mode = np.empty(n_hours, dtype=object)

    elec_cap = config.electrolyzer_capacity_mw
    hydro_mw = config.hydro_power_mw
    bess_pwr = config.bess_max_power_mw
    chg_eff = config.bess_charge_eff
    dis_eff = config.bess_discharge_eff
    bess_max = bess_size_mwh
    bess_enabled = bess_max > 0

    bess_capacity = bess_max if bess_enabled else 0.0
    if not bess_enabled:
        bess_max = 1e-6

    total_energy_mwh = 0.0
    hours_full = hours_partial = hours_shutdown = 0
    h2_from_full = h2_from_partial = 0.0
    total_charge_loss = total_discharge_loss = total_curtailment = 0.0
    total_renewable_generated = 0.0

    for h in range(n_hours):
        pv_raw = float(pv_profile[h])
        wind_raw = float(wind_profile[h])
        net_pv = max(0.0, pv_raw)
        renewable = net_pv + wind_raw
        total_renewable_generated += renewable

        curtailment = 0.0
        bess_in_bef = bess_in_aft = bess_chg_loss = 0.0
        bess_out_bef = bess_out_aft = bess_dis_loss = 0.0
        pv_to_e = wind_to_e = hydro_to_e = bess_to_e = 0.0

        hydro_to_e = min(elec_cap, hydro_mw)
        power_shortfall = elec_cap - hydro_to_e
        bess_avail_dis = bess_capacity if bess_enabled else 0.0
        combined_power = hydro_to_e + renewable + (bess_avail_dis * dis_eff)

        if combined_power >= elec_cap:
            # FIRM
            if renewable >= power_shortfall:
                if renewable > 0:
                    pv_to_e = (net_pv / renewable) * power_shortfall
                    wind_to_e = (wind_raw / renewable) * power_shortfall
                electrolyzer_mw = elec_cap
                remaining = renewable - power_shortfall
                if bess_enabled and remaining > 0 and bess_capacity < bess_max:
                    avail_space = bess_max - bess_capacity
                    bess_in_bef = min(remaining, bess_pwr, avail_space / chg_eff)
                    bess_in_aft = bess_in_bef * chg_eff
                    bess_chg_loss = bess_in_bef - bess_in_aft
                    bess_capacity += bess_in_aft
                    curtailment = remaining - bess_in_bef
                else:
                    curtailment = remaining
            else:
                pv_to_e = net_pv
                wind_to_e = wind_raw
                add_shortfall = power_shortfall - renewable
                if bess_enabled:
                    bess_out_bef = min(add_shortfall / dis_eff, bess_capacity)
                    bess_out_aft = bess_out_bef * dis_eff
                    bess_dis_loss = bess_out_bef - bess_out_aft
                    bess_capacity -= bess_out_bef
                    bess_to_e = bess_out_aft
                electrolyzer_mw = elec_cap
                curtailment = 0.0
            operation_mode = "FIRM"
            hours_full += 1
            h2_from_full += (electrolyzer_mw * 1000.0 / config.h2_conversion_factor)

        elif hydro_mw >= 250.0:
            # SUPPLEMENTAL
            electrolyzer_mw = 250.0
            hydro_to_e = 250.0
            pv_to_e = wind_to_e = bess_to_e = 0.0
            if bess_enabled and renewable > 0 and bess_capacity < bess_max:
                avail_space = bess_max - bess_capacity
                bess_in_bef = min(renewable, bess_pwr, avail_space / chg_eff)
                bess_in_aft = bess_in_bef * chg_eff
                bess_chg_loss = bess_in_bef - bess_in_aft
                bess_capacity += bess_in_aft
                curtailment = renewable - bess_in_bef
            else:
                curtailment = renewable
            operation_mode = "SUPPLEMENTAL"
            hours_partial += 1
            h2_from_partial += (electrolyzer_mw * 1000.0 / config.h2_conversion_factor)

        else:
            # SHUTDOWN
            electrolyzer_mw = 0.0
            hydro_to_e = pv_to_e = wind_to_e = bess_to_e = 0.0
            total_avail = hydro_mw + renewable
            if bess_enabled and total_avail > 0 and bess_capacity < bess_max:
                avail_space = bess_max - bess_capacity
                bess_in_bef = min(total_avail, bess_pwr, avail_space / chg_eff)
                bess_in_aft = bess_in_bef * chg_eff
                bess_chg_loss = bess_in_bef - bess_in_aft
                bess_capacity += bess_in_aft
                curtailment = total_avail - bess_in_bef
            else:
                curtailment = total_avail
            operation_mode = "SHUTDOWN"
            hours_shutdown += 1

        total_charge_loss += bess_chg_loss
        total_discharge_loss += bess_dis_loss
        total_curtailment += curtailment
        total_energy_mwh += electrolyzer_mw

        bess_soc = (bess_capacity / bess_max) * 100.0 if bess_max > 1e-5 else 0.0
        h2_prod = electrolyzer_mw * 1000.0 / config.h2_conversion_factor
        cf = (electrolyzer_mw / elec_cap) * 100.0 if elec_cap > 0 else 0.0

        Hour[h] = h
        PV_MW[h] = pv_raw
        Wind_MW[h] = wind_raw
        Renewable_MW[h] = renewable
        Hydro_MW[h] = hydro_mw
        Net_Available_MW[h] = electrolyzer_mw
        Electrolyzer_MW[h] = electrolyzer_mw
        PV_to_Elec_MW[h] = pv_to_e
        Wind_to_Elec_MW[h] = wind_to_e
        Hydro_to_Elec_MW[h] = hydro_to_e
        BESS_to_Elec_MW[h] = bess_to_e
        BESS_Charge_Before_Eff[h] = bess_in_bef
        BESS_Charge_After_Eff[h] = bess_in_aft
        BESS_Charge_Loss[h] = bess_chg_loss
        BESS_Discharge_Before_Eff[h] = bess_out_bef
        BESS_Discharge_After_Eff[h] = bess_out_aft
        BESS_Discharge_Loss[h] = bess_dis_loss
        BESS_SOC_pct[h] = bess_soc
        BESS_Capacity_MWh[h] = bess_capacity
        Curtailment_MW[h] = curtailment
        H2_Production_kg[h] = h2_prod
        Capacity_Factor_pct[h] = cf
        Operation_Mode[h] = operation_mode

    overall_cf = (total_energy_mwh / (elec_cap * n_hours)) * 100.0
    firm_cf = (hours_full / n_hours) * 100.0
    utilization = ((hours_full + hours_partial) / n_hours) * 100.0
    supplemental = overall_cf - firm_cf
    curtail_pct = (total_curtailment / total_renewable_generated * 100.0) if total_renewable_generated > 0 else 0.0
    operating_hours_firm = hours_full

    hourly_df = pd.DataFrame({
        'Hour': Hour,
        'PV_MW': PV_MW,
        'Wind_MW': Wind_MW,
        'Renewable_MW': Renewable_MW,
        'Hydro_MW': Hydro_MW,
        'Net_Available_MW': Net_Available_MW,
        'Electrolyzer_MW': Electrolyzer_MW,
        'PV_to_Elec_MW': PV_to_Elec_MW,
        'Wind_to_Elec_MW': Wind_to_Elec_MW,
        'Hydro_to_Elec_MW': Hydro_to_Elec_MW,
        'BESS_to_Elec_MW': BESS_to_Elec_MW,
        'BESS_Charge_Before_Eff_MWh': BESS_Charge_Before_Eff,
        'BESS_Charge_After_Eff_MWh': BESS_Charge_After_Eff,
        'BESS_Charge_Loss_MWh': BESS_Charge_Loss,
        'BESS_Discharge_Before_Eff_MWh': BESS_Discharge_Before_Eff,
        'BESS_Discharge_After_Eff_MWh': BESS_Discharge_After_Eff,
        'BESS_Discharge_Loss_MWh': BESS_Discharge_Loss,
        'BESS_SOC_%': BESS_SOC_pct,
        'BESS_Capacity_MWh': BESS_Capacity_MWh,
        'Curtailment_MW': Curtailment_MW,
        'H2_Production_kg/h': H2_Production_kg,
        'Capacity_Factor_%': Capacity_Factor_pct,
        'Operation_Mode': Operation_Mode,
    })

    hourly_df['Day'] = hourly_df['Hour'] // 24
    days_24h = int(hourly_df.groupby('Day')['Operation_Mode'].apply(lambda x: (x == 'FIRM').all()).sum())

    summary = {
        'bess_size_mwh': bess_size_mwh,
        'overall_cf_pct': round(overall_cf, 2),
        'firm_cf_pct': round(firm_cf, 2),
        'supplemental_cf_pct': round(supplemental, 2),
        'utilization_pct': round(utilization, 2),
        'hours_full_capacity': hours_full,
        'hours_partial_capacity': hours_partial,
        'hours_shutdown': hours_shutdown,
        'operating_hours': operating_hours_firm,
        'days_full_24h': days_24h,
        'total_energy_mwh': round(total_energy_mwh, 1),
        'h2_from_full_kg': round(h2_from_full, 1),
        'h2_from_partial_kg': round(h2_from_partial, 1),
        'total_h2_kg': round(h2_from_full + h2_from_partial, 1),
        'total_renewable_gen_mwh': round(total_renewable_generated, 1),
        'total_curtailment_mwh': round(total_curtailment, 1),
        'curtailment_pct': round(curtail_pct, 2),
        'total_charge_loss_mwh': round(total_charge_loss, 1),
        'total_discharge_loss_mwh': round(total_discharge_loss, 1),
    }

    return hourly_df, summary


def run_bess_sensitivity(pv_profile, wind_profile, bess_sizes, config, progress_callback=None):
    results = []
    hourly_data = {}
    for idx, bess_size in enumerate(bess_sizes):
        if progress_callback:
            progress_callback(idx, len(bess_sizes), bess_size)
        hourly_df, summary = run_dispatch(pv_profile, wind_profile, bess_size, config)
        results.append(summary)
        hourly_data[bess_size] = hourly_df
    return pd.DataFrame(results), hourly_data


def run_pv_sensitivity(pv_profile_ref, wind_profile, bess_sizes, config,
                       pv_cases=None, pv_reference_mw=1000.0, progress_callback=None):
    """
    FIXED: Added pv_reference_mw parameter.
    """
    if pv_cases is None:
        pv_cases = {"1000 MW PV": 1000.0, "500 MW PV": 500.0}

    pv_results = {}
    for label, pv_mw in pv_cases.items():
        scale = pv_mw / pv_reference_mw
        scaled_pv = pv_profile_ref * scale

        cfg = SystemConfig(
            electrolyzer_capacity_mw=config.electrolyzer_capacity_mw,
            hydro_power_mw=config.hydro_power_mw,
            bess_max_power_mw=config.bess_max_power_mw,
            bess_charge_eff=config.bess_charge_eff,
            bess_discharge_eff=config.bess_discharge_eff,
            pv_capacity_mw=pv_mw,
            wind_capacity_mw=config.wind_capacity_mw,
            h2_conversion_factor=config.h2_conversion_factor,
        )

        summary_df, hourly_data = run_bess_sensitivity(scaled_pv, wind_profile, bess_sizes, cfg, progress_callback)
        pv_results[label] = {'summary': summary_df, 'hourly': hourly_data}

    return pv_results


def get_representative_days(hourly_df):
    df = hourly_df.copy()
    df['Day'] = df['Hour'] // 24
    df['Hour_of_Day'] = df['Hour'] % 24

    daily_renewable = df.groupby('Day')['Renewable_MW'].sum()
    median_day = daily_renewable.sort_values().index[len(daily_renewable) // 2]
    typical_day = df[df['Day'] == median_day].copy()

    p10_value = daily_renewable.quantile(0.10)
    low_day = (daily_renewable - p10_value).abs().idxmin()
    low_renewable_day = df[df['Day'] == low_day].copy()

    return typical_day, low_renewable_day
