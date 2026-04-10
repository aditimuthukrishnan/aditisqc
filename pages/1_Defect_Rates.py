"""
Page: Defect Rate Analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from theme import apply_theme, section_divider, PARADIGM_COLORS, PARADIGM_NAMES

st.set_page_config(page_title="Defect Rates", layout="wide")
apply_theme()

st.markdown('<div class="page-title">Defect Rate Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Defect distribution by stage, supplier, and product type</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Run the simulation from the home page first.")
    st.stop()

results = st.session_state['results']

# Build combined dataframe
all_records = []
for p in ['3.0', '4.0', '5.0']:
    for rec in results[p].unit_records:
        rec_copy = rec.copy()
        rec_copy['paradigm'] = f'Industry {p}'
        all_records.append(rec_copy)
df = pd.DataFrame(all_records)

# --- Overall Defect Rates ---
st.markdown("##### Overall Defect Rates")

col1, col2 = st.columns(2)

with col1:
    defect_rates = []
    for p in ['3.0', '4.0', '5.0']:
        r = results[p]
        n = max(r.total_units, 1)
        defect_rates.append({
            'Paradigm': f'Industry {p}',
            'Defect Rate (%)': r.defective_units / n * 100,
            'Escape Rate (%)': r.defects_escaped / max(r.defective_units, 1) * 100,
            'Detection Rate (%)': r.defects_detected / max(r.defective_units, 1) * 100,
        })

    df_rates = pd.DataFrame(defect_rates)

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Detected', x=df_rates['Paradigm'],
                         y=df_rates['Detection Rate (%)'],
                         marker_color='#06d6a0'))
    fig.add_trace(go.Bar(name='Escaped', x=df_rates['Paradigm'],
                         y=df_rates['Escape Rate (%)'],
                         marker_color='#ef476f'))
    fig.update_layout(
        barmode='stack', height=380,
        title='Defect Detection vs Escape',
        yaxis_title='% of Defective Units',
        legend=dict(orientation='h', y=1.12),
        margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Defect stage distribution
    defective_df = df[df['is_defective'] == True]
    if len(defective_df) > 0:
        stage_data = defective_df.groupby(['paradigm', 'defect_stage']).size().reset_index(name='count')
        fig = px.bar(stage_data, x='defect_stage', y='count', color='paradigm',
                     barmode='group', color_discrete_sequence=PARADIGM_COLORS,
                     labels={'defect_stage': 'Defect Origin Stage', 'count': 'Count', 'paradigm': ''},
                     title='Defect Origin by Manufacturing Stage')
        fig.update_layout(
            height=380, margin=dict(t=60, b=40),
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation='h', y=1.12),
        )
        fig.update_yaxes(gridcolor='#e9ecef')
        st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- By Supplier ---
st.markdown("##### Defect Rate by Supplier")

col1, col2 = st.columns(2)

with col1:
    sup_defect = df.groupby(['paradigm', 'supplier']).agg(
        total=('unit_id', 'count'),
        defective=('is_defective', 'sum')
    ).reset_index()
    sup_defect['rate'] = sup_defect['defective'] / sup_defect['total'] * 100

    fig = px.bar(sup_defect, x='supplier', y='rate', color='paradigm',
                 barmode='group', color_discrete_sequence=PARADIGM_COLORS,
                 labels={'supplier': 'Supplier', 'rate': 'Defect Rate (%)', 'paradigm': ''},
                 title='Defect Rate by Supplier')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Supplier cost vs defect scatter
    sup_cost = df[df['paradigm'] == 'Industry 5.0'].groupby('supplier').agg(
        avg_cost=('total_cost', 'mean'),
        defect_rate=('is_defective', 'mean'),
        avg_scqrs=('scqrs_score', 'mean'),
    ).reset_index()
    sup_cost['defect_rate'] *= 100

    fig = px.scatter(sup_cost, x='defect_rate', y='avg_cost', size='avg_scqrs',
                     color='supplier', text='supplier',
                     labels={'defect_rate': 'Defect Rate (%)', 'avg_cost': 'Avg Cost per Unit',
                             'avg_scqrs': 'SCQRS Score'},
                     title='Supplier: Cost vs Defect Rate (Industry 5.0)',
                     color_discrete_sequence=['#118ab2', '#ffd166', '#ef476f'])
    fig.update_traces(textposition='top center')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- By Product Type ---
st.markdown("##### Defect Rate by Product Type")

prod_defect = df.groupby(['paradigm', 'product_type']).agg(
    total=('unit_id', 'count'),
    defective=('is_defective', 'sum'),
    avg_cost=('total_cost', 'mean'),
    avg_co2=('co2_kg', 'mean'),
).reset_index()
prod_defect['rate'] = prod_defect['defective'] / prod_defect['total'] * 100

col1, col2 = st.columns(2)

with col1:
    fig = px.bar(prod_defect, x='product_type', y='rate', color='paradigm',
                 barmode='group', color_discrete_sequence=PARADIGM_COLORS,
                 labels={'product_type': 'Product Type', 'rate': 'Defect Rate (%)', 'paradigm': ''},
                 title='Defect Rate by Product Type')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # BOM complexity vs defect rate
    df_50 = df[df['paradigm'] == 'Industry 5.0']
    fig = px.scatter(df_50, x='bom_complexity', y='scqrs_score',
                     color='is_defective',
                     color_discrete_map={True: '#ef476f', False: '#06d6a0'},
                     labels={'bom_complexity': 'BOM Complexity', 'scqrs_score': 'SCQRS Score',
                             'is_defective': 'Defective'},
                     title='BOM Complexity vs SCQRS Score',
                     opacity=0.6)
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Detection Point Analysis ---
st.markdown("##### Where Are Defects Being Caught?")

for p in ['3.0', '4.0', '5.0']:
    df_p = pd.DataFrame(results[p].unit_records)
    detected = df_p[df_p['defect_detected'] == True]
    if len(detected) > 0:
        stage_counts = detected['detection_stage'].value_counts().reset_index()
        stage_counts.columns = ['Stage', 'Count']
        st.markdown(f"**Industry {p}**")
        fig = px.bar(stage_counts, x='Stage', y='Count',
                     color_discrete_sequence=[PARADIGM_COLORS[['3.0','4.0','5.0'].index(p)]],
                     labels={'Stage': 'Detection Point', 'Count': 'Units Caught'})
        fig.update_layout(
            height=250, margin=dict(t=20, b=30),
            plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
        )
        fig.update_yaxes(gridcolor='#e9ecef')
        st.plotly_chart(fig, use_container_width=True)
