"""
FIRM POWER CHARTS v2.0
======================
Clean, professional charts matching presentation style
Fixed: overlapping labels, messy axes, illegible text
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Professional color palette - high contrast
COLORS = {
    'pv_1000':    '#1565C0',  # Dark blue (1000 MW)
    'pv_500':     '#42A5F5',  # Light blue (500 MW)
    'hydro':      '#FF6B35',  # Orange
    'pv':         '#4CAF50',  # Green
    'wind':       '#2196F3',  # Blue
    'bess_soc':   '#9C27B0',  # Purple
    'load':       '#FFD700',  # Gold
    'bars':       '#1976D2',  # Blue bars
    'line':       '#FF6F00',  # Orange line
}

FONT_FAMILY = 'Arial, sans-serif'
TITLE_SIZE = 18
AXIS_TITLE_SIZE = 14
AXIS_LABEL_SIZE = 12
LEGEND_SIZE = 12
DATA_LABEL_SIZE = 11


def chart_cf_vs_bess(pv_results: dict):
    """
    Chart 1: System Performance vs Battery Size
    Clean line chart with data labels, matching slide 155 style
    """
    fig = go.Figure()
    
    for label, data in pv_results.items():
        df = data['summary'].copy()
        df = df.sort_values('bess_size_mwh')
        
        # Determine color based on PV capacity
        if '1000' in label:
            color = COLORS['pv_1000']
            marker_symbol = 'circle'
        else:
            color = COLORS['pv_500']
            marker_symbol = 'diamond'
        
        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'],
            y=df['firm_cf_pct'],
            mode='lines+markers+text',
            name=label,
            line=dict(color=color, width=3),
            marker=dict(size=10, symbol=marker_symbol),
            text=[f"{val:.1f}%" for val in df['firm_cf_pct']],
            textposition='top center',
            textfont=dict(size=DATA_LABEL_SIZE, color=color, family=FONT_FAMILY),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'BESS: %{x:,.0f} MWh<br>' +
                         'Capacity Factor: %{y:.2f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(
            text='<b>System Performance vs Battery Size</b>',
            font=dict(size=TITLE_SIZE, family=FONT_FAMILY, color='#1976D2'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='<b>BESS Size (MWh)</b>',
            titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
            tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
            showgrid=True,
            gridcolor='#E0E0E0',
            zeroline=False
        ),
        yaxis=dict(
            title='<b>Capacity Factor (%)</b>',
            titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
            tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
            showgrid=True,
            gridcolor='#E0E0E0',
            zeroline=False,
            range=[80, 100]  # Fixed range for better visibility
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#CCCCCC',
            borderwidth=1,
            font=dict(size=LEGEND_SIZE, family=FONT_FAMILY)
        ),
        margin=dict(l=80, r=40, t=80, b=100)
    )
    
    return fig


def chart_days_vs_bess(pv_results: dict):
    """
    Chart 2: Full-Power Operation Days
    Dual-axis bar+line chart matching slide 157/159 style
    Fixed: no overlapping labels, clean spacing
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    for idx, (label, data) in enumerate(pv_results.items()):
        df = data['summary'].copy()
        df = df.sort_values('bess_size_mwh')
        
        # Determine styling
        if '1000' in label:
            bar_color = '#1565C0'  # Dark blue
            line_color = '#0D47A1'  # Darker blue
            offset = -0.2 if len(pv_results) > 1 else 0
        else:
            bar_color = '#42A5F5'  # Light blue
            line_color = '#1976D2'  # Medium blue
            offset = 0.2 if len(pv_results) > 1 else 0
        
        # Bars: Days with 24h full output
        fig.add_trace(go.Bar(
            x=df['bess_size_mwh'] + offset * 100,  # Offset bars slightly
            y=df['days_full_24h'],
            name=f'{label} - Days',
            marker_color=bar_color,
            text=[f"{int(val)}" for val in df['days_full_24h']],
            textposition='outside',
            textfont=dict(size=DATA_LABEL_SIZE, color=bar_color, family=FONT_FAMILY),
            width=150,  # Fixed bar width
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'BESS: %{x:,.0f} MWh<br>' +
                         'Days: %{y}<extra></extra>',
            showlegend=True
        ), secondary_y=False)
        
        # Lines: Operating hours
        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'],
            y=df['operating_hours'],
            name=f'{label} - Hours',
            mode='lines+markers+text',
            line=dict(color=line_color, width=3),
            marker=dict(size=8, symbol='circle'),
            text=[f"{int(val)}" for val in df['operating_hours']],
            textposition='top center',
            textfont=dict(size=DATA_LABEL_SIZE - 1, color=line_color, family=FONT_FAMILY),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'BESS: %{x:,.0f} MWh<br>' +
                         'Hours: %{y}<extra></extra>',
            showlegend=True
        ), secondary_y=True)
    
    # Update axes
    fig.update_xaxes(
        title='<b>BESS Size (MWh)</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        showgrid=True,
        gridcolor='#E0E0E0'
    )
    
    fig.update_yaxes(
        title='<b>Days with 24h Full Output</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY, color=COLORS['bars']),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        showgrid=False,
        secondary_y=False,
        range=[0, 365]
    )
    
    fig.update_yaxes(
        title='<b>Operating Hours</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY, color=COLORS['line']),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        showgrid=True,
        gridcolor='#E0E0E0',
        secondary_y=True,
        range=[7000, 9000]
    )
    
    fig.update_layout(
        title=dict(
            text='<b>Full-Power Operation Days</b>',
            font=dict(size=TITLE_SIZE, family=FONT_FAMILY, color='#1976D2'),
            x=0.5,
            xanchor='center'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        barmode='group',
        bargap=0.2,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#CCCCCC',
            borderwidth=1,
            font=dict(size=LEGEND_SIZE, family=FONT_FAMILY)
        ),
        margin=dict(l=80, r=80, t=80, b=120)
    )
    
    return fig


def chart_dispatch_profile(day_df, title_text, elec_mw):
    """
    Dispatch profile: stacked area + load line + BESS SOC
    Matching slides 152-153 style
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Stacked areas
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'],
        y=day_df['Hydro_MW'],
        name='Hydro',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(255, 107, 53, 0.7)',
        hovertemplate='Hour %{x}<br>Hydro: %{y:.2f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'],
        y=day_df['PV_MW'],
        name='PV',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(76, 175, 80, 0.7)',
        hovertemplate='Hour %{x}<br>PV: %{y:.2f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'],
        y=day_df['Wind_MW'],
        name='Wind',
        mode='lines',
        line=dict(width=0),
        stackgroup='one',
        fillcolor='rgba(33, 150, 243, 0.7)',
        hovertemplate='Hour %{x}<br>Wind: %{y:.2f} MW<extra></extra>'
    ), secondary_y=False)
    
    # Load target line
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'],
        y=[elec_mw] * len(day_df),
        name='Firm Power Target',
        mode='lines',
        line=dict(width=3, color='#FFD700', dash='dash'),
        hovertemplate='Target: %{y:.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    # BESS SOC
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'],
        y=day_df['BESS_SOC_%'],
        name='BESS SOC',
        mode='lines',
        line=dict(width=3, color='#9C27B0'),
        hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'
    ), secondary_y=True)
    
    fig.update_xaxes(
        title='<b>Hours</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        tickmode='linear',
        tick0=0,
        dtick=2,
        range=[0, 24],
        showgrid=True,
        gridcolor='#E0E0E0'
    )
    
    fig.update_yaxes(
        title='<b>Power (MW)</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        showgrid=True,
        gridcolor='#E0E0E0',
        secondary_y=False
    )
    
    fig.update_yaxes(
        title='<b>BESS SOC (%)</b>',
        titlefont=dict(size=AXIS_TITLE_SIZE, family=FONT_FAMILY, color='#9C27B0'),
        tickfont=dict(size=AXIS_LABEL_SIZE, family=FONT_FAMILY),
        range=[0, 120],
        showgrid=False,
        secondary_y=True
    )
    
    fig.update_layout(
        title=dict(
            text=f'<b>{title_text}</b>',
            font=dict(size=TITLE_SIZE, family=FONT_FAMILY, color='#1976D2'),
            x=0.5,
            xanchor='center'
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='#CCCCCC',
            borderwidth=1,
            font=dict(size=LEGEND_SIZE, family=FONT_FAMILY)
        ),
        margin=dict(l=80, r=80, t=80, b=100)
    )
    
    return fig


# Unused charts (kept for backward compatibility but not called)
def chart_curtailment_vs_bess(pv_results: dict):
    """Not used in v2.0"""
    pass

def chart_baseline_without_bess(baseline: dict):
    """Not used in v2.0"""
    pass


def build_summary_table(pv_results: dict):
    """Build comprehensive summary table with light background"""
    all_rows = []
    
    for pv_label, data in pv_results.items():
        df = data['summary'].copy()
        df['PV Case'] = pv_label
        df = df[[
            'PV Case', 'bess_size_mwh', 'firm_cf_pct', 'operating_hours',
            'days_full_24h', 'curtailment_pct', 'total_h2_kg', 'total_energy_mwh'
        ]]
        all_rows.append(df)
    
    combined = pd.concat(all_rows, ignore_index=True)
    combined.columns = [
        'PV Case', 'BESS Size (MWh)', 'Capacity Factor (%)', 'Operating Hours',
        'Days 24h Full', 'Curtailment (%)', 'Total H2 (tonnes/yr)', 'Total Energy (MWh/yr)'
    ]
    
    # Format numeric columns
    combined['Total H2 (tonnes/yr)'] = (combined['Total H2 (tonnes/yr)'] / 1000).round(1)
    combined['Total Energy (MWh/yr)'] = combined['Total Energy (MWh/yr)'].round(1)
    combined['Capacity Factor (%)'] = combined['Capacity Factor (%)'].round(2)
    combined['Curtailment (%)'] = combined['Curtailment (%)'].round(2)
    
    return combined
