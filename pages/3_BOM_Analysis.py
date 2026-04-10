"""
Page: BOM Analysis & Suggestions
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from theme import apply_theme, suggestion_card, section_divider, PARADIGM_COLORS

st.set_page_config(page_title="BOM Analysis", layout="wide")
apply_theme()

st.markdown('<div class="page-title">BOM Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Bill of Materials impact on quality, cost, and sustainability</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Run the simulation from the home page first.")
    st.stop()

results = st.session_state['results']
df = pd.DataFrame(results['5.0'].unit_records)

section_divider()

# --- BOM Complexity Overview ---
st.markdown("##### Product Complexity Profile")

col1, col2 = st.columns(2)

with col1:
    prod_stats = df.groupby('product_type').agg(
        units=('unit_id', 'count'),
        defect_rate=('is_defective', 'mean'),
        avg_cost=('total_cost', 'mean'),
        avg_co2=('co2_kg', 'mean'),
        avg_scqrs=('scqrs_score', 'mean'),
        avg_complexity=('bom_complexity', 'mean'),
    ).reset_index()
    prod_stats['defect_rate'] *= 100

    fig = px.bar(prod_stats, x='product_type', y='defect_rate',
                 color='avg_complexity', color_continuous_scale='YlOrRd',
                 labels={'product_type': 'Product', 'defect_rate': 'Defect Rate (%)',
                         'avg_complexity': 'BOM Complexity'},
                 title='Defect Rate by Product Type')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(prod_stats, x='avg_complexity', y='defect_rate',
                     size='avg_cost', color='product_type',
                     text='product_type',
                     labels={'avg_complexity': 'BOM Complexity', 'defect_rate': 'Defect Rate (%)',
                             'avg_cost': 'Avg Cost'},
                     title='Complexity vs Defect Rate (bubble = cost)',
                     color_discrete_sequence=['#118ab2', '#ffd166', '#ef476f'])
    fig.update_traces(textposition='top center', marker=dict(sizemin=15))
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
    )
    fig.update_xaxes(gridcolor='#e9ecef')
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- BOM x Supplier Interaction ---
st.markdown("##### BOM-Supplier Quality Interaction")

col1, col2 = st.columns(2)

with col1:
    cross = df.groupby(['product_type', 'supplier']).agg(
        defect_rate=('is_defective', 'mean'),
        count=('unit_id', 'count'),
    ).reset_index()
    cross['defect_rate'] *= 100

    pivot = cross.pivot(index='product_type', columns='supplier', values='defect_rate')

    fig = px.imshow(pivot, text_auto='.1f', color_continuous_scale='RdYlGn_r',
                    labels={'color': 'Defect Rate (%)'},
                    title='Defect Rate: Product Type x Supplier')
    fig.update_layout(height=350, margin=dict(t=60, b=40))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    cross_cost = df.groupby(['product_type', 'supplier']).agg(
        avg_cost=('total_cost', 'mean'),
    ).reset_index()
    pivot_cost = cross_cost.pivot(index='product_type', columns='supplier', values='avg_cost')

    fig = px.imshow(pivot_cost, text_auto=',.0f', color_continuous_scale='Blues',
                    labels={'color': 'Avg Cost'},
                    title='Average Cost: Product Type x Supplier')
    fig.update_layout(height=350, margin=dict(t=60, b=40))
    st.plotly_chart(fig, use_container_width=True)

section_divider()

# --- BOM Suggestions ---
st.markdown("##### BOM Optimization Suggestions")

for _, row in prod_stats.iterrows():
    product = row['product_type']
    rate = row['defect_rate']
    complexity = row['avg_complexity']
    cost = row['avg_cost']

    if rate > 18:
        # Find worst supplier for this product
        prod_df = df[df['product_type'] == product]
        worst_sup = prod_df.groupby('supplier')['is_defective'].mean().idxmax()
        worst_rate = prod_df.groupby('supplier')['is_defective'].mean().max() * 100

        suggestion_card(
            f"{product}: High defect rate ({rate:.1f}%) — complexity {complexity:.1f}",
            f"This product's BOM complexity of {complexity:.1f} correlates with elevated defect rates. "
            f"The worst-performing supplier for this product is {worst_sup} ({worst_rate:.1f}% defect rate). "
            f"Consider: (1) reducing component count through design-for-manufacturing review, "
            f"(2) standardizing sub-assemblies to reduce variability, "
            f"(3) restricting this product to higher-quality suppliers only.",
            level="critical"
        )
    elif rate > 10:
        suggestion_card(
            f"{product}: Moderate defect rate ({rate:.1f}%)",
            f"BOM complexity of {complexity:.1f} is manageable but contributing to quality issues. "
            f"Review critical-to-quality components and consider incoming inspection "
            f"focus on the highest-risk sub-assemblies. Average cost per unit: {cost:,.0f}.",
            level="warning"
        )
    else:
        suggestion_card(
            f"{product}: Well-controlled ({rate:.1f}%)",
            f"Defect rate is within acceptable limits for complexity level {complexity:.1f}. "
            f"Current supplier-BOM combination is performing well. Document best practices "
            f"for application to higher-complexity products.",
            level="info"
        )

section_divider()

# --- Cost Impact of BOM Decisions ---
st.markdown("##### Cost Impact Analysis")

col1, col2 = st.columns(2)

with col1:
    # Cost breakdown by defective vs non-defective
    df['status'] = df['is_defective'].map({True: 'Defective', False: 'Non-Defective'})
    cost_by_status = df.groupby(['product_type', 'status'])['total_cost'].mean().reset_index()

    fig = px.bar(cost_by_status, x='product_type', y='total_cost', color='status',
                 barmode='group',
                 color_discrete_map={'Defective': '#ef476f', 'Non-Defective': '#06d6a0'},
                 labels={'product_type': 'Product', 'total_cost': 'Avg Cost', 'status': ''},
                 title='Cost: Defective vs Non-Defective Units')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # CO2 by product type
    co2_by_product = df.groupby(['product_type', 'status'])['co2_kg'].mean().reset_index()

    fig = px.bar(co2_by_product, x='product_type', y='co2_kg', color='status',
                 barmode='group',
                 color_discrete_map={'Defective': '#ef476f', 'Non-Defective': '#06d6a0'},
                 labels={'product_type': 'Product', 'co2_kg': 'Avg CO2 (kg)', 'status': ''},
                 title='Carbon Footprint: Defective vs Non-Defective')
    fig.update_layout(
        height=380, margin=dict(t=60, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=1.12),
    )
    fig.update_yaxes(gridcolor='#e9ecef')
    st.plotly_chart(fig, use_container_width=True)
