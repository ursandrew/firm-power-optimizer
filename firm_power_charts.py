"""
FIRM POWER CHARTS v3.0
======================
- Fixed: Dark text on all axes
- New: System Scaling Analysis chart (replaces Days chart)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

COLORS = {
    'pv_1000': '#1565C0', 'pv_500': '#42A5F5',
    'pv': '#1E3A8A', 'wind': '#1E90FF', 'hydro': '#FFD700', 'bess': '#10B981',
    'cf_line': '#FF6F00',
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
            textfont={'size': 11, 'color': color},
            hovertemplate='<b>%{fullData.name}</b><br>BESS: %{x:,.0f} MWh<br>CF: %{y:.2f}%<extra></extra>'
        ))
    
    fig.update_layout(
        title_text='<b>System Performance vs Battery Size</b>',
        title_x=0.5,
        title_font={'size': 18, 'color': '#1976D2'},
        xaxis_title='<b>BESS Size (MWh)</b>',
        yaxis_title='<b>Capacity Factor (%)</b>',
        xaxis={'showgrid': True, 'gridcolor': '#E0E0E0', 'tickfont': {'size': 12, 'color': '#000000'}},
        yaxis={'showgrid': True, 'gridcolor': '#E0E0E0', 'range': [80, 100], 'tickfont': {'size': 12, 'color': '#000000'}},
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 40, 't': 80, 'b': 100},
        font={'color': '#000000'}
    )
    return fig


def chart_system_scaling(pv_results: dict, elec_mw: float):
    """
    Chart 2: System Scaling Analysis (like slide 161)
    Shows how system components scale with different electrolyzer sizes
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Use the first PV case for scaling analysis
    first_label = list(pv_results.keys())[0]
    df = pv_results[first_label]['summary'].copy().sort_values('bess_size_mwh')
    
    # Get system sizing data
    pv_capacity = pv_results[first_label].get('pv_mw', 1000)
    wind_capacity = pv_results[first_label].get('wind_mw', 1104)
    hydro_capacity = pv_results[first_label].get('hydro_mw', 250)
    
    # Calculate "electrolyzer sizes" based on firm power capability
    # Scale down from the target (e.g., 500 MW) based on CF
    electrolyzer_sizes = []
    pv_scaled = []
    wind_scaled = []
    hydro_scaled = []
    bess_scaled = []
    cf_values = []
    
    for idx, row in df.iterrows():
        # Effective firm power = target * CF
        effective_mw = elec_mw * (row['firm_cf_pct'] / 100)
        electrolyzer_sizes.append(effective_mw)
        
        # Components stay fixed
        pv_scaled.append(pv_capacity)
        wind_scaled.append(wind_capacity)
        hydro_scaled.append(hydro_capacity)
        bess_scaled.append(row['bess_size_mwh'])
        cf_values.append(row['firm_cf_pct'])
    
    # Reverse for chart (largest electrolyzer first)
    electrolyzer_sizes = electrolyzer_sizes[::-1]
    pv_scaled = pv_scaled[::-1]
    wind_scaled = wind_scaled[::-1]
    hydro_scaled = hydro_scaled[::-1]
    bess_scaled = bess_scaled[::-1]
    cf_values = cf_values[::-1]
    
    # Bars: Component capacities
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=pv_scaled, name='PV',
        marker_color=COLORS['pv'], text=[f"{int(v)}" for v in pv_scaled],
        textposition='inside', textfont={'size': 11, 'color': 'white'},
        hovertemplate='PV: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=wind_scaled, name='Wind',
        marker_color=COLORS['wind'], text=[f"{int(v)}" for v in wind_scaled],
        textposition='inside', textfont={'size': 11, 'color': 'white'},
        hovertemplate='Wind: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=bess_scaled, name='BESS',
        marker_color=COLORS['bess'], text=[f"{int(v)}" for v in bess_scaled],
        textposition='inside', textfont={'size': 11, 'color': 'white'},
        hovertemplate='BESS: %{y:,.0f} MWh<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=hydro_scaled, name='Hydro',
        marker_color=COLORS['hydro'], text=[f"{int(v)}" for v in hydro_scaled],
        textposition='inside', textfont={'size': 11, 'color': 'black'},
        hovertemplate='Hydro: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    # Line: Capacity Factor
    fig.add_trace(go.Scatter(
        x=electrolyzer_sizes, y=cf_values, name='CF',
        mode='lines+markers+text', line={'color': COLORS['cf_line'], 'width': 3},
        marker={'size': 10}, text=[f"{v:.2f}" for v in cf_values],
        textposition='top center', textfont={'size': 10, 'color': COLORS['cf_line']},
        hovertemplate='CF: %{y:.2f}%<extra></extra>'
    ), secondary_y=True)
    
    fig.update_xaxes(title_text='<b>Electrolyzer Size (MW)</b>', showgrid=True, gridcolor='#E0E0E0',
                     tickfont={'size': 12, 'color': '#000000'})
    fig.update_yaxes(title_text='<b>Total Renewable Capacity (PV + Wind) BESS</b>', showgrid=True, gridcolor='#E0E0E0',
                     secondary_y=False, tickfont={'size': 12, 'color': '#000000'})
    fig.update_yaxes(title_text='<b>Capacity Factor %</b>', showgrid=False, range=[65, 100],
                     secondary_y=True, tickfont={'size': 12, 'color': '#000000'})
    
    fig.update_layout(
        title_text='<b>System Scaling Analysis</b>', title_x=0.5,
        title_font={'size': 18, 'color': '#1976D2'},
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, barmode='stack',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.3, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 80, 't': 80, 'b': 120},
        font={'color': '#000000'}
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
    
    fig.update_xaxes(title_text='<b>Hours</b>', tickmode='linear', tick0=0, dtick=2, range=[0, 24],
                     showgrid=True, gridcolor='#E0E0E0', tickfont={'size': 12, 'color': '#000000'})
    fig.update_yaxes(title_text='<b>Power (MW)</b>', showgrid=True, gridcolor='#E0E0E0', secondary_y=False,
                     tickfont={'size': 12, 'color': '#000000'})
    fig.update_yaxes(title_text='<b>BESS SOC (%)</b>', range=[0, 120], showgrid=False, secondary_y=True,
                     tickfont={'size': 12, 'color': '#000000'})
    
    fig.update_layout(
        title_text=f'<b>{title_text}</b>', title_x=0.5, title_font={'size': 18, 'color': '#1976D2'},
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5},
        margin={'l': 80, 'r': 80, 't': 80, 'b': 100},
        font={'color': '#000000'}
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
