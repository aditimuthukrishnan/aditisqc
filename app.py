"""
HVAC Supply Chain Quality Dashboard
Main entry point — run with: streamlit run app.py
"""

import streamlit as st
from engine import run_all_paradigms, DEFAULT_SUPPLIERS, DEFAULT_BOM
from theme import apply_theme, section_divider

st.set_page_config(
    page_title="SCQRS Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_theme()

# --- Sidebar: Simulation Controls ---
st.sidebar.markdown("### Configuration")

num_units = st.sidebar.slider("Units to simulate", 50, 1000, 300, step=50)

st.sidebar.markdown("##### Supplier Quality")
sq_a = st.sidebar.slider("Supplier A", 0.50, 1.00, 0.92, 0.01, key="sqa")
sq_b = st.sidebar.slider("Supplier B", 0.50, 1.00, 0.85, 0.01, key="sqb")
sq_c = st.sidebar.slider("Supplier C", 0.50, 1.00, 0.78, 0.01, key="sqc")

st.sidebar.markdown("##### Base Defect Rates")
split_d = st.sidebar.slider("Split AC", 0.01, 0.30, 0.08, 0.01, key="sd")
cass_d = st.sidebar.slider("Cassette AC", 0.01, 0.30, 0.12, 0.01, key="cd")
vrf_d = st.sidebar.slider("VRF System", 0.01, 0.30, 0.18, 0.01, key="vd")

suppliers = {
    'Supplier_A': {'quality_score': sq_a, 'material_cost': 8500, 'lead_time_mean': 30},
    'Supplier_B': {'quality_score': sq_b, 'material_cost': 7200, 'lead_time_mean': 25},
    'Supplier_C': {'quality_score': sq_c, 'material_cost': 6000, 'lead_time_mean': 20},
}

bom_profiles = {
    'Split_AC':    {'complexity': 0.4, 'components': 45,  'base_defect_prob': split_d},
    'Cassette_AC': {'complexity': 0.6, 'components': 68,  'base_defect_prob': cass_d},
    'VRF_System':  {'complexity': 0.9, 'components': 120, 'base_defect_prob': vrf_d},
}

if st.sidebar.button("Run Simulation", type="primary", use_container_width=True):
    with st.spinner("Simulating..."):
        st.session_state['results'] = run_all_paradigms(num_units, suppliers, bom_profiles)
        st.session_state['suppliers'] = suppliers
        st.session_state['bom_profiles'] = bom_profiles

# --- Main Content ---
st.markdown('<div class="page-title">Supply Chain Quality Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">HVAC manufacturing quality analysis across Industry 3.0, 4.0, and 5.0 paradigms</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Configure parameters in the sidebar and run the simulation to begin.")
    st.stop()

results = st.session_state['results']

# --- KPI Row ---
col1, col2, col3, col4 = st.columns(4)

r50 = results['5.0']
r30 = results['3.0']
n50 = max(r50.total_units, 1)
n30 = max(r30.total_units, 1)

escape_50 = r50.defects_escaped / max(r50.defective_units, 1) * 100
escape_30 = r30.defects_escaped / max(r30.defective_units, 1) * 100

with col1:
    st.metric("Defect Escape Rate", f"{escape_50:.1f}%",
              delta=f"{escape_50 - escape_30:.1f}% vs 3.0", delta_color="inverse")
with col2:
    cost_50 = r50.total_cost / n50
    cost_30 = r30.total_cost / n30
    st.metric("Cost per Unit", f"{cost_50:,.0f}",
              delta=f"{cost_50 - cost_30:,.0f} vs 3.0", delta_color="inverse")
with col3:
    co2_50 = r50.total_co2_kg / n50
    co2_30 = r30.total_co2_kg / n30
    st.metric("CO2 per Unit (kg)", f"{co2_50:.1f}",
              delta=f"{co2_50 - co2_30:.1f} vs 3.0", delta_color="inverse")
with col4:
    st.metric("Avg SCQRS", f"{r50.avg_scqrs:.1f} / 100")

section_divider()

# --- Quick Summary Table ---
import pandas as pd

summary_data = []
for p in ['3.0', '4.0', '5.0']:
    r = results[p]
    n = max(r.total_units, 1)
    summary_data.append({
        'Paradigm': f'Industry {p}',
        'Units': r.total_units,
        'Defective': r.defective_units,
        'Escaped': r.defects_escaped,
        'Reworked': r.units_reworked,
        'Scrapped': r.units_scrapped,
        'First Pass Yield': f"{r.first_pass_yield:.1%}",
        'Avg Lead Time (min)': f"{r.total_lead_time / n:.1f}",
        'Avg Cost': f"{r.total_cost / n:,.0f}",
        'CO2/Unit (kg)': f"{r.total_co2_kg / n:.1f}",
        'Material Waste (kg)': f"{r.material_waste_kg:.0f}",
    })

st.markdown("##### Paradigm Comparison")
st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

section_divider()

# --- Improvement Summary ---
st.markdown("##### Improvement over Industry 3.0 Baseline")

for paradigm in ['4.0', '5.0']:
    r = results[paradigm]
    n = max(r.total_units, 1)
    escape_imp = ((r30.defects_escaped - r.defects_escaped) / max(r30.defects_escaped, 1)) * 100
    cost_imp = ((r30.total_cost/n30 - r.total_cost/n) / (r30.total_cost/n30)) * 100
    co2_imp = ((r30.total_co2_kg/n30 - r.total_co2_kg/n) / (r30.total_co2_kg/n30)) * 100
    waste_imp = ((r30.material_waste_kg - r.material_waste_kg) / max(r30.material_waste_kg, 1)) * 100

    cols = st.columns(5)
    cols[0].markdown(f"**Industry {paradigm}**")
    cols[1].metric("Escape Rate", f"{escape_imp:+.0f}%")
    cols[2].metric("Cost", f"{cost_imp:+.1f}%")
    cols[3].metric("CO2", f"{co2_imp:+.1f}%")
    cols[4].metric("Waste", f"{waste_imp:+.0f}%")
