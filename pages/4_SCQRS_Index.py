"""
Page: SCQRS Index Analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from theme import apply_theme, section_divider

st.set_page_config(page_title="SCQRS Index", layout="wide")
apply_theme()

st.markdown('<div class="page-title">SCQRS Index</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Supply Chain Quality Risk Score — predictive risk assessment</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Run the simulation from the home page first.")
    st.stop()

results = st.session_state['results']

section_divider()

# --- SCQRS Overview ---
st.markdown("##### Score Distribution")

col1, col2 = st.columns(2)

with col1:
    df_50 = pd.DataFrame(results['5.0'].unit_records)
    df_50['Status'] = df_50['is_defective'].map({True: 'Defective', False: 'Non-Defective'})

    fig = px.histogram(df_50, x='scqrs_score', color='Status', nbins=30,
                       barmode='overlay', opacity=0.7,
                       color_discrete_map={'Defective': '#ef476f', 'Non-Defective': '#06d6a0'},
                       labels={'scqrs_score': 'SCQRS Score', 'Status': ''},
                       title='SCQRS Distribution: Defective vs Non-Defective')
    fig.update_layout(
        height=400, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.box(df_50, x='Status', y='scqrs_score', color='Status',
                 color_discrete_map={'Defective': '#ef476f', 'Non-Defective': '#06d6a0'},
                 labels={'scqrs_score': 'SCQRS Score'},
                 title='SCQRS Score Comparison')
    fig.update_layout(
        height=400, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

# Key stats
avg_def = df_50[df_50['is_defective'] == True]['scqrs_score'].mean()
avg_good = df_50[df_50['is_defective'] == False]['scqrs_score'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Avg SCQRS (Non-Defective)", f"{avg_good:.1f}")
col2.metric("Avg SCQRS (Defective)", f"{avg_def:.1f}")
col3.metric("Separation Gap", f"{avg_def - avg_good:.1f} points")

section_divider()

# --- SCQRS Components ---
st.markdown("##### Score Breakdown by Factor")

col1, col2 = st.columns(2)

with col1:
    fig = px.scatter(df_50, x='supplier_quality', y='scqrs_score',
                     color='is_defective',
                     color_discrete_map={True: '#ef476f', False: '#06d6a0'},
                     labels={'supplier_quality': 'Supplier Quality Score',
                             'scqrs_score': 'SCQRS Score', 'is_defective': 'Defective'},
                     title='Supplier Quality vs SCQRS',
                     opacity=0.5)
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(df_50, x='bom_complexity', y='scqrs_score',
                     color='is_defective',
                     color_discrete_map={True: '#ef476f', False: '#06d6a0'},
                     labels={'bom_complexity': 'BOM Complexity',
                             'scqrs_score': 'SCQRS Score', 'is_defective': 'Defective'},
                     title='BOM Complexity vs SCQRS',
                     opacity=0.5)
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Correlation Matrix ---
st.markdown("##### Feature Correlations")

corr_cols = ['supplier_quality', 'bom_complexity', 'scqrs_score', 'total_cost', 'co2_kg', 'energy_kwh', 'lead_time']
df_corr = df_50[corr_cols].copy()
df_corr.columns = ['Supplier Quality', 'BOM Complexity', 'SCQRS', 'Cost', 'CO2', 'Energy', 'Lead Time']

fig = px.imshow(df_corr.corr(), text_auto='.2f', color_continuous_scale='RdBu_r',
                title='Correlation Matrix')
fig.update_layout(height=500, margin=dict(t=60, b=40))
st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- SCQRS by Supplier and Product ---
st.markdown("##### SCQRS Breakdown")

col1, col2 = st.columns(2)

with col1:
    sup_scqrs = df_50.groupby('supplier')['scqrs_score'].agg(['mean', 'std']).reset_index()
    sup_scqrs.columns = ['Supplier', 'Mean', 'Std']
    sup_scqrs = sup_scqrs.sort_values('Mean')

    fig = px.bar(sup_scqrs, x='Mean', y='Supplier', orientation='h',
                 error_x='Std', color='Mean', color_continuous_scale='RdYlGn_r',
                 labels={'Mean': 'Average SCQRS'},
                 title='SCQRS by Supplier')
    fig.update_layout(
        height=300, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    prod_scqrs = df_50.groupby('product_type')['scqrs_score'].agg(['mean', 'std']).reset_index()
    prod_scqrs.columns = ['Product', 'Mean', 'Std']
    prod_scqrs = prod_scqrs.sort_values('Mean')

    fig = px.bar(prod_scqrs, x='Mean', y='Product', orientation='h',
                 error_x='Std', color='Mean', color_continuous_scale='RdYlGn_r',
                 labels={'Mean': 'Average SCQRS'},
                 title='SCQRS by Product Type')
    fig.update_layout(
        height=300, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- Paradigm Comparison ---
st.markdown("##### SCQRS Across Paradigms")

all_scqrs = []
for p in ['3.0', '4.0', '5.0']:
    for rec in results[p].unit_records:
        all_scqrs.append({'Paradigm': f'Industry {p}', 'SCQRS': rec['scqrs_score']})

df_scqrs = pd.DataFrame(all_scqrs)
fig = px.violin(df_scqrs, x='Paradigm', y='SCQRS', color='Paradigm',
                color_discrete_sequence=['#ef476f', '#118ab2', '#06d6a0'],
                title='SCQRS Score Distribution by Paradigm',
                box=True, points='outliers')
fig.update_layout(
    height=400, margin=dict(t=60, b=40),
    plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
)
fig.update_yaxes(gridcolor='#e9ecef')
st.plotly_chart(fig, use_container_width=True)
