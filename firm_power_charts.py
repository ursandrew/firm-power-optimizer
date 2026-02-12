"""
FIRM POWER CHARTS - CLEAN PROFESSIONAL VERSION
===============================================
Reproduces Finschhafen slides with readable, high-contrast design.
No "overall CF" or "supplemental CF" terminology in UI - only "Capacity Factor".
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Professional color palette - high contrast, colorblind-safe
COLORS = {
    'hydro':       '#FF6B35',   # Bright orange (distinct from wind/PV)
    'pv':          '#4CAF50',   # Green
    'wind':        '#2196F3',   # Blue
    'bess_soc':    '#9C27B0',   # Purple
    'firm_power':  '#FFD700',   # Gold line
    'pv_1000':     '#1565C0',   # Dark blue (1000 MW PV)
    'pv_500':      '#42A5F5',   # Light blue (500 MW PV)
}

# Chart styling constants
FONT_FAMILY = 'Arial, sans-serif'
TITLE_SIZE = 18
AXIS_TITLE_SIZE = 14
AXIS_LABEL_SIZE = 12
LEGEND_SIZE = 12


def chart_dispatch_profile(day_df: pd.DataFrame, title: str, firm_power_mw: float = 500.0):
    """
    Stacked area dispatch + BESS SOC line (slides 152-153 style).
    Clean, readable version with proper contrast.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    hours = day_df['Hour_of_Day'].values

    # Stacked generation (Hydro → PV → Wind order, bottom to top)
    fig.add_trace(go.Scatter(
        x=hours,
        y=day_df['Hydro_MW'],
        name='Hydro',
        mode='lines',
        line=dict(width=0),
        stackgroup='generation',
        fillcolor=COLORS['hydro'],
        hovertemplate='<b>Hydro</b><br>Hour %{x}<br>%{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hours,
        y=day_df['PV_MW'].clip(lower=0),
        name='PV',
        mode='lines',
        line=dict(width=0),
        stackgroup='generation',
        fillcolor=COLORS['pv'],
        hovertemplate='<b>PV</b><br>Hour %{x}<br>%{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=hours,
        y=day_df['Wind_MW'],
        name='Wind',
        mode='lines',
        line=dict(width=0),
        stackgroup='generation',
        fillcolor=COLORS['wind'],
        hovertemplate='<b>Wind</b><br>Hour %{x}<br>%{y:.1f} MW<extra></extra>'
    ), secondary_y=False)

    # Firm power line (thick gold line)
    fig.add_trace(go.Scatter(
        x=hours,
        y=[firm_power_mw] * len(hours),
        name='Firm Power Target',
        mode='lines',
        line=dict(color=COLORS['firm_power'], width=3),
        hovertemplate='<b>Target</b><br>%{y:.0f} MW<extra></extra>'
    ), secondary_y=False)

    # BESS SOC on secondary axis (thick purple line)
    fig.add_trace(go.Scatter(
        x=hours,
        y=day_df['BESS_SOC_%'],
        name='BESS SOC',
        mode='lines',
        line=dict(color=COLORS['bess_soc'], width=3),
        hovertemplate='<b>BESS SOC</b><br>Hour %{x}<br>%{y:.1f}%<extra></extra>'
    ), secondary_y=True)

    # Axes
    fig.update_xaxes(
        title_text='<b>Hour of Day</b>',
        tickmode='linear', tick0=0, dtick=3,
        range=[-0.5, 24.5],
        showgrid=True, gridcolor='#E0E0E0', gridwidth=1,
        title_font=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Power (MW)</b>',
        secondary_y=False,
        rangemode='tozero',
        showgrid=True, gridcolor='#E0E0E0', gridwidth=1,
        title_font=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>BESS SOC (%)</b>',
        secondary_y=True,
        range=[0, 105],
        showgrid=False,
        title_font=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE)
    )

    fig.update_layout(
        title=dict(text=f'<b>{title}</b>', x=0.5, xanchor='center', font=dict(size=TITLE_SIZE)),
        hovermode='x unified',
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=FONT_FAMILY),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=-0.25,
            xanchor='center', x=0.5,
            font=dict(size=LEGEND_SIZE),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC', borderwidth=1
        )
    )
    return fig


def chart_cf_vs_bess(pv_results: dict):
    """
    Capacity Factor vs BESS size (slide 155 style).
    Shows only FIRM CF (labeled as "Capacity Factor" in UI).
    """
    fig = go.Figure()

    line_styles = {
        '1000 MW PV': dict(color=COLORS['pv_1000'], width=3, symbol='circle', dash='solid'),
        '500 MW PV':  dict(color=COLORS['pv_500'],  width=3, symbol='diamond', dash='dash'),
    }

    for label, data in pv_results.items():
        df = data['summary']
        style = line_styles.get(label, dict(color='grey', width=2))

        # Use firm_cf_pct but display as "Capacity Factor"
        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'],
            y=df['firm_cf_pct'],  # Internal: firm CF
            name=label,
            mode='lines+markers+text',
            line=dict(color=style['color'], width=style['width'], dash=style.get('dash', 'solid')),
            marker=dict(symbol=style['symbol'], size=10, color=style['color'], line=dict(width=2, color='white')),
            text=[f"{v:.1f}%" for v in df['firm_cf_pct']],
            textposition='top center',
            textfont=dict(size=11, color=style['color'], family=FONT_FAMILY),
            hovertemplate='<b>' + label + '</b><br>BESS: %{x:,} MWh<br>CF: %{y:.2f}%<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text='<b>Capacity Factor vs BESS Size</b>', x=0.5, xanchor='center', font=dict(size=TITLE_SIZE)),
        xaxis=dict(
            title='<b>BESS Size (MWh)</b>',
            showgrid=True, gridcolor='#E0E0E0',
            title_font=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
            tickfont=dict(size=AXIS_LABEL_SIZE)
        ),
        yaxis=dict(
            title='<b>Capacity Factor (%)</b>',
            showgrid=True, gridcolor='#E0E0E0',
            range=[85, 100],
            title_font=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
            tickfont=dict(size=AXIS_LABEL_SIZE)
        ),
        height=480,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=FONT_FAMILY),
        hovermode='x unified',
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.20, xanchor='center', x=0.5,
            font=dict(size=LEGEND_SIZE), bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC', borderwidth=1
        )
    )
    return fig


def chart_days_vs_bess(pv_results: dict):
    """
    Days with 24h full operation + operating hours (slide 157 style).
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    bar_colors = {'1000 MW PV': COLORS['pv_1000'], '500 MW PV': COLORS['pv_500']}
    line_colors = {'1000 MW PV': '#1E88E5', '500 MW PV': '#64B5F6'}

    for label, data in pv_results.items():
        df = data['summary']
        bess_x = df['bess_size_mwh']

        # Bars: days with 24h full output
        fig.add_trace(go.Bar(
            x=bess_x,
            y=df['days_full_24h'],
            name=f'{label} - Days',
            marker_color=bar_colors.get(label, 'grey'),
            text=df['days_full_24h'],
            textposition='outside',
            textfont=dict(size=11, color=bar_colors.get(label)),
            offsetgroup=label,
            hovertemplate='<b>' + label + '</b><br>BESS: %{x:,} MWh<br>Days: %{y}<extra></extra>'
        ), secondary_y=False)

        # Line: operating hours (firm hours)
        fig.add_trace(go.Scatter(
            x=bess_x,
            y=df['operating_hours'],
            name=f'{label} - Hours',
            mode='lines+markers+text',
            line=dict(color=line_colors.get(label), width=2.5),
            marker=dict(size=8, symbol='circle'),
            text=[str(int(v)) for v in df['operating_hours']],
            textposition='top center',
            textfont=dict(size=10, color=line_colors.get(label)),
            hovertemplate='<b>' + label + '</b><br>BESS: %{x:,} MWh<br>Hours: %{y:,}<extra></extra>'
        ), secondary_y=True)

    fig.update_xaxes(
        title_text='<b>BESS Size (MWh)</b>',
        showgrid=True, gridcolor='#E0E0E0',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Days with 24h Full Output</b>',
        secondary_y=False, rangemode='tozero',
        showgrid=True, gridcolor='#E0E0E0',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Operating Hours (Annual)</b>',
        secondary_y=True, rangemode='tozero',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )

    fig.update_layout(
        title=dict(text='<b>Days of High Performance vs BESS Size</b>', x=0.5, xanchor='center', font=dict(size=TITLE_SIZE)),
        height=480,
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=FONT_FAMILY),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5,
            font=dict(size=LEGEND_SIZE), bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC', borderwidth=1
        )
    )
    return fig


def chart_curtailment_vs_bess(pv_results: dict):
    """
    Curtailment % vs BESS size with difference line (slide 158 style).
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    pv_labels = list(pv_results.keys())
    bar_colors = {'1000 MW PV': COLORS['pv_1000'], '500 MW PV': COLORS['pv_500']}

    for label in pv_labels:
        df = pv_results[label]['summary']
        fig.add_trace(go.Bar(
            x=df['bess_size_mwh'],
            y=df['curtailment_pct'],
            name=label,
            marker_color=bar_colors.get(label, 'grey'),
            text=[f"{v:.1f}%" for v in df['curtailment_pct']],
            textposition='outside',
            textfont=dict(size=11, color=bar_colors.get(label)),
            offsetgroup=label,
            hovertemplate='<b>' + label + '</b><br>BESS: %{x:,} MWh<br>Curtailment: %{y:.2f}%<extra></extra>'
        ), secondary_y=False)

    # Difference line
    if len(pv_labels) == 2:
        df1 = pv_results[pv_labels[0]]['summary'].set_index('bess_size_mwh')
        df2 = pv_results[pv_labels[1]]['summary'].set_index('bess_size_mwh')
        common = df1.index.intersection(df2.index)
        diff = (df1.loc[common, 'curtailment_pct'] - df2.loc[common, 'curtailment_pct']).abs()

        fig.add_trace(go.Scatter(
            x=diff.index,
            y=diff.values,
            name='Difference',
            mode='lines+markers+text',
            line=dict(color='#66BB6A', width=2.5),
            marker=dict(size=9, symbol='diamond'),
            text=[f"{v:.2f}%" for v in diff.values],
            textposition='top center',
            textfont=dict(size=10, color='#66BB6A'),
            hovertemplate='<b>Difference</b><br>BESS: %{x:,} MWh<br>Δ: %{y:.2f}%<extra></extra>'
        ), secondary_y=True)

    fig.update_xaxes(
        title_text='<b>BESS Size (MWh)</b>',
        showgrid=True, gridcolor='#E0E0E0',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Curtailment (%)</b>',
        secondary_y=False, rangemode='tozero',
        showgrid=True, gridcolor='#E0E0E0',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Difference (%)</b>',
        secondary_y=True, rangemode='tozero',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )

    fig.update_layout(
        title=dict(text='<b>Curtailment % vs BESS Size</b>', x=0.5, xanchor='center', font=dict(size=TITLE_SIZE)),
        height=480,
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=FONT_FAMILY),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5,
            font=dict(size=LEGEND_SIZE), bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC', borderwidth=1
        )
    )
    return fig


def chart_baseline_without_bess(baseline_results: dict):
    """
    Baseline CF & operating hours WITHOUT BESS (slide 154 style).
    """
    labels  = list(baseline_results.keys())
    cf_vals = [baseline_results[k]['firm_cf_pct'] for k in labels]  # firm_cf_pct
    hr_vals = [baseline_results[k]['operating_hours'] for k in labels]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=labels,
        y=cf_vals,
        name='Capacity Factor',
        marker_color=[COLORS['pv_1000'], COLORS['pv_500']],
        text=[f"{v:.2f}%" for v in cf_vals],
        textposition='outside',
        textfont=dict(size=12),
        hovertemplate='<b>%{x}</b><br>CF: %{y:.2f}%<extra></extra>'
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=labels,
        y=hr_vals,
        name='Operating Hours',
        mode='lines+markers+text',
        line=dict(color='#64B5F6', width=3),
        marker=dict(size=12),
        text=[str(int(v)) for v in hr_vals],
        textposition='top center',
        textfont=dict(size=11, color='#1976D2'),
        hovertemplate='<b>%{x}</b><br>Hours: %{y:,}<extra></extra>'
    ), secondary_y=True)

    fig.update_yaxes(
        title_text='<b>Capacity Factor (%)</b>',
        secondary_y=False, range=[70, 85],
        showgrid=True, gridcolor='#E0E0E0',
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )
    fig.update_yaxes(
        title_text='<b>Operating Hours (Annual)</b>',
        secondary_y=True,
        title_font=dict(size=AXIS_TITLE_SIZE), tickfont=dict(size=AXIS_LABEL_SIZE)
    )

    fig.update_layout(
        title=dict(text='<b>Baseline Performance: Without BESS</b>', x=0.5, xanchor='center', font=dict(size=TITLE_SIZE)),
        height=420,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=FONT_FAMILY),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5,
            font=dict(size=LEGEND_SIZE), bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#CCCCCC', borderwidth=1
        )
    )
    return fig


def build_summary_table(pv_results: dict):
    """
    Build comparison table - shows only firm_cf_pct (labeled as 'CF (%)').
    """
    rows = []
    for pv_label, data in pv_results.items():
        for _, row in data['summary'].iterrows():
            rows.append({
                'PV Case':                pv_label,
                'BESS Size (MWh)':        int(row['bess_size_mwh']),
                'Capacity Factor (%)':    f"{row['firm_cf_pct']:.2f}",  # firm CF only
                'Operating Hours':        int(row['operating_hours']),
                'Days 24h Full':          int(row['days_full_24h']),
                'Curtailment (%)':        f"{row['curtailment_pct']:.2f}",
                'Total H2 (tonnes/yr)':   f"{row['total_h2_kg'] / 1000:.1f}",
                'Total Energy (GWh)':     f"{row['total_energy_mwh'] / 1000:.1f}",
            })
    return pd.DataFrame(rows)
