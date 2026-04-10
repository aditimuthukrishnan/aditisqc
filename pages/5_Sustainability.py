"""
Page: Sustainability Impact
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from theme import apply_theme, suggestion_card, section_divider, PARADIGM_COLORS

st.set_page_config(page_title="Sustainability", layout="wide")
apply_theme()

st.markdown('<div class="page-title">Sustainability Impact</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Environmental cost of defects and efficiency gains across paradigms</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Run the simulation from the home page first.")
    st.stop()

results = st.session_state['results']

section_divider()

# --- Key Environmental Metrics ---
st.markdown("##### Environmental Performance")

paradigms = ['3.0', '4.0', '5.0']
labels = ['Industry 3.0', 'Industry 4.0', 'Industry 5.0']

col1, col2, col3 = st.columns(3)

metrics_data = []
for p in paradigms:
    r = results[p]
    n = max(r.total_units, 1)
    metrics_data.append({
        'paradigm': f'Industry {p}',
        'co2_per_unit': r.total_co2_kg / n,
        'energy_per_unit': r.total_energy_kwh / n,
        'waste_total': r.material_waste_kg,
        'co2_saved': r.co2_saved_kg,
    })

df_env = pd.DataFrame(metrics_data)

with col1:
    fig = px.bar(df_env, x='paradigm', y='co2_per_unit',
                 color='paradigm', color_discrete_sequence=PARADIGM_COLORS,
                 labels={'paradigm': '', 'co2_per_unit': 'kg CO2'},
                 title='CO2 Emissions per Unit')
    fig.update_layout(height=350, showlegend=False, margin=dict(t=60, b=40),
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(text=[f'{v:.1f}' for v in df_env['co2_per_unit']], textposition='outside')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(df_env, x='paradigm', y='energy_per_unit',
                 color='paradigm', color_discrete_sequence=PARADIGM_COLORS,
                 labels={'paradigm': '', 'energy_per_unit': 'kWh'},
                 title='Energy per Unit')
    fig.update_layout(height=350, showlegend=False, margin=dict(t=60, b=40),
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(text=[f'{v:.1f}' for v in df_env['energy_per_unit']], textposition='outside')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col3:
    fig = px.bar(df_env, x='paradigm', y='waste_total',
                 color='paradigm', color_discrete_sequence=PARADIGM_COLORS,
                 labels={'paradigm': '', 'waste_total': 'kg'},
                 title='Total Material Waste')
    fig.update_layout(height=350, showlegend=False, margin=dict(t=60, b=40),
                      plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(text=[f'{v:.0f}' for v in df_env['waste_total']], textposition='outside')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Defective vs Non-Defective Environmental Cost ---
st.markdown("##### Environmental Cost of Defects")

df_50 = pd.DataFrame(results['5.0'].unit_records)
df_50['Status'] = df_50['is_defective'].map({True: 'Defective', False: 'Non-Defective'})

col1, col2 = st.columns(2)

with col1:
    env_cost = df_50.groupby('Status').agg(
        avg_co2=('co2_kg', 'mean'),
        avg_energy=('energy_kwh', 'mean'),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(name='CO2 (kg)', x=env_cost['Status'], y=env_cost['avg_co2'],
                         marker_color=['#06d6a0', '#ef476f']))
    fig.update_layout(
        title='Average CO2: Defective vs Non-Defective',
        height=350, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
        yaxis_title='kg CO2',
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Energy (kWh)', x=env_cost['Status'], y=env_cost['avg_energy'],
                         marker_color=['#06d6a0', '#ef476f']))
    fig.update_layout(
        title='Average Energy: Defective vs Non-Defective',
        height=350, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
        yaxis_title='kWh',
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Product Environmental Profile ---
st.markdown("##### Environmental Profile by Product")

prod_env = df_50.groupby('product_type').agg(
    avg_co2=('co2_kg', 'mean'),
    avg_energy=('energy_kwh', 'mean'),
    avg_cost=('total_cost', 'mean'),
    defect_rate=('is_defective', 'mean'),
).reset_index()
prod_env['defect_rate'] *= 100

fig = px.scatter(prod_env, x='avg_energy', y='avg_co2', size='defect_rate',
                 color='product_type', text='product_type',
                 labels={'avg_energy': 'Avg Energy (kWh)', 'avg_co2': 'Avg CO2 (kg)',
                         'defect_rate': 'Defect Rate (%)', 'product_type': 'Product'},
                 title='Energy vs CO2 by Product (bubble size = defect rate)',
                 color_discrete_sequence=['#118ab2', '#ffd166', '#ef476f'])
fig.update_traces(textposition='top center', marker=dict(sizemin=15))
fig.update_layout(
    height=400, margin=dict(t=60, b=40),
    plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
)
fig.update_xaxes(gridcolor='#e9ecef')
fig.update_yaxes(gridcolor='#e9ecef')
st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Industry 5.0 Sustainability Advantage ---
st.markdown("##### Industry 5.0 Sustainability Advantage")

r30 = results['3.0']
r50 = results['5.0']
n30 = max(r30.total_units, 1)
n50 = max(r50.total_units, 1)

co2_reduction = ((r30.total_co2_kg/n30 - r50.total_co2_kg/n50) / (r30.total_co2_kg/n30)) * 100
energy_reduction = ((r30.total_energy_kwh/n30 - r50.total_energy_kwh/n50) / (r30.total_energy_kwh/n30)) * 100
waste_reduction = ((r30.material_waste_kg - r50.material_waste_kg) / max(r30.material_waste_kg, 1)) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("CO2 Reduction", f"{co2_reduction:.1f}%")
col2.metric("Energy Reduction", f"{energy_reduction:.1f}%")
col3.metric("Waste Reduction", f"{waste_reduction:.0f}%")
col4.metric("CO2 Saved (5.0 only)", f"{r50.co2_saved_kg:.1f} kg")

st.markdown("")

suggestion_card(
    "Sustainability-weighted detection is the key differentiator",
    f"Industry 5.0's approach of prioritizing high-environmental-impact defects (like brazing leaks "
    f"with refrigerant GWP of 2088x CO2) directly prevented {r50.co2_saved_kg:.1f} kg of CO2-equivalent "
    f"emissions. Combined with earlier detection reducing rework energy, the total environmental "
    f"benefit represents a {co2_reduction:.1f}% reduction in per-unit carbon footprint compared to "
    f"traditional quality management.",
    level="info"
)
