"""
============================================================================
HVAC Manufacturing Supply Chain Quality — Interactive Dashboard
============================================================================
Run with: streamlit run dashboard.py
============================================================================
"""

import streamlit as st
import simpy
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="HVAC Supply Chain Quality Simulator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA CLASSES (same as simulation)
# ============================================================================

@dataclass
class HVACUnit:
    unit_id: int
    product_type: str
    supplier: str
    bom_complexity: float
    supplier_quality: float
    base_defect_prob: float
    material_cost: float
    entry_time: float = 0.0
    exit_time: float = 0.0
    is_defective: bool = False
    defect_stage: str = ''
    defect_detected: bool = False
    detection_stage: str = ''
    reworked: bool = False
    scrapped: bool = False
    total_energy_kwh: float = 0.0
    total_co2_kg: float = 0.0
    total_cost: float = 0.0
    scqrs_score: float = 0.0
    features: Dict = field(default_factory=dict)


@dataclass
class SimulationResults:
    paradigm: str
    total_units: int = 0
    defective_units: int = 0
    defects_detected: int = 0
    defects_escaped: int = 0
    units_reworked: int = 0
    units_scrapped: int = 0
    total_lead_time: float = 0.0
    total_cost: float = 0.0
    total_energy_kwh: float = 0.0
    total_co2_kg: float = 0.0
    co2_saved_kg: float = 0.0
    material_waste_kg: float = 0.0
    first_pass_yield: float = 0.0
    avg_scqrs: float = 0.0
    unit_records: List = field(default_factory=list)


# ============================================================================
# SIMULATION ENGINE (streamlined for dashboard)
# ============================================================================

STAGES = {
    'cutting':  {'time_mean': 12, 'time_std': 2,  'defect_contrib': 0.10, 'energy_kwh': 3.5,  'co2_kg': 1.8},
    'brazing':  {'time_mean': 25, 'time_std': 5,  'defect_contrib': 0.35, 'energy_kwh': 8.2,  'co2_kg': 4.1},
    'assembly': {'time_mean': 35, 'time_std': 8,  'defect_contrib': 0.25, 'energy_kwh': 5.0,  'co2_kg': 2.5},
    'painting': {'time_mean': 20, 'time_std': 3,  'defect_contrib': 0.15, 'energy_kwh': 6.5,  'co2_kg': 3.8},
    'testing':  {'time_mean': 15, 'time_std': 2,  'defect_contrib': 0.15, 'energy_kwh': 2.0,  'co2_kg': 1.0},
}

SUSTAINABILITY_WEIGHTS = {
    'brazing_leak': 5.0,
    'assembly_defect': 2.0,
    'cutting_defect': 1.5,
    'painting_defect': 3.0,
    'testing_failure': 1.0,
}

REWORK_COST = 2500
SCRAP_COST = 12000
INSPECTION_COST = 150
ML_COST = 50
HUMAN_REVIEW_COST = 200


def calculate_scqrs(unit, paradigm='3.0'):
    supplier_risk = (1 - unit.supplier_quality) * 25
    bom_risk = unit.bom_complexity * 25
    process_variation = np.clip(np.random.normal(0.5, 0.15), 0, 1)
    process_risk = process_variation * 25
    defect_risk = unit.base_defect_prob * 25 / 0.18
    scqrs = supplier_risk + bom_risk + process_risk + defect_risk
    if paradigm == '5.0':
        scqrs *= (1.0 + unit.bom_complexity * 0.3)
    return np.clip(scqrs, 0, 100)


class DefectPredictor:
    def __init__(self, accuracy=0.88):
        self.accuracy = accuracy
    
    def predict(self, unit, stage):
        true_prob = (
            unit.base_defect_prob *
            (1 + (1 - unit.supplier_quality)) *
            (1 + unit.bom_complexity * 0.5) *
            STAGES[stage]['defect_contrib'] / 0.35
        )
        true_prob = np.clip(true_prob, 0, 0.95)
        predicted_prob = np.clip(true_prob + np.random.normal(0, 0.08), 0, 1)
        return predicted_prob, predicted_prob > 0.15


class HVACSimulation:
    def __init__(self, paradigm, num_units, suppliers, bom_profiles):
        self.paradigm = paradigm
        self.num_units = num_units
        self.suppliers = suppliers
        self.bom_profiles = bom_profiles
        self.env = simpy.Environment()
        self.results = SimulationResults(paradigm=paradigm)
        self.ml_predictor = DefectPredictor()
        
        self.cutting_machine = simpy.Resource(self.env, capacity=2)
        self.brazing_station = simpy.Resource(self.env, capacity=3)
        self.assembly_line = simpy.Resource(self.env, capacity=4)
        self.painting_booth = simpy.Resource(self.env, capacity=2)
        self.testing_station = simpy.Resource(self.env, capacity=2)
        self.inspection_station = simpy.Resource(self.env, capacity=2)
        self.rework_station = simpy.Resource(self.env, capacity=1)
        
        np.random.seed(42 + hash(paradigm) % 1000)
    
    def generate_unit(self, unit_id):
        product_type = np.random.choice(list(self.bom_profiles.keys()))
        bom = self.bom_profiles[product_type]
        supplier_name = np.random.choice(list(self.suppliers.keys()))
        supplier = self.suppliers[supplier_name]
        
        return HVACUnit(
            unit_id=unit_id, product_type=product_type, supplier=supplier_name,
            bom_complexity=bom['complexity'], supplier_quality=supplier['quality_score'],
            base_defect_prob=bom['base_defect_prob'], material_cost=supplier['material_cost'],
            features={'supplier_quality': supplier['quality_score'], 'bom_complexity': bom['complexity'],
                     'num_components': bom['components'], 'material_cost': supplier['material_cost']}
        )
    
    def determine_defect(self, unit):
        prob = unit.base_defect_prob * (2 - unit.supplier_quality) * (1 + unit.bom_complexity * 0.3)
        prob = np.clip(prob, 0, 0.5)
        is_defective = np.random.random() < prob
        if is_defective:
            stage_probs = np.array([STAGES[s]['defect_contrib'] for s in STAGES])
            stage_probs /= stage_probs.sum()
            return True, np.random.choice(list(STAGES.keys()), p=stage_probs)
        return False, ''
    
    def process_stage(self, unit, stage_name, resource):
        stage = STAGES[stage_name]
        with resource.request() as req:
            yield req
            yield self.env.timeout(max(1, np.random.normal(stage['time_mean'], stage['time_std'])))
            unit.total_energy_kwh += stage['energy_kwh']
            unit.total_co2_kg += stage['co2_kg']
    
    def industry_30(self, unit):
        unit.entry_time = self.env.now
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        unit.scqrs_score = calculate_scqrs(unit, '3.0')
        
        yield from self.process_stage(unit, 'cutting', self.cutting_machine)
        yield from self.process_stage(unit, 'brazing', self.brazing_station)
        yield from self.process_stage(unit, 'assembly', self.assembly_line)
        yield from self.process_stage(unit, 'painting', self.painting_booth)
        yield from self.process_stage(unit, 'testing', self.testing_station)
        
        with self.inspection_station.request() as req:
            yield req
            yield self.env.timeout(max(1, np.random.normal(10, 2)))
            unit.total_cost += INSPECTION_COST
            if unit.is_defective:
                if np.random.random() < 0.60:
                    unit.defect_detected = True
                    unit.detection_stage = 'final_inspection'
                    if np.random.random() < 0.7:
                        unit.reworked = True
                        with self.rework_station.request() as rr:
                            yield rr
                            yield self.env.timeout(max(1, np.random.normal(45, 10)))
                        unit.total_cost += REWORK_COST
                        unit.total_energy_kwh += 15
                        unit.total_co2_kg += 7.5
                    else:
                        unit.scrapped = True
                        unit.total_cost += SCRAP_COST
                        self.results.material_waste_kg += 25
                else:
                    self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record(unit)
    
    def industry_40(self, unit):
        unit.entry_time = self.env.now
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        unit.scqrs_score = calculate_scqrs(unit, '4.0')
        
        stages = [('cutting', self.cutting_machine), ('brazing', self.brazing_station),
                  ('assembly', self.assembly_line), ('painting', self.painting_booth),
                  ('testing', self.testing_station)]
        
        for sname, res in stages:
            yield from self.process_stage(unit, sname, res)
            pred_prob, flagged = self.ml_predictor.predict(unit, sname)
            unit.total_cost += ML_COST / 5
            
            if flagged and unit.is_defective and sname == unit.defect_stage:
                unit.defect_detected = True
                unit.detection_stage = sname
                if np.random.random() < 0.85:
                    unit.reworked = True
                    with self.rework_station.request() as rr:
                        yield rr
                        yield self.env.timeout(max(1, np.random.normal(20, 5)))
                    unit.total_cost += REWORK_COST * 0.6
                    unit.total_energy_kwh += 8
                    unit.total_co2_kg += 4
                else:
                    unit.scrapped = True
                    unit.total_cost += SCRAP_COST * 0.5
                    self.results.material_waste_kg += 12
                break
            elif flagged and not unit.is_defective:
                yield self.env.timeout(5)
        
        if unit.is_defective and not unit.defect_detected:
            if np.random.random() < 0.75:
                unit.defect_detected = True
                unit.detection_stage = 'final_auto'
                unit.reworked = True
                unit.total_cost += REWORK_COST * 0.8
                unit.total_energy_kwh += 12
                unit.total_co2_kg += 6
            else:
                self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record(unit)
    
    def industry_50(self, unit):
        unit.entry_time = self.env.now
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        unit.scqrs_score = calculate_scqrs(unit, '5.0')
        
        stages = [('cutting', self.cutting_machine), ('brazing', self.brazing_station),
                  ('assembly', self.assembly_line), ('painting', self.painting_booth),
                  ('testing', self.testing_station)]
        
        for sname, res in stages:
            yield from self.process_stage(unit, sname, res)
            pred_prob, _ = self.ml_predictor.predict(unit, sname)
            unit.total_cost += ML_COST / 5
            
            sw = SUSTAINABILITY_WEIGHTS.get(f'{sname}_{"leak" if sname == "brazing" else "defect"}', 1.0)
            flagged_50 = pred_prob > (0.15 / sw)
            
            if flagged_50:
                unit.total_cost += HUMAN_REVIEW_COST
                yield self.env.timeout(max(1, np.random.normal(8, 2)))
                
                if unit.is_defective and sname == unit.defect_stage:
                    if np.random.random() < 0.95:
                        unit.defect_detected = True
                        unit.detection_stage = sname
                        unit.reworked = True
                        with self.rework_station.request() as rr:
                            yield rr
                            yield self.env.timeout(max(1, np.random.normal(20, 5)))
                        unit.total_cost += REWORK_COST * 0.5
                        unit.total_energy_kwh += 5
                        unit.total_co2_kg += 2.5
                        self.results.co2_saved_kg += sw * 2
                        break
        
        if unit.is_defective and not unit.defect_detected:
            if np.random.random() < 0.88:
                unit.defect_detected = True
                unit.detection_stage = 'final_collab'
                unit.reworked = True
                unit.total_cost += REWORK_COST * 0.7
                unit.total_energy_kwh += 10
                unit.total_co2_kg += 5
            else:
                self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record(unit)
    
    def _record(self, unit):
        self.results.total_units += 1
        self.results.total_lead_time += (unit.exit_time - unit.entry_time)
        self.results.total_cost += unit.total_cost
        self.results.total_energy_kwh += unit.total_energy_kwh
        self.results.total_co2_kg += unit.total_co2_kg
        if unit.is_defective: self.results.defective_units += 1
        if unit.defect_detected: self.results.defects_detected += 1
        if unit.reworked: self.results.units_reworked += 1
        if unit.scrapped: self.results.units_scrapped += 1
        
        self.results.unit_records.append({
            'unit_id': unit.unit_id, 'product_type': unit.product_type,
            'supplier': unit.supplier, 'bom_complexity': unit.bom_complexity,
            'supplier_quality': unit.supplier_quality, 'is_defective': unit.is_defective,
            'defect_stage': unit.defect_stage, 'defect_detected': unit.defect_detected,
            'detection_stage': unit.detection_stage, 'reworked': unit.reworked,
            'scrapped': unit.scrapped, 'lead_time': unit.exit_time - unit.entry_time,
            'total_cost': unit.total_cost, 'energy_kwh': unit.total_energy_kwh,
            'co2_kg': unit.total_co2_kg, 'scqrs_score': unit.scqrs_score,
        })
    
    def unit_gen(self):
        pmap = {'3.0': self.industry_30, '4.0': self.industry_40, '5.0': self.industry_50}
        for i in range(self.num_units):
            self.env.process(pmap[self.paradigm](self.generate_unit(i)))
            yield self.env.timeout(np.random.uniform(5, 15))
    
    def run(self):
        self.env.process(self.unit_gen())
        self.env.run(until=50000)
        n = max(self.results.total_units, 1)
        self.results.first_pass_yield = 1 - (self.results.defective_units / n)
        self.results.avg_scqrs = np.mean([r['scqrs_score'] for r in self.results.unit_records]) if self.results.unit_records else 0
        return self.results


# ============================================================================
# STREAMLIT DASHBOARD
# ============================================================================

def main():
    # --- Header ---
    st.markdown('<div class="main-header">🏭 HVAC Supply Chain Quality Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comparing Industry 3.0 → 4.0 → 5.0 Quality Paradigms | Novel SCQRS Index</div>', unsafe_allow_html=True)
    
    # --- Sidebar Controls ---
    st.sidebar.header("⚙️ Simulation Parameters")
    
    num_units = st.sidebar.slider("Number of HVAC Units", 50, 1000, 300, step=50,
                                   help="More units = more accurate but slower")
    
    st.sidebar.subheader("🏢 Supplier Configuration")
    
    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        sq_a = st.slider("Supplier A Quality", 0.50, 1.00, 0.92, 0.01)
        sq_b = st.slider("Supplier B Quality", 0.50, 1.00, 0.85, 0.01)
        sq_c = st.slider("Supplier C Quality", 0.50, 1.00, 0.78, 0.01)
    with col_s2:
        sc_a = st.number_input("Cost A (₹)", 5000, 15000, 8500, 500)
        sc_b = st.number_input("Cost B (₹)", 5000, 15000, 7200, 500)
        sc_c = st.number_input("Cost C (₹)", 5000, 15000, 6000, 500)
    
    suppliers = {
        'Supplier_A': {'quality_score': sq_a, 'material_cost': sc_a, 'lead_time_mean': 30},
        'Supplier_B': {'quality_score': sq_b, 'material_cost': sc_b, 'lead_time_mean': 25},
        'Supplier_C': {'quality_score': sq_c, 'material_cost': sc_c, 'lead_time_mean': 20},
    }
    
    st.sidebar.subheader("📦 BOM Configuration")
    split_defect = st.sidebar.slider("Split AC Defect Rate", 0.01, 0.30, 0.08, 0.01)
    cassette_defect = st.sidebar.slider("Cassette AC Defect Rate", 0.01, 0.30, 0.12, 0.01)
    vrf_defect = st.sidebar.slider("VRF System Defect Rate", 0.01, 0.30, 0.18, 0.01)
    
    bom_profiles = {
        'Split_AC':    {'complexity': 0.4, 'components': 45,  'base_defect_prob': split_defect},
        'Cassette_AC': {'complexity': 0.6, 'components': 68,  'base_defect_prob': cassette_defect},
        'VRF_System':  {'complexity': 0.9, 'components': 120, 'base_defect_prob': vrf_defect},
    }
    
    # --- Run Simulation ---
    run_button = st.sidebar.button("🚀 Run Simulation", type="primary", use_container_width=True)
    
    if run_button:
        results = {}
        progress = st.progress(0, text="Starting simulation...")
        
        for i, paradigm in enumerate(['3.0', '4.0', '5.0']):
            progress.progress((i) / 3, text=f"Running Industry {paradigm} simulation...")
            sim = HVACSimulation(paradigm, num_units, suppliers, bom_profiles)
            results[paradigm] = sim.run()
        
        progress.progress(1.0, text="✅ Simulation complete!")
        
        # Store in session state
        st.session_state['results'] = results
        st.session_state['suppliers'] = suppliers
        st.session_state['bom_profiles'] = bom_profiles
    
    # --- Display Results ---
    if 'results' not in st.session_state:
        st.info("👈 Configure parameters in the sidebar and click **Run Simulation** to begin.")
        
        # Show framework explanation
        with st.expander("📖 About This Simulation", expanded=True):
            st.markdown("""
            ### What This Simulates
            
            This tool simulates an **HVAC manufacturing supply chain** through 5 production stages 
            (Cutting → Brazing → Assembly → Painting → Testing) under three quality management paradigms:
            
            | Paradigm | Quality Approach | Detection Method |
            |----------|-----------------|-----------------|
            | **Industry 3.0** | SPC/SQC | Final inspection only (60% catch rate) |
            | **Industry 4.0** | ML-Automated | Mid-process ML prediction |
            | **Industry 5.0** | Human-AI + Sustainable | ML + Human review + Sustainability scoring |
            
            ### Novel Contribution: SCQRS Index
            
            The **Supply Chain Quality Risk Score (SCQRS)** is a composite index combining:
            - Supplier quality reliability (0-25 pts)
            - BOM complexity risk (0-25 pts)  
            - Process variation risk (0-25 pts)
            - Base defect probability (0-25 pts)
            - Sustainability weighting (Industry 5.0 only)
            """)
        return
    
    results = st.session_state['results']
    
    # ===== KEY METRICS ROW =====
    st.markdown("---")
    st.subheader("📊 Key Performance Indicators")
    
    cols = st.columns(4)
    
    for i, (paradigm, color) in enumerate([('3.0', '🔴'), ('4.0', '🔵'), ('5.0', '🟢')]):
        r = results[paradigm]
        n = max(r.total_units, 1)
        with cols[i]:
            st.markdown(f"### {color} Industry {paradigm}")
            escape_rate = r.defects_escaped / max(r.defective_units, 1) * 100
            st.metric("Defect Escape Rate", f"{escape_rate:.1f}%",
                      delta=f"{escape_rate - (results['3.0'].defects_escaped / max(results['3.0'].defective_units, 1) * 100):.1f}%" if paradigm != '3.0' else None,
                      delta_color="inverse")
            st.metric("Avg Cost/Unit", f"₹{r.total_cost/n:,.0f}",
                      delta=f"₹{(r.total_cost/n - results['3.0'].total_cost/max(results['3.0'].total_units,1)):,.0f}" if paradigm != '3.0' else None,
                      delta_color="inverse")
            st.metric("CO₂/Unit", f"{r.total_co2_kg/n:.1f} kg",
                      delta=f"{(r.total_co2_kg/n - results['3.0'].total_co2_kg/max(results['3.0'].total_units,1)):.1f} kg" if paradigm != '3.0' else None,
                      delta_color="inverse")
            st.metric("SCQRS Score", f"{r.avg_scqrs:.1f}/100")
    
    # Summary column
    with cols[3]:
        st.markdown("### 📈 Best Improvement")
        r30 = results['3.0']
        r50 = results['5.0']
        n30 = max(r30.total_units, 1)
        n50 = max(r50.total_units, 1)
        
        escape_imp = ((r30.defects_escaped - r50.defects_escaped) / max(r30.defects_escaped, 1)) * 100
        cost_imp = ((r30.total_cost/n30 - r50.total_cost/n50) / (r30.total_cost/n30)) * 100
        co2_imp = ((r30.total_co2_kg/n30 - r50.total_co2_kg/n50) / (r30.total_co2_kg/n30)) * 100
        
        st.metric("Escape Rate Reduction", f"{escape_imp:.0f}%", "Industry 5.0 vs 3.0")
        st.metric("Cost Reduction", f"{cost_imp:.1f}%", "Industry 5.0 vs 3.0")
        st.metric("CO₂ Reduction", f"{co2_imp:.1f}%", "Industry 5.0 vs 3.0")
    
    # ===== TABS FOR DETAILED ANALYSIS =====
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Comparative Charts", "🎯 SCQRS Analysis", "🏭 Supply Chain View",
        "🌱 Sustainability Impact", "📋 Raw Data"
    ])
    
    # ----- TAB 1: COMPARATIVE CHARTS -----
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Defect Escape Rate comparison
            paradigms = ['Industry 3.0', 'Industry 4.0', 'Industry 5.0']
            escape_rates = [results[p.split()[-1]].defects_escaped / max(results[p.split()[-1]].defective_units, 1) * 100 for p in paradigms]
            
            fig = px.bar(x=paradigms, y=escape_rates,
                        color=paradigms, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        labels={'x': 'Paradigm', 'y': 'Escape Rate (%)'},
                        title='🚨 Defect Escape Rate by Paradigm')
            fig.update_layout(showlegend=False, height=400)
            fig.update_traces(text=[f'{v:.1f}%' for v in escape_rates], textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Cost comparison
            avg_costs = [results[p.split()[-1]].total_cost / max(results[p.split()[-1]].total_units, 1) for p in paradigms]
            
            fig = px.bar(x=paradigms, y=avg_costs,
                        color=paradigms, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        labels={'x': 'Paradigm', 'y': 'Cost (₹)'},
                        title='💰 Average Cost per Unit')
            fig.update_layout(showlegend=False, height=400)
            fig.update_traces(text=[f'₹{v:,.0f}' for v in avg_costs], textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Lead time comparison
            avg_leads = [results[p.split()[-1]].total_lead_time / max(results[p.split()[-1]].total_units, 1) for p in paradigms]
            
            fig = px.bar(x=paradigms, y=avg_leads,
                        color=paradigms, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        labels={'x': 'Paradigm', 'y': 'Lead Time (min)'},
                        title='⏱️ Average Lead Time per Unit')
            fig.update_layout(showlegend=False, height=400)
            fig.update_traces(text=[f'{v:.1f} min' for v in avg_leads], textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            # Radar chart — multi-dimensional comparison
            categories = ['First Pass Yield', 'Detection Rate', 'Low Cost', 'Low CO₂', 'Low Waste']
            
            fig = go.Figure()
            colors_r = ['#e74c3c', '#3498db', '#2ecc71']
            
            for idx, p in enumerate(['3.0', '4.0', '5.0']):
                r = results[p]
                n = max(r.total_units, 1)
                det_rate = r.defects_detected / max(r.defective_units, 1)
                max_cost = max(results[pp].total_cost / max(results[pp].total_units, 1) for pp in ['3.0', '4.0', '5.0'])
                max_co2 = max(results[pp].total_co2_kg / max(results[pp].total_units, 1) for pp in ['3.0', '4.0', '5.0'])
                max_waste = max(results[pp].material_waste_kg for pp in ['3.0', '4.0', '5.0'])
                
                values = [
                    r.first_pass_yield * 100,
                    det_rate * 100,
                    (1 - r.total_cost / n / max_cost) * 100 if max_cost > 0 else 50,
                    (1 - r.total_co2_kg / n / max_co2) * 100 if max_co2 > 0 else 50,
                    (1 - r.material_waste_kg / max_waste) * 100 if max_waste > 0 else 50,
                ]
                values.append(values[0])  # Close the polygon
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories + [categories[0]],
                    fill='toself',
                    name=f'Industry {p}',
                    line_color=colors_r[idx],
                    opacity=0.6
                ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title='🎯 Multi-Dimensional Performance Radar',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # ----- TAB 2: SCQRS ANALYSIS -----
    with tab2:
        st.subheader("🎯 Supply Chain Quality Risk Score (SCQRS) — Novel Contribution")
        st.markdown("The SCQRS integrates supplier quality, BOM complexity, process variation, and sustainability impact into a single predictive risk score.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # SCQRS distribution by paradigm
            all_data = []
            for p in ['3.0', '4.0', '5.0']:
                for rec in results[p].unit_records:
                    all_data.append({'paradigm': f'Industry {p}', 'scqrs': rec['scqrs_score'],
                                   'is_defective': rec['is_defective']})
            df_all = pd.DataFrame(all_data)
            
            fig = px.histogram(df_all, x='scqrs', color='paradigm',
                             color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                             barmode='overlay', opacity=0.6,
                             title='SCQRS Distribution Across Paradigms',
                             labels={'scqrs': 'SCQRS Score', 'paradigm': 'Paradigm'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # SCQRS: Defective vs Non-defective (Industry 5.0)
            df_50 = pd.DataFrame(results['5.0'].unit_records)
            df_50['Status'] = df_50['is_defective'].map({True: 'Defective', False: 'Non-Defective'})
            
            fig = px.box(df_50, x='Status', y='scqrs_score', color='Status',
                        color_discrete_sequence=['#2ecc71', '#e74c3c'],
                        title='SCQRS: Defective vs Non-Defective (Industry 5.0)',
                        labels={'scqrs_score': 'SCQRS Score'})
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            # SCQRS by Supplier
            df_50_sup = df_50.groupby('supplier')['scqrs_score'].agg(['mean', 'std']).reset_index()
            df_50_sup.columns = ['Supplier', 'Mean SCQRS', 'Std SCQRS']
            
            fig = px.bar(df_50_sup, x='Supplier', y='Mean SCQRS', error_y='Std SCQRS',
                        color='Mean SCQRS', color_continuous_scale='RdYlGn_r',
                        title='Average SCQRS by Supplier')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            # SCQRS by Product Type
            df_50_prod = df_50.groupby('product_type')['scqrs_score'].agg(['mean', 'std']).reset_index()
            df_50_prod.columns = ['Product', 'Mean SCQRS', 'Std SCQRS']
            
            fig = px.bar(df_50_prod, x='Product', y='Mean SCQRS', error_y='Std SCQRS',
                        color='Mean SCQRS', color_continuous_scale='RdYlGn_r',
                        title='Average SCQRS by Product Type (BOM Complexity)')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # SCQRS Correlation Heatmap
        st.subheader("SCQRS Feature Correlations")
        df_corr = df_50[['supplier_quality', 'bom_complexity', 'scqrs_score', 'total_cost', 'co2_kg', 'energy_kwh']].copy()
        df_corr.columns = ['Supplier Quality', 'BOM Complexity', 'SCQRS Score', 'Total Cost', 'CO₂ (kg)', 'Energy (kWh)']
        corr = df_corr.corr()
        
        fig = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r',
                       title='Correlation Matrix: SCQRS and Key Variables')
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # ----- TAB 3: SUPPLY CHAIN VIEW -----
    with tab3:
        st.subheader("🏭 Supply Chain Quality Flow")
        
        # Detection stage distribution
        col1, col2 = st.columns(2)
        
        with col1:
            for p in ['3.0', '4.0', '5.0']:
                df_p = pd.DataFrame(results[p].unit_records)
                detected = df_p[df_p['defect_detected'] == True]
                if len(detected) > 0:
                    stage_counts = detected['detection_stage'].value_counts()
                    fig = px.pie(values=stage_counts.values, names=stage_counts.index,
                               title=f'Industry {p}: Where Defects Are Caught',
                               color_discrete_sequence=px.colors.qualitative.Set3)
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Defect by supplier across paradigms
            supplier_defects = []
            for p in ['3.0', '4.0', '5.0']:
                df_p = pd.DataFrame(results[p].unit_records)
                for sup in df_p['supplier'].unique():
                    sup_data = df_p[df_p['supplier'] == sup]
                    defect_rate = sup_data['is_defective'].mean() * 100
                    supplier_defects.append({
                        'Paradigm': f'Industry {p}',
                        'Supplier': sup,
                        'Defect Rate (%)': defect_rate
                    })
            
            df_sup = pd.DataFrame(supplier_defects)
            fig = px.bar(df_sup, x='Supplier', y='Defect Rate (%)', color='Paradigm',
                        barmode='group', color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        title='Defect Rate by Supplier Across Paradigms')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Product type analysis
            product_data = []
            for p in ['3.0', '4.0', '5.0']:
                df_p = pd.DataFrame(results[p].unit_records)
                for prod in df_p['product_type'].unique():
                    prod_df = df_p[df_p['product_type'] == prod]
                    product_data.append({
                        'Paradigm': f'Industry {p}',
                        'Product': prod,
                        'Avg Cost': prod_df['total_cost'].mean(),
                        'Defect Rate': prod_df['is_defective'].mean() * 100
                    })
            
            df_prod = pd.DataFrame(product_data)
            fig = px.scatter(df_prod, x='Defect Rate', y='Avg Cost', color='Paradigm',
                           symbol='Product', size=[20]*len(df_prod),
                           color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                           title='Cost vs Defect Rate by Product Type',
                           labels={'Defect Rate': 'Defect Rate (%)', 'Avg Cost': 'Avg Cost (₹)'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # ----- TAB 4: SUSTAINABILITY -----
    with tab4:
        st.subheader("🌱 Sustainability Impact Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CO2 per unit comparison
            paradigms_list = ['Industry 3.0', 'Industry 4.0', 'Industry 5.0']
            co2_vals = [results[p.split()[-1]].total_co2_kg / max(results[p.split()[-1]].total_units, 1) for p in paradigms_list]
            
            fig = px.bar(x=paradigms_list, y=co2_vals,
                        color=paradigms_list, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        labels={'x': 'Paradigm', 'y': 'CO₂ per Unit (kg)'},
                        title='🌍 Carbon Footprint per Unit')
            fig.update_layout(showlegend=False, height=400)
            fig.update_traces(text=[f'{v:.1f} kg' for v in co2_vals], textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Energy consumption
            energy_vals = [results[p.split()[-1]].total_energy_kwh / max(results[p.split()[-1]].total_units, 1) for p in paradigms_list]
            
            fig = px.bar(x=paradigms_list, y=energy_vals,
                        color=paradigms_list, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        labels={'x': 'Paradigm', 'y': 'Energy per Unit (kWh)'},
                        title='⚡ Energy Consumption per Unit')
            fig.update_layout(showlegend=False, height=400)
            fig.update_traces(text=[f'{v:.1f} kWh' for v in energy_vals], textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        # Material waste
        waste_vals = [results[p.split()[-1]].material_waste_kg for p in paradigms_list]
        co2_saved = [results[p.split()[-1]].co2_saved_kg for p in paradigms_list]
        
        col3, col4 = st.columns(2)
        with col3:
            fig = px.bar(x=paradigms_list, y=waste_vals,
                        color=paradigms_list, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        title='🗑️ Total Material Waste (kg)',
                        labels={'x': 'Paradigm', 'y': 'Waste (kg)'})
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            fig = px.bar(x=paradigms_list, y=co2_saved,
                        color=paradigms_list, color_discrete_sequence=['#e74c3c', '#3498db', '#2ecc71'],
                        title='💚 CO₂ Saved by Early Detection (kg)',
                        labels={'x': 'Paradigm', 'y': 'CO₂ Saved (kg)'})
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Sustainability summary
        st.markdown("---")
        st.subheader("📊 Sustainability Improvement Summary (Industry 5.0 vs 3.0)")
        
        r30 = results['3.0']
        r50 = results['5.0']
        n30, n50 = max(r30.total_units, 1), max(r50.total_units, 1)
        
        scol1, scol2, scol3, scol4 = st.columns(4)
        scol1.metric("CO₂ Reduction", f"{((r30.total_co2_kg/n30 - r50.total_co2_kg/n50)/(r30.total_co2_kg/n30))*100:.1f}%")
        scol2.metric("Energy Reduction", f"{((r30.total_energy_kwh/n30 - r50.total_energy_kwh/n50)/(r30.total_energy_kwh/n30))*100:.1f}%")
        scol3.metric("Waste Reduction", f"{((r30.material_waste_kg - r50.material_waste_kg)/max(r30.material_waste_kg,1))*100:.1f}%")
        scol4.metric("CO₂ Saved (5.0)", f"{r50.co2_saved_kg:.1f} kg", "From sustainability-weighted detection")
    
    # ----- TAB 5: RAW DATA -----
    with tab5:
        st.subheader("📋 Simulation Raw Data")
        
        paradigm_select = st.selectbox("Select Paradigm", ['3.0', '4.0', '5.0'])
        df_raw = pd.DataFrame(results[paradigm_select].unit_records)
        
        st.dataframe(df_raw, use_container_width=True, height=400)
        
        csv = df_raw.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"hvac_simulation_industry_{paradigm_select}.csv",
            mime="text/csv"
        )
        
        # Summary stats
        st.subheader("Summary Statistics")
        st.dataframe(df_raw.describe(), use_container_width=True)


if __name__ == '__main__':
    main()