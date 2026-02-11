"""
FIRM POWER CHARTS
=================
Reproduces all charts from the Finschhafen Feasibility Study slides.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Colour palette (matches slide style) ─────────────────────────────────────
COLORS = {
    'hydro':       'rgba(230, 115, 0, 0.85)',    # Orange
    'pv':          'rgba(76, 153, 0, 0.85)',     # Green
    'wind':        'rgba(100, 180, 220, 0.85)',  # Light blue
    'bess_soc':    'rgba(148, 0, 211, 0.9)',     # Purple
    'firm_power':  '#FFD700',                    # Gold
    'pv_1000':     '#1a237e',                    # Dark navy
    'pv_500':      '#1976D2',                    # Mid blue
    'bar_1000':    '#1a237e',
    'bar_500':     '#1E90FF',
    'line_500':    '#90CAF9',
}


def chart_dispatch_profile(day_df: pd.DataFrame, title: str,
                           firm_power_mw: float = 500.0) -> go.Figure:
    """
    Stacked area dispatch chart with BESS SOC secondary axis.
    Reproduces slides 152 (typical day) and 153 (low renewable day).
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    hours = day_df['Hour_of_Day'].values

    # Stacked generation areas
    fig.add_trace(go.Scatter(
        x=hours, y=day_df['Hydro_MW'],
        name='Hydro_MW', mode='lines',
        line=dict(width=0),
        stackgroup='gen',
        fillcolor=COLORS['hydro'],
        hovertemplate='Hour %{x}<br>Hydro: %{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hours, y=day_df['PV_MW'].clip(lower=0),
        name='PV_MW', mode='lines',
        line=dict(width=0),
        stackgroup='gen',
        fillcolor=COLORS['pv'],
        hovertemplate='Hour %{x}<br>PV: %{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hours, y=day_df['Wind_MW'],
        name='Wind_MW', mode='lines',
        line=dict(width=0),
        stackgroup='gen',
        fillcolor=COLORS['wind'],
        hovertemplate='Hour %{x}<br>Wind: %{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    # Firm power line
    fig.add_trace(go.Scatter(
        x=hours, y=[firm_power_mw] * len(hours),
        name='Firm Power_MW',
        mode='lines',
        line=dict(color=COLORS['firm_power'], width=2.5, dash='solid'),
        hovertemplate='Firm Power: %{y:.0f} MW<extra></extra>'
    ), secondary_y=False)

    # BESS SOC on secondary axis
    fig.add_trace(go.Scatter(
        x=hours, y=day_df['BESS_SOC_pct'],
        name='BESS_SOC %',
        mode='lines',
        line=dict(color=COLORS['bess_soc'], width=2.5),
        hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'
    ), secondary_y=True)

    fig.update_xaxes(title_text='Hours', tickmode='linear', tick0=1, dtick=2)
    fig.update_yaxes(title_text='Power (MW)', secondary_y=False, rangemode='tozero')
    fig.update_yaxes(title_text='BESS SoC %', secondary_y=True, range=[0, 110])

    fig.update_layout(
        title=title,
        hovermode='x unified',
        height=480,
        legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig


def chart_cf_vs_bess(pv_results: dict, metric: str = 'overall_cf_pct') -> go.Figure:
    """
    Capacity Factor % vs BESS size - line chart.
    Reproduces slide 155 (BESS Sensitivity Analysis).
    """
    fig = go.Figure()

    styles = {
        '1000 MW PV': dict(color=COLORS['pv_1000'], width=2.5, symbol='circle'),
        '500 MW PV':  dict(color=COLORS['pv_500'],  width=2.5, symbol='circle-open'),
    }

    label_map = {
        'overall_cf_pct': 'Annual Capacity Factor (%)',
        'firm_cf_pct':    'Firm CF (%)',
        'curtailment_pct': 'Curtailment (%)',
    }

    for label, data in pv_results.items():
        df = data['summary']
        style = styles.get(label, dict(color='grey', width=2))

        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'],
            y=df[metric],
            name=label,
            mode='lines+markers+text',
            line=dict(color=style['color'], width=style['width']),
            marker=dict(symbol=style.get('symbol', 'circle'), size=8, color=style['color']),
            text=[f"{v:.1f}%" for v in df[metric]],
            textposition='top center',
            hovertemplate='BESS: %{x:,} MWh<br>' + label_map.get(metric, metric) + ': %{y:.2f}%<extra>' + label + '</extra>'
        ))

    fig.update_layout(
        title=f'System Performance vs BESS Size (PV Capacity Comparison)',
        xaxis_title='BESS Size (MWh)',
        yaxis_title=label_map.get(metric, metric),
        height=460,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=-0.20, xanchor='center', x=0.5),
    )
    fig.update_xaxes(showgrid=True, gridcolor='#e0e0e0')
    fig.update_yaxes(showgrid=True, gridcolor='#e0e0e0')
    return fig


def chart_days_vs_bess(pv_results: dict) -> go.Figure:
    """
    Days with 24h full operation + operating hours vs BESS size.
    Reproduces slide 157.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    bar_colors = {'1000 MW PV': COLORS['bar_1000'], '500 MW PV': COLORS['bar_500']}
    line_colors = {'1000 MW PV': '#90CAF9', '500 MW PV': COLORS['line_500']}

    for label, data in pv_results.items():
        df = data['summary']
        bess_x = df['bess_size_mwh']

        # Bar: days with 24h full operation
        fig.add_trace(go.Bar(
            x=bess_x, y=df['days_full_24h'],
            name=f'{label} - Days',
            marker_color=bar_colors.get(label, 'grey'),
            text=df['days_full_24h'],
            textposition='outside',
            offsetgroup=label,
            hovertemplate='BESS: %{x:,} MWh<br>Days: %{y}<extra>' + label + '</extra>'
        ), secondary_y=False)

        # Line: operating hours
        fig.add_trace(go.Scatter(
            x=bess_x, y=df['operating_hours'],
            name=f'{label} - Hrs',
            mode='lines+markers+text',
            line=dict(color=line_colors.get(label, 'grey'), width=2),
            marker=dict(size=7),
            text=[str(int(v)) for v in df['operating_hours']],
            textposition='top center',
            hovertemplate='BESS: %{x:,} MWh<br>Operating Hrs: %{y:,}<extra>' + label + '</extra>'
        ), secondary_y=True)

    fig.update_xaxes(title_text='BESS Size (MWh)')
    fig.update_yaxes(title_text='Number of Days with 24h Full Output', secondary_y=False)
    fig.update_yaxes(title_text='Operating Hours (Annual)', secondary_y=True)
    fig.update_layout(
        title='Days of High Performance vs BESS Size',
        height=460,
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
    )
    return fig


def chart_curtailment_vs_bess(pv_results: dict) -> go.Figure:
    """
    Curtailment % vs BESS size with difference line.
    Reproduces slide 158.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    pv_labels = list(pv_results.keys())
    bar_colors = {'1000 MW PV': COLORS['bar_1000'], '500 MW PV': COLORS['bar_500']}

    for label in pv_labels:
        df = pv_results[label]['summary']
        fig.add_trace(go.Bar(
            x=df['bess_size_mwh'], y=df['curtailment_pct'],
            name=label,
            marker_color=bar_colors.get(label, 'grey'),
            text=[f"{v:.1f}%" for v in df['curtailment_pct']],
            textposition='outside',
            offsetgroup=label,
            hovertemplate='BESS: %{x:,} MWh<br>Curtailment: %{y:.2f}%<extra>' + label + '</extra>'
        ), secondary_y=False)

    # Difference line (if two PV cases)
    if len(pv_labels) == 2:
        df1 = pv_results[pv_labels[0]]['summary'].set_index('bess_size_mwh')
        df2 = pv_results[pv_labels[1]]['summary'].set_index('bess_size_mwh')
        common_idx = df1.index.intersection(df2.index)
        diff = (df1.loc[common_idx, 'curtailment_pct'] - df2.loc[common_idx, 'curtailment_pct']).abs()

        fig.add_trace(go.Scatter(
            x=diff.index, y=diff.values,
            name='Difference %',
            mode='lines+markers+text',
            line=dict(color='#66BB6A', width=2),
            marker=dict(size=8, symbol='circle'),
            text=[f"{v:.2f}%" for v in diff.values],
            textposition='top center',
        ), secondary_y=True)

    fig.update_xaxes(title_text='BESS Size (MWh)')
    fig.update_yaxes(title_text='Curtailment (%)', secondary_y=False)
    fig.update_yaxes(title_text='Difference %', secondary_y=True)
    fig.update_layout(
        title='Curtailment % vs BESS Size',
        height=460,
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
    )
    return fig


def chart_baseline_without_bess(baseline_results: dict) -> go.Figure:
    """
    Bar+line chart showing CF% and operating hours WITHOUT BESS.
    Reproduces slide 154.
    """
    labels  = list(baseline_results.keys())
    cf_vals = [baseline_results[k]['overall_cf_pct'] for k in labels]
    hr_vals = [baseline_results[k]['operating_hours'] for k in labels]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=labels, y=cf_vals,
        name='Annual CF %',
        marker_color=[COLORS['bar_1000'], COLORS['bar_500']],
        text=[f"{v:.2f}%" for v in cf_vals],
        textposition='outside',
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=labels, y=hr_vals,
        name='Operating Hours',
        mode='lines+markers+text',
        line=dict(color='#90CAF9', width=2),
        marker=dict(size=10),
        text=[str(int(v)) for v in hr_vals],
        textposition='top right',
    ), secondary_y=True)

    fig.update_yaxes(title_text='Annual CF %', secondary_y=False, range=[70, 82])
    fig.update_yaxes(title_text='Operating Hours (Annual)', secondary_y=True)
    fig.update_layout(
        title='Annual Operating Hours Without BESS',
        height=420,
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    return fig


def chart_cf_vs_firm_power(firm_power_results: dict) -> go.Figure:
    """
    CF% vs Firm Power Output (bar chart).
    Reproduces slide 160.
    """
    labels = list(firm_power_results.keys())
    cf_vals = [firm_power_results[k]['overall_cf_pct'] for k in labels]

    fig = go.Figure(go.Bar(
        x=labels, y=cf_vals,
        marker_color='#1976D2',
        text=[f"{v:.2f}%" for v in cf_vals],
        textposition='outside',
    ))

    fig.update_layout(
        title='Capacity Factor vs Firm Power Output',
        xaxis_title='Firm Power Output (MW)',
        yaxis_title='Capacity Factor %',
        height=420,
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(range=[75, 105]),
    )
    return fig


def build_summary_table(pv_results: dict) -> pd.DataFrame:
    """Build comparison table for display in Streamlit."""
    rows = []
    for pv_label, data in pv_results.items():
        for _, row in data['summary'].iterrows():
            rows.append({
                'PV Case':              pv_label,
                'BESS Size (MWh)':      int(row['bess_size_mwh']),
                'Overall CF (%)':       f"{row['overall_cf_pct']:.2f}",
                'Firm CF (%)':          f"{row['firm_cf_pct']:.2f}",
                'Operating Hrs':        int(row['operating_hours']),
                'Days 24h Full':        int(row['days_full_24h']),
                'Curtailment (%)':      f"{row['curtailment_pct']:.2f}",
                'Total H2 (tonnes/yr)': f"{row['total_h2_kg'] / 1000:.1f}",
                'Total Energy (GWh)':   f"{row['total_energy_mwh'] / 1000:.1f}",
            })
    return pd.DataFrame(rows)
