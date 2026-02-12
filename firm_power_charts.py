"""
FIRM POWER CHARTS v2.2
======================
Simplified Plotly syntax - no titlefont/tickfont parameters
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

COLORS = {
    'pv_1000': '#1565C0', 'pv_500': '#42A5F5',
    'bars': '#1976D2', 'line': '#FF6F00',
}


def chart_cf_vs_bess(pv_results: dict):
    """Chart 1: System Performance vs Battery Size"""
    fig = go.Figure()
    
    for label, data in pv_results.items():
        df = data['summary'].copy().sort_values('bess_size_mwh')
        color = COLORS['pv_1000'] if '1000' in label else COLORS['pv_500']
        
        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'], y=df['firm_cf_pct'],
            mode='lines+markers+text', name=label,
            line={'color': color, 'width': 3},
            marker={'size': 10},
            text=[f"{val:.1f}%" for val in df['firm_cf_pct']],
            textposition='top center',
            hovertemplate='<b>%{fullData.name}</b><br>BESS: %{x:,.0f} MWh<br>CF: %{y:.2f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title_text='<b>System Performance vs Battery Size</b>',
        title_x=0.5,
        xaxis_title='<b>BESS Size (MWh)</b>',
        yaxis_title='<b>Capacity Factor (%)</b>',
        xaxis={'showgrid': True, 'gridcolor': '#E0E0E0'},
        yaxis={'showgrid': True, 'gridcolor': '#E0E0E0', 'range': [80, 100]},
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 40, 't': 80, 'b': 100}
    )
    return fig


def chart_days_vs_bess(pv_results: dict):
    """Chart 2: Full-Power Operation Days"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    for label, data in pv_results.items():
        df = data['summary'].copy().sort_values('bess_size_mwh')
        bar_color = '#1565C0' if '1000' in label else '#42A5F5'
        line_color = '#0D47A1' if '1000' in label else '#1976D2'
        offset = -0.2 if len(pv_results) > 1 and '1000' in label else (0.2 if len(pv_results) > 1 else 0)
        
        fig.add_trace(go.Bar(
            x=df['bess_size_mwh'] + offset * 100, y=df['days_full_24h'],
            name=f'{label} - Days', marker_color=bar_color,
            text=[f"{int(v)}" for v in df['days_full_24h']],
            textposition='outside', width=150,
            hovertemplate='<b>%{fullData.name}</b><br>BESS: %{x:,.0f} MWh<br>Days: %{y}<extra></extra>'
        ), secondary_y=False)
        
        fig.add_trace(go.Scatter(
            x=df['bess_size_mwh'], y=df['operating_hours'],
            name=f'{label} - Hours', mode='lines+markers+text',
            line={'color': line_color, 'width': 3}, marker={'size': 8},
            text=[f"{int(v)}" for v in df['operating_hours']],
            textposition='top center',
            hovertemplate='<b>%{fullData.name}</b><br>BESS: %{x:,.0f} MWh<br>Hours: %{y}<extra></extra>'
        ), secondary_y=True)
    
    fig.update_xaxes(title_text='<b>BESS Size (MWh)</b>', showgrid=True, gridcolor='#E0E0E0')
    fig.update_yaxes(title_text='<b>Days with 24h Full Output</b>', showgrid=False, range=[0, 365], secondary_y=False)
    fig.update_yaxes(title_text='<b>Operating Hours</b>', showgrid=True, gridcolor='#E0E0E0', range=[7000, 9000], secondary_y=True)
    
    fig.update_layout(
        title_text='<b>Full-Power Operation Days</b>', title_x=0.5,
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, barmode='group', bargap=0.2,
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.3, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 80, 't': 80, 'b': 120}
    )
    return fig


def chart_dispatch_profile(day_df, title_text, elec_mw):
    """Dispatch profile"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'], y=day_df['Hydro_MW'], name='Hydro',
        mode='lines', line={'width': 0}, stackgroup='one', fillcolor='rgba(255, 107, 53, 0.7)'
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'], y=day_df['PV_MW'], name='PV',
        mode='lines', line={'width': 0}, stackgroup='one', fillcolor='rgba(76, 175, 80, 0.7)'
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'], y=day_df['Wind_MW'], name='Wind',
        mode='lines', line={'width': 0}, stackgroup='one', fillcolor='rgba(33, 150, 243, 0.7)'
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'], y=[elec_mw] * len(day_df),
        name='Firm Power Target', mode='lines',
        line={'width': 3, 'color': '#FFD700', 'dash': 'dash'}
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=day_df['Hour_of_Day'], y=day_df['BESS_SOC_%'], name='BESS SOC',
        mode='lines', line={'width': 3, 'color': '#9C27B0'}
    ), secondary_y=True)
    
    fig.update_xaxes(title_text='<b>Hours</b>', tickmode='linear', tick0=0, dtick=2, range=[0, 24], showgrid=True, gridcolor='#E0E0E0')
    fig.update_yaxes(title_text='<b>Power (MW)</b>', showgrid=True, gridcolor='#E0E0E0', secondary_y=False)
    fig.update_yaxes(title_text='<b>BESS SOC (%)</b>', range=[0, 120], showgrid=False, secondary_y=True)
    
    fig.update_layout(
        title_text=f'<b>{title_text}</b>', title_x=0.5,
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 80, 't': 80, 'b': 100}
    )
    return fig


def chart_curtailment_vs_bess(pv_results: dict):
    pass

def chart_baseline_without_bess(baseline: dict):
    pass


def build_summary_table(pv_results: dict):
    all_rows = []
    for pv_label, data in pv_results.items():
        df = data['summary'].copy()
        df['PV Case'] = pv_label
        df = df[['PV Case', 'bess_size_mwh', 'firm_cf_pct', 'operating_hours',
                'days_full_24h', 'curtailment_pct', 'total_h2_kg', 'total_energy_mwh']]
        all_rows.append(df)
    
    combined = pd.concat(all_rows, ignore_index=True)
    combined.columns = ['PV Case', 'BESS Size (MWh)', 'Capacity Factor (%)', 'Operating Hours',
                       'Days 24h Full', 'Curtailment (%)', 'Total H2 (tonnes/yr)', 'Total Energy (MWh/yr)']
    
    combined['Total H2 (tonnes/yr)'] = (combined['Total H2 (tonnes/yr)'] / 1000).round(1)
    combined['Total Energy (MWh/yr)'] = combined['Total Energy (MWh/yr)'].round(1)
    combined['Capacity Factor (%)'] = combined['Capacity Factor (%)'].round(2)
    combined['Curtailment (%)'] = combined['Curtailment (%)'].round(2)
    
    return combined
