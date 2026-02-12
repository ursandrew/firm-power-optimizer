"""
FIRM POWER CHARTS v3.1
======================
Fixed: Proper System Scaling Analysis logic + readable axis text
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

COLORS = {
    'pv_1000': '#1565C0', 'pv_500': '#42A5F5',
    'pv': '#000000', 'wind': '#1E90FF', 'hydro': '#FFD700', 'bess': '#10B981',
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
        title={'text': '<b>System Performance vs Battery Size</b>', 'font': {'size': 18, 'color': '#1976D2', 'family': 'Arial'}},
        title_x=0.5,
        xaxis={'title': {'text': '<b>BESS Size (MWh)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
               'showgrid': True, 'gridcolor': '#E0E0E0', 
               'tickfont': {'size': 12, 'color': '#000000', 'family': 'Arial'}},
        yaxis={'title': {'text': '<b>Capacity Factor (%)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
               'showgrid': True, 'gridcolor': '#E0E0E0', 'range': [80, 100],
               'tickfont': {'size': 12, 'color': '#000000', 'family': 'Arial'}},
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5,
                'font': {'size': 12, 'color': '#000000', 'family': 'Arial'}},
        margin={'l': 80, 'r': 40, 't': 80, 'b': 100}
    )
    return fig


def chart_system_scaling(pv_results: dict, elec_mw: float):
    """
    Chart 2: System Scaling Analysis (Slide 161 logic)
    
    Key insight: As electrolyzer size DECREASES (500→300 MW),
    plant components (PV, Wind, BESS) also DECREASE proportionally,
    while CF remains constant (~86%)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Get the best case (highest CF) for each PV scenario
    first_label = list(pv_results.keys())[0]
    df = pv_results[first_label]['summary'].copy()
    best_idx = df['firm_cf_pct'].idxmax()
    best_row = df.loc[best_idx]
    
    # Base system (500 MW electrolyzer case)
    base_pv = pv_results[first_label].get('pv_mw', 1000)
    base_wind = pv_results[first_label].get('wind_mw', 1104)
    base_bess = best_row['bess_size_mwh']
    base_hydro = pv_results[first_label].get('hydro_mw', 250)
    base_cf = best_row['firm_cf_pct']
    
    # Electrolyzer sizes (reducing from 500 to 300 MW)
    electrolyzer_sizes = [500, 450, 400, 350, 300]
    
    pv_capacities = []
    wind_capacities = []
    bess_capacities = []
    hydro_capacities = []
    cf_values = []
    
    for elec_size in electrolyzer_sizes:
        # Scale factor relative to base (500 MW)
        scale = elec_size / 500.0
        
        pv_capacities.append(base_pv * scale)
        wind_capacities.append(base_wind * scale)
        bess_capacities.append(base_bess * scale)
        hydro_capacities.append(base_hydro * scale)
        cf_values.append(base_cf)  # CF stays constant
    
    # Stacked bars
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=pv_capacities, name='PV',
        marker_color=COLORS['pv'], 
        text=[f"{int(v)}" for v in pv_capacities],
        textposition='inside', textfont={'size': 11, 'color': 'white', 'family': 'Arial'},
        hovertemplate='PV: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=wind_capacities, name='Wind',
        marker_color=COLORS['wind'],
        text=[f"{int(v)}" for v in wind_capacities],
        textposition='inside', textfont={'size': 11, 'color': 'white', 'family': 'Arial'},
        hovertemplate='Wind: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=bess_capacities, name='BESS',
        marker_color=COLORS['bess'],
        text=[f"{int(v)}" for v in bess_capacities],
        textposition='inside', textfont={'size': 11, 'color': 'white', 'family': 'Arial'},
        hovertemplate='BESS: %{y:,.0f} MWh<extra></extra>'
    ), secondary_y=False)
    
    fig.add_trace(go.Bar(
        x=electrolyzer_sizes, y=hydro_capacities, name='Hydro',
        marker_color=COLORS['hydro'],
        text=[f"{int(v)}" for v in hydro_capacities],
        textposition='inside', textfont={'size': 11, 'color': 'black', 'family': 'Arial'},
        hovertemplate='Hydro: %{y:,.0f} MW<extra></extra>'
    ), secondary_y=False)
    
    # CF line
    fig.add_trace(go.Scatter(
        x=electrolyzer_sizes, y=cf_values, name='CF',
        mode='lines+markers+text', line={'color': COLORS['cf_line'], 'width': 3},
        marker={'size': 10}, 
        text=[f"{v:.2f}" for v in cf_values],
        textposition='top center', textfont={'size': 10, 'color': COLORS['cf_line'], 'family': 'Arial'},
        hovertemplate='CF: %{y:.2f}%<extra></extra>'
    ), secondary_y=True)
    
    fig.update_xaxes(
        title={'text': '<b>Electrolyzer size (MW)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        showgrid=True, gridcolor='#E0E0E0',
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    fig.update_yaxes(
        title={'text': '<b>Total renewable capacity (PV + Wind + BESS)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        showgrid=True, gridcolor='#E0E0E0', secondary_y=False,
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    fig.update_yaxes(
        title={'text': '<b>Capacity Factor %</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        showgrid=False, range=[65, 100], secondary_y=True,
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    
    fig.update_layout(
        title={'text': '<b>System Scaling Analysis</b>', 'font': {'size': 18, 'color': '#1976D2', 'family': 'Arial'}},
        title_x=0.5,
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, barmode='stack',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.3, 'xanchor': 'center', 'x': 0.5,
                'font': {'size': 12, 'color': '#000000', 'family': 'Arial'}},
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
    
    fig.update_xaxes(
        title={'text': '<b>Hours</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        tickmode='linear', tick0=0, dtick=2, range=[0, 24],
        showgrid=True, gridcolor='#E0E0E0', 
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    fig.update_yaxes(
        title={'text': '<b>Power (MW)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        showgrid=True, gridcolor='#E0E0E0', secondary_y=False,
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    fig.update_yaxes(
        title={'text': '<b>BESS SOC (%)</b>', 'font': {'size': 14, 'color': '#000000', 'family': 'Arial'}},
        range=[0, 120], showgrid=False, secondary_y=True,
        tickfont={'size': 12, 'color': '#000000', 'family': 'Arial'}
    )
    
    fig.update_layout(
        title={'text': f'<b>{title_text}</b>', 'font': {'size': 18, 'color': '#1976D2', 'family': 'Arial'}},
        title_x=0.5,
        plot_bgcolor='white', paper_bgcolor='white',
        height=500, hovermode='x unified',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': -0.25, 'xanchor': 'center', 'x': 0.5,
                'font': {'size': 12, 'color': '#000000', 'family': 'Arial'}},
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
