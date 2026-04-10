import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import seaborn as sns
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

RANDOM_SEED = 42
NUM_UNITS = 500          # Number of HVAC units to simulate per paradigm
SIM_TIME = 50000         # Max simulation time (minutes)

# --- Supplier Configuration ---
# 3 suppliers with different quality profiles
SUPPLIERS = {
    'Supplier_A': {'quality_score': 0.92, 'material_cost': 8500, 'lead_time_mean': 30},
    'Supplier_B': {'quality_score': 0.85, 'material_cost': 7200, 'lead_time_mean': 25},
    'Supplier_C': {'quality_score': 0.78, 'material_cost': 6000, 'lead_time_mean': 20},
}

# --- BOM Complexity ---
# Higher complexity = more components = higher defect probability
BOM_PROFILES = {
    'Split_AC':    {'complexity': 0.4, 'components': 45,  'base_defect_prob': 0.08},
    'Cassette_AC': {'complexity': 0.6, 'components': 68,  'base_defect_prob': 0.12},
    'VRF_System':  {'complexity': 0.9, 'components': 120, 'base_defect_prob': 0.18},
}

# --- Manufacturing Stages ---
STAGES = {
    'cutting':  {'time_mean': 12, 'time_std': 2,  'defect_contrib': 0.10, 'energy_kwh': 3.5,  'co2_kg': 1.8},
    'brazing':  {'time_mean': 25, 'time_std': 5,  'defect_contrib': 0.35, 'energy_kwh': 8.2,  'co2_kg': 4.1},
    'assembly': {'time_mean': 35, 'time_std': 8,  'defect_contrib': 0.25, 'energy_kwh': 5.0,  'co2_kg': 2.5},
    'painting': {'time_mean': 20, 'time_std': 3,  'defect_contrib': 0.15, 'energy_kwh': 6.5,  'co2_kg': 3.8},
    'testing':  {'time_mean': 15, 'time_std': 2,  'defect_contrib': 0.15, 'energy_kwh': 2.0,  'co2_kg': 1.0},
}

# --- Sustainability Weights (Industry 5.0) ---
# Environmental impact multiplier per defect type
SUSTAINABILITY_WEIGHTS = {
    'brazing_leak':     5.0,   # Refrigerant release (high GWP)
    'assembly_defect':  2.0,   # Material waste from rework
    'cutting_defect':   1.5,   # Metal scrap
    'painting_defect':  3.0,   # VOC emissions + chemical waste
    'testing_failure':  1.0,   # Energy waste only
}

# --- Cost Parameters ---
REWORK_COST_PER_UNIT = 2500       # INR
SCRAP_COST_PER_UNIT = 12000       # INR
INSPECTION_COST_PER_UNIT = 150    # INR
ML_SYSTEM_COST_PER_UNIT = 50      # INR (amortized)
HUMAN_REVIEW_COST_PER_UNIT = 200  # INR (Industry 5.0 only)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class HVACUnit:
    """Represents a single HVAC unit moving through the supply chain."""
    unit_id: int
    product_type: str
    supplier: str
    bom_complexity: float
    supplier_quality: float
    base_defect_prob: float
    material_cost: float
    
    # Tracking fields
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
    scqrs_score: float = 0.0  # Supply Chain Quality Risk Score
    
    # Feature vector for ML
    features: Dict = field(default_factory=dict)


@dataclass
class SimulationResults:
    """Stores aggregate results for a paradigm simulation."""
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
# SUPPLY CHAIN QUALITY RISK SCORE (SCQRS) — YOUR NOVEL CONTRIBUTION
# ============================================================================

def calculate_scqrs(unit: HVACUnit, paradigm: str = '3.0') -> float:
    """
    Calculate the Supply Chain Quality Risk Score (SCQRS).
    
    This is the novel index that integrates:
    1. Supplier quality reliability
    2. BOM complexity risk
    3. Process parameter risk (simulated)
    4. Sustainability impact weight (Industry 5.0 only)
    
    Score range: 0 (no risk) to 100 (extreme risk)
    """
    # Component 1: Supplier Risk (0-25 points)
    supplier_risk = (1 - unit.supplier_quality) * 25
    
    # Component 2: BOM Complexity Risk (0-25 points)
    bom_risk = unit.bom_complexity * 25
    
    # Component 3: Process Risk — simulated via random process variation (0-25 points)
    process_variation = np.random.normal(0.5, 0.15)
    process_variation = np.clip(process_variation, 0, 1)
    process_risk = process_variation * 25
    
    # Component 4: Base defect probability contribution (0-25 points)
    defect_risk = unit.base_defect_prob * 25 / 0.18  # Normalized to max
    
    scqrs = supplier_risk + bom_risk + process_risk + defect_risk
    
    # Industry 5.0: Apply sustainability weighting
    if paradigm == '5.0':
        # Higher SCQRS for products where defects have worse environmental impact
        sustainability_multiplier = 1.0 + (unit.bom_complexity * 0.3)  # Complex products = more waste
        scqrs *= sustainability_multiplier
    
    return np.clip(scqrs, 0, 100)


# ============================================================================
# SIMULATED ML DEFECT PREDICTOR
# ============================================================================

class DefectPredictor:
    """
    Simulates an ML model that predicts defect probability.
    
    In your actual project, this would be replaced with a trained
    XGBoost/Random Forest model using real or SECOM dataset features.
    
    For simulation purposes, we model the ML prediction as a function
    of supplier quality, BOM complexity, and process parameters with
    added noise to simulate model imperfection.
    """
    
    def __init__(self, accuracy: float = 0.88):
        """
        Args:
            accuracy: Simulated model accuracy (0.88 = 88% accuracy)
        """
        self.accuracy = accuracy
        self.predictions_made = 0
        self.correct_predictions = 0
    
    def predict(self, unit: HVACUnit, stage: str) -> Tuple[float, bool]:
        """
        Predict defect probability at a given manufacturing stage.
        
        Returns:
            (predicted_probability, is_flagged)
        """
        # True underlying defect probability based on supply chain factors
        true_prob = (
            unit.base_defect_prob * 
            (1 + (1 - unit.supplier_quality)) * 
            (1 + unit.bom_complexity * 0.5) *
            STAGES[stage]['defect_contrib'] / 0.35  # Normalize to brazing
        )
        true_prob = np.clip(true_prob, 0, 0.95)
        
        # Add ML model noise (simulates imperfect prediction)
        noise = np.random.normal(0, 0.08)
        predicted_prob = np.clip(true_prob + noise, 0, 1)
        
        # Flag if predicted probability exceeds threshold
        threshold = 0.15
        is_flagged = predicted_prob > threshold
        
        # Track accuracy
        self.predictions_made += 1
        actual_defect = np.random.random() < true_prob
        if is_flagged == actual_defect:
            self.correct_predictions += 1
        
        return predicted_prob, is_flagged
    
    def get_accuracy(self) -> float:
        if self.predictions_made == 0:
            return 0
        return self.correct_predictions / self.predictions_made


# ============================================================================
# SIMULATION ENVIRONMENT
# ============================================================================

class HVACManufacturingSimulation:
    """
    Main simulation class that runs the HVAC manufacturing line
    under different Industry paradigms.
    """
    
    def __init__(self, paradigm: str, num_units: int = NUM_UNITS):
        self.paradigm = paradigm
        self.num_units = num_units
        self.env = simpy.Environment()
        self.results = SimulationResults(paradigm=paradigm)
        self.ml_predictor = DefectPredictor(accuracy=0.88)
        
        # Resources (workers/machines at each stage)
        self.cutting_machine = simpy.Resource(self.env, capacity=2)
        self.brazing_station = simpy.Resource(self.env, capacity=3)
        self.assembly_line = simpy.Resource(self.env, capacity=4)
        self.painting_booth = simpy.Resource(self.env, capacity=2)
        self.testing_station = simpy.Resource(self.env, capacity=2)
        self.inspection_station = simpy.Resource(self.env, capacity=2)
        self.rework_station = simpy.Resource(self.env, capacity=1)
        
        np.random.seed(RANDOM_SEED + hash(paradigm) % 1000)
    
    def generate_unit(self, unit_id: int) -> HVACUnit:
        """Generate a random HVAC unit with supply chain attributes."""
        # Random product type
        product_type = np.random.choice(list(BOM_PROFILES.keys()))
        bom = BOM_PROFILES[product_type]
        
        # Random supplier
        supplier_name = np.random.choice(list(SUPPLIERS.keys()))
        supplier = SUPPLIERS[supplier_name]
        
        unit = HVACUnit(
            unit_id=unit_id,
            product_type=product_type,
            supplier=supplier_name,
            bom_complexity=bom['complexity'],
            supplier_quality=supplier['quality_score'],
            base_defect_prob=bom['base_defect_prob'],
            material_cost=supplier['material_cost'],
        )
        
        # Store features for ML (would be used in actual model training)
        unit.features = {
            'supplier_quality': supplier['quality_score'],
            'bom_complexity': bom['complexity'],
            'num_components': bom['components'],
            'material_cost': supplier['material_cost'],
            'supplier_lead_time': supplier['lead_time_mean'],
        }
        
        return unit
    
    def determine_defect(self, unit: HVACUnit) -> Tuple[bool, str]:
        """
        Determine if a unit is actually defective based on supply chain factors.
        Uses the SCQRS-influenced probability.
        """
        # Combined defect probability from supplier quality + BOM + randomness
        prob = unit.base_defect_prob * (2 - unit.supplier_quality) * (1 + unit.bom_complexity * 0.3)
        prob = np.clip(prob, 0, 0.5)
        
        is_defective = np.random.random() < prob
        
        if is_defective:
            # Determine which stage the defect originates from
            stage_probs = [STAGES[s]['defect_contrib'] for s in STAGES]
            stage_probs = np.array(stage_probs) / sum(stage_probs)
            defect_stage = np.random.choice(list(STAGES.keys()), p=stage_probs)
            return True, defect_stage
        
        return False, ''
    
    def process_stage(self, unit: HVACUnit, stage_name: str, resource: simpy.Resource):
        """Process a unit through a manufacturing stage."""
        stage = STAGES[stage_name]
        
        with resource.request() as req:
            yield req
            
            # Processing time with variability
            proc_time = max(1, np.random.normal(stage['time_mean'], stage['time_std']))
            yield self.env.timeout(proc_time)
            
            # Track energy and emissions
            unit.total_energy_kwh += stage['energy_kwh']
            unit.total_co2_kg += stage['co2_kg']
    
    def industry_30_process(self, unit: HVACUnit):
        """
        Industry 3.0: Traditional SPC/SQC approach.
        - Defects only detected at FINAL inspection
        - Statistical sampling (not 100% inspection)
        - No predictive capability
        """
        unit.entry_time = self.env.now
        
        # Determine if unit is actually defective
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        
        # Calculate SCQRS (for comparison, not used in decision-making)
        unit.scqrs_score = calculate_scqrs(unit, paradigm='3.0')
        
        # Process through all stages (no mid-process detection)
        yield from self.process_stage(unit, 'cutting', self.cutting_machine)
        yield from self.process_stage(unit, 'brazing', self.brazing_station)
        yield from self.process_stage(unit, 'assembly', self.assembly_line)
        yield from self.process_stage(unit, 'painting', self.painting_booth)
        yield from self.process_stage(unit, 'testing', self.testing_station)
        
        # Final inspection — statistical sampling (only catch 60% of defects)
        with self.inspection_station.request() as req:
            yield req
            yield self.env.timeout(np.random.normal(10, 2))
            unit.total_cost += INSPECTION_COST_PER_UNIT
            
            if unit.is_defective:
                detection_prob = 0.60  # Industry 3.0: 60% detection rate
                if np.random.random() < detection_prob:
                    unit.defect_detected = True
                    unit.detection_stage = 'final_inspection'
                    
                    # Rework or scrap decision
                    if np.random.random() < 0.7:  # 70% can be reworked
                        unit.reworked = True
                        with self.rework_station.request() as rework_req:
                            yield rework_req
                            yield self.env.timeout(np.random.normal(45, 10))
                        unit.total_cost += REWORK_COST_PER_UNIT
                        unit.total_energy_kwh += 15  # Rework energy
                        unit.total_co2_kg += 7.5
                    else:
                        unit.scrapped = True
                        unit.total_cost += SCRAP_COST_PER_UNIT
                        self.results.material_waste_kg += 25  # ~25 kg per scrapped unit
                else:
                    # Defect escaped to customer
                    self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record_unit(unit)
    
    def industry_40_process(self, unit: HVACUnit):
        """
        Industry 4.0: ML-automated quality prediction.
        - ML model predicts defects at each stage
        - Automated flagging and rerouting
        - No human interpretation layer
        - No sustainability consideration
        """
        unit.entry_time = self.env.now
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        unit.scqrs_score = calculate_scqrs(unit, paradigm='4.0')
        
        stages_resources = [
            ('cutting', self.cutting_machine),
            ('brazing', self.brazing_station),
            ('assembly', self.assembly_line),
            ('painting', self.painting_booth),
            ('testing', self.testing_station),
        ]
        
        for stage_name, resource in stages_resources:
            yield from self.process_stage(unit, stage_name, resource)
            
            # ML prediction at each stage
            pred_prob, is_flagged = self.ml_predictor.predict(unit, stage_name)
            unit.total_cost += ML_SYSTEM_COST_PER_UNIT / len(stages_resources)
            
            if is_flagged and unit.is_defective and stage_name == unit.defect_stage:
                # Caught at the right stage — early detection!
                unit.defect_detected = True
                unit.detection_stage = stage_name
                
                if np.random.random() < 0.85:  # 85% reworkable (caught early)
                    unit.reworked = True
                    with self.rework_station.request() as rework_req:
                        yield rework_req
                        yield self.env.timeout(np.random.normal(20, 5))  # Faster rework (caught early)
                    unit.total_cost += REWORK_COST_PER_UNIT * 0.6  # 40% cheaper rework
                    unit.total_energy_kwh += 8  # Less rework energy
                    unit.total_co2_kg += 4
                else:
                    unit.scrapped = True
                    unit.total_cost += SCRAP_COST_PER_UNIT * 0.5  # Less material wasted
                    self.results.material_waste_kg += 12
                break  # Unit exits line for rework/scrap
            
            elif is_flagged and not unit.is_defective:
                # False positive — unnecessary inspection delay
                yield self.env.timeout(5)  # Extra inspection time
        
        # If defective but not caught by ML
        if unit.is_defective and not unit.defect_detected:
            # Final automated check catches some
            if np.random.random() < 0.75:
                unit.defect_detected = True
                unit.detection_stage = 'final_auto_check'
                unit.reworked = True
                unit.total_cost += REWORK_COST_PER_UNIT * 0.8
                unit.total_energy_kwh += 12
                unit.total_co2_kg += 6
            else:
                self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record_unit(unit)
    
    def industry_50_process(self, unit: HVACUnit):
        """
        Industry 5.0: Human-AI collaborative + sustainable quality.
        - ML prediction + SHAP explainability
        - Human decision node for flagged items
        - Sustainability-weighted SCQRS scoring
        - Defects prioritized by environmental impact
        """
        unit.entry_time = self.env.now
        unit.is_defective, unit.defect_stage = self.determine_defect(unit)
        unit.scqrs_score = calculate_scqrs(unit, paradigm='5.0')
        
        stages_resources = [
            ('cutting', self.cutting_machine),
            ('brazing', self.brazing_station),
            ('assembly', self.assembly_line),
            ('painting', self.painting_booth),
            ('testing', self.testing_station),
        ]
        
        for stage_name, resource in stages_resources:
            yield from self.process_stage(unit, stage_name, resource)
            
            # ML prediction + SCQRS-informed threshold
            pred_prob, is_flagged = self.ml_predictor.predict(unit, stage_name)
            unit.total_cost += ML_SYSTEM_COST_PER_UNIT / len(stages_resources)
            
            # Industry 5.0: Adaptive threshold based on sustainability impact
            sustainability_weight = SUSTAINABILITY_WEIGHTS.get(
                f'{stage_name}_{"leak" if stage_name == "brazing" else "defect"}', 1.0
            )
            adjusted_threshold = 0.15 / sustainability_weight  # Lower threshold for high-impact stages
            is_flagged_50 = pred_prob > adjusted_threshold
            
            if is_flagged_50:
                # Human decision node (Industry 5.0 differentiator)
                unit.total_cost += HUMAN_REVIEW_COST_PER_UNIT
                yield self.env.timeout(np.random.normal(8, 2))  # Human review time
                
                # Human expert improves detection accuracy
                # (experienced inspector + ML explanation = better decision)
                human_accuracy_boost = 0.15  # 15% improvement over pure ML
                
                if unit.is_defective and stage_name == unit.defect_stage:
                    detection_prob = min(0.95, self.ml_predictor.accuracy + human_accuracy_boost)
                    
                    if np.random.random() < detection_prob:
                        unit.defect_detected = True
                        unit.detection_stage = stage_name
                        
                        # Sustainability-informed rework decision
                        if sustainability_weight >= 3.0:
                            # High environmental impact — prioritize careful rework
                            unit.reworked = True
                            with self.rework_station.request() as rework_req:
                                yield rework_req
                                yield self.env.timeout(np.random.normal(25, 5))
                            unit.total_cost += REWORK_COST_PER_UNIT * 0.5
                            unit.total_energy_kwh += 6
                            unit.total_co2_kg += 3
                            # CO2 saved by catching brazing leak early
                            self.results.co2_saved_kg += sustainability_weight * 2
                        else:
                            unit.reworked = True
                            with self.rework_station.request() as rework_req:
                                yield rework_req
                                yield self.env.timeout(np.random.normal(18, 4))
                            unit.total_cost += REWORK_COST_PER_UNIT * 0.5
                            unit.total_energy_kwh += 5
                            unit.total_co2_kg += 2.5
                        break
                
                elif not unit.is_defective:
                    # Human catches false positive — avoids unnecessary rework
                    # (Industry 5.0 advantage: human expertise filters ML errors)
                    if np.random.random() < 0.85:  # Human correctly identifies false alarm 85%
                        pass  # Unit continues — no unnecessary rework
                    else:
                        yield self.env.timeout(3)  # Minor delay from extra check
        
        # If defective but not caught
        if unit.is_defective and not unit.defect_detected:
            # Final human-AI collaborative check
            if np.random.random() < 0.88:  # Higher catch rate than 4.0
                unit.defect_detected = True
                unit.detection_stage = 'final_collaborative_check'
                unit.reworked = True
                unit.total_cost += REWORK_COST_PER_UNIT * 0.7
                unit.total_energy_kwh += 10
                unit.total_co2_kg += 5
            else:
                self.results.defects_escaped += 1
        
        unit.exit_time = self.env.now
        unit.total_cost += unit.material_cost
        self._record_unit(unit)
    
    def _record_unit(self, unit: HVACUnit):
        """Record completed unit into results."""
        self.results.total_units += 1
        self.results.total_lead_time += (unit.exit_time - unit.entry_time)
        self.results.total_cost += unit.total_cost
        self.results.total_energy_kwh += unit.total_energy_kwh
        self.results.total_co2_kg += unit.total_co2_kg
        
        if unit.is_defective:
            self.results.defective_units += 1
        if unit.defect_detected:
            self.results.defects_detected += 1
        if unit.reworked:
            self.results.units_reworked += 1
        if unit.scrapped:
            self.results.units_scrapped += 1
        
        self.results.unit_records.append({
            'unit_id': unit.unit_id,
            'product_type': unit.product_type,
            'supplier': unit.supplier,
            'bom_complexity': unit.bom_complexity,
            'supplier_quality': unit.supplier_quality,
            'is_defective': unit.is_defective,
            'defect_stage': unit.defect_stage,
            'defect_detected': unit.defect_detected,
            'detection_stage': unit.detection_stage,
            'reworked': unit.reworked,
            'scrapped': unit.scrapped,
            'lead_time': unit.exit_time - unit.entry_time,
            'total_cost': unit.total_cost,
            'energy_kwh': unit.total_energy_kwh,
            'co2_kg': unit.total_co2_kg,
            'scqrs_score': unit.scqrs_score,
        })
    
    def unit_generator(self):
        """Generate HVAC units arriving at the manufacturing line."""
        process_map = {
            '3.0': self.industry_30_process,
            '4.0': self.industry_40_process,
            '5.0': self.industry_50_process,
        }
        
        for i in range(self.num_units):
            unit = self.generate_unit(i)
            self.env.process(process_map[self.paradigm](unit))
            
            # Inter-arrival time (units arrive every 5-15 minutes)
            yield self.env.timeout(np.random.uniform(5, 15))
    
    def run(self) -> SimulationResults:
        """Execute the simulation."""
        self.env.process(self.unit_generator())
        self.env.run(until=SIM_TIME)
        
        # Calculate aggregate metrics
        n = max(self.results.total_units, 1)
        self.results.first_pass_yield = 1 - (self.results.defective_units / n)
        self.results.avg_scqrs = np.mean([r['scqrs_score'] for r in self.results.unit_records]) if self.results.unit_records else 0
        
        return self.results


# ============================================================================
# VISUALIZATION & REPORTING
# ============================================================================

def create_comparison_dashboard(results_dict: Dict[str, SimulationResults], save_path: str = 'simulation_results.png'):
    """Create a comprehensive comparison dashboard."""
    
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('HVAC Supply Chain Quality Simulation\nIndustry 3.0 vs 4.0 vs 5.0 Comparison', 
                 fontsize=16, fontweight='bold', y=1.02)
    
    paradigms = ['3.0', '4.0', '5.0']
    colors = ['#e74c3c', '#3498db', '#2ecc71']  # Red, Blue, Green
    
    # --- 1. Defect Escape Rate ---
    ax1 = axes[0, 0]
    escape_rates = [results_dict[p].defects_escaped / max(results_dict[p].defective_units, 1) * 100 
                    for p in paradigms]
    bars = ax1.bar(paradigms, escape_rates, color=colors, edgecolor='black', linewidth=0.5)
    ax1.set_title('Defect Escape Rate (%)', fontweight='bold')
    ax1.set_ylabel('% Defects Reaching Customer')
    for bar, val in zip(bars, escape_rates):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5, 
                f'{val:.1f}%', ha='center', fontweight='bold')
    
    # --- 2. Average Lead Time ---
    ax2 = axes[0, 1]
    avg_lead = [results_dict[p].total_lead_time / max(results_dict[p].total_units, 1) 
                for p in paradigms]
    bars = ax2.bar(paradigms, avg_lead, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_title('Average Lead Time (minutes)', fontweight='bold')
    ax2.set_ylabel('Minutes per Unit')
    for bar, val in zip(bars, avg_lead):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                f'{val:.1f}', ha='center', fontweight='bold')
    
    # --- 3. Total Cost per Unit ---
    ax3 = axes[0, 2]
    avg_cost = [results_dict[p].total_cost / max(results_dict[p].total_units, 1) 
                for p in paradigms]
    bars = ax3.bar(paradigms, avg_cost, color=colors, edgecolor='black', linewidth=0.5)
    ax3.set_title('Average Cost per Unit (INR)', fontweight='bold')
    ax3.set_ylabel('INR')
    for bar, val in zip(bars, avg_cost):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 50,
                f'₹{val:,.0f}', ha='center', fontweight='bold')
    
    # --- 4. CO2 Emissions per Unit ---
    ax4 = axes[1, 0]
    avg_co2 = [results_dict[p].total_co2_kg / max(results_dict[p].total_units, 1) 
               for p in paradigms]
    bars = ax4.bar(paradigms, avg_co2, color=colors, edgecolor='black', linewidth=0.5)
    ax4.set_title('CO₂ Emissions per Unit (kg)', fontweight='bold')
    ax4.set_ylabel('kg CO₂')
    for bar, val in zip(bars, avg_co2):
        ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.2,
                f'{val:.1f}', ha='center', fontweight='bold')
    
    # --- 5. SCQRS Distribution ---
    ax5 = axes[1, 1]
    for p, color in zip(paradigms, colors):
        scores = [r['scqrs_score'] for r in results_dict[p].unit_records]
        ax5.hist(scores, bins=25, alpha=0.5, color=color, label=f'Industry {p}', edgecolor='black', linewidth=0.3)
    ax5.set_title('SCQRS Score Distribution', fontweight='bold')
    ax5.set_xlabel('Supply Chain Quality Risk Score')
    ax5.set_ylabel('Frequency')
    ax5.legend()
    
    # --- 6. Summary Metrics Table ---
    ax6 = axes[1, 2]
    ax6.axis('off')
    
    table_data = []
    headers = ['Metric', 'Industry 3.0', 'Industry 4.0', 'Industry 5.0']
    
    metrics = [
        ('Total Defective', [results_dict[p].defective_units for p in paradigms]),
        ('Defects Escaped', [results_dict[p].defects_escaped for p in paradigms]),
        ('Units Reworked', [results_dict[p].units_reworked for p in paradigms]),
        ('Units Scrapped', [results_dict[p].units_scrapped for p in paradigms]),
        ('First Pass Yield', [f'{results_dict[p].first_pass_yield:.1%}' for p in paradigms]),
        ('Avg SCQRS', [f'{results_dict[p].avg_scqrs:.1f}' for p in paradigms]),
        ('Material Waste (kg)', [f'{results_dict[p].material_waste_kg:.0f}' for p in paradigms]),
        ('CO₂ Saved (kg)', [f'{results_dict[p].co2_saved_kg:.1f}' for p in paradigms]),
    ]
    
    for metric_name, values in metrics:
        table_data.append([metric_name] + [str(v) for v in values])
    
    table = ax6.table(cellText=table_data, colLabels=headers, 
                       cellLoc='center', loc='center',
                       colColours=['#f0f0f0'] + colors)
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Color the header text white for colored columns
    for j in range(1, 4):
        table[0, j].set_text_props(color='white', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n📊 Dashboard saved to: {save_path}")


def create_scqrs_analysis(results_dict: Dict[str, SimulationResults], save_path: str = 'scqrs_analysis.png'):
    """Create detailed SCQRS (your novel contribution) analysis charts."""
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle('Supply Chain Quality Risk Score (SCQRS) — Novel Contribution Analysis', 
                 fontsize=14, fontweight='bold')
    
    # Use Industry 5.0 data for SCQRS analysis
    df = pd.DataFrame(results_dict['5.0'].unit_records)
    
    # --- 1. SCQRS vs Defect Occurrence ---
    ax1 = axes[0]
    defective = df[df['is_defective'] == True]['scqrs_score']
    non_defective = df[df['is_defective'] == False]['scqrs_score']
    ax1.hist(non_defective, bins=20, alpha=0.6, color='#2ecc71', label='Non-Defective', edgecolor='black', linewidth=0.3)
    ax1.hist(defective, bins=20, alpha=0.6, color='#e74c3c', label='Defective', edgecolor='black', linewidth=0.3)
    ax1.set_title('SCQRS: Defective vs Non-Defective Units')
    ax1.set_xlabel('SCQRS Score')
    ax1.legend()
    
    # --- 2. SCQRS by Supplier ---
    ax2 = axes[1]
    supplier_groups = df.groupby('supplier')['scqrs_score'].mean().sort_values()
    colors_sup = ['#2ecc71', '#f39c12', '#e74c3c']
    supplier_groups.plot(kind='barh', ax=ax2, color=colors_sup[:len(supplier_groups)], edgecolor='black')
    ax2.set_title('Average SCQRS by Supplier')
    ax2.set_xlabel('SCQRS Score')
    
    # --- 3. SCQRS by Product Type ---
    ax3 = axes[2]
    product_groups = df.groupby('product_type')['scqrs_score'].mean().sort_values()
    product_groups.plot(kind='barh', ax=ax3, color=['#3498db', '#9b59b6', '#e67e22'], edgecolor='black')
    ax3.set_title('Average SCQRS by Product Type (BOM Complexity)')
    ax3.set_xlabel('SCQRS Score')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📊 SCQRS Analysis saved to: {save_path}")


def print_summary(results_dict: Dict[str, SimulationResults]):
    """Print a clean text summary of all paradigm results."""
    
    print("\n" + "="*80)
    print("  HVAC MANUFACTURING SUPPLY CHAIN QUALITY SIMULATION — RESULTS SUMMARY")
    print("="*80)
    
    for paradigm in ['3.0', '4.0', '5.0']:
        r = results_dict[paradigm]
        n = max(r.total_units, 1)
        
        print(f"\n{'─'*40}")
        print(f"  INDUSTRY {paradigm}")
        print(f"{'─'*40}")
        print(f"  Units Processed:      {r.total_units}")
        print(f"  Defective Units:      {r.defective_units} ({r.defective_units/n:.1%})")
        print(f"  Defects Detected:     {r.defects_detected}")
        print(f"  Defects ESCAPED:      {r.defects_escaped} ({r.defects_escaped/max(r.defective_units,1):.1%} escape rate)")
        print(f"  Units Reworked:       {r.units_reworked}")
        print(f"  Units Scrapped:       {r.units_scrapped}")
        print(f"  First Pass Yield:     {r.first_pass_yield:.1%}")
        print(f"  Avg Lead Time:        {r.total_lead_time/n:.1f} min")
        print(f"  Avg Cost/Unit:        ₹{r.total_cost/n:,.0f}")
        print(f"  Avg Energy/Unit:      {r.total_energy_kwh/n:.1f} kWh")
        print(f"  Avg CO₂/Unit:         {r.total_co2_kg/n:.1f} kg")
        print(f"  Material Waste:       {r.material_waste_kg:.0f} kg total")
        print(f"  CO₂ Saved:            {r.co2_saved_kg:.1f} kg")
        print(f"  Avg SCQRS Score:      {r.avg_scqrs:.1f}/100")
    
    # Improvement summary
    print(f"\n{'='*80}")
    print("  IMPROVEMENT SUMMARY (vs Industry 3.0 baseline)")
    print(f"{'='*80}")
    
    r30 = results_dict['3.0']
    for paradigm in ['4.0', '5.0']:
        r = results_dict[paradigm]
        n30 = max(r30.total_units, 1)
        n = max(r.total_units, 1)
        
        escape_improvement = ((r30.defects_escaped - r.defects_escaped) / max(r30.defects_escaped, 1)) * 100
        cost_improvement = ((r30.total_cost/n30 - r.total_cost/n) / (r30.total_cost/n30)) * 100
        co2_improvement = ((r30.total_co2_kg/n30 - r.total_co2_kg/n) / (r30.total_co2_kg/n30)) * 100
        lead_improvement = ((r30.total_lead_time/n30 - r.total_lead_time/n) / (r30.total_lead_time/n30)) * 100
        
        print(f"\n  Industry {paradigm} vs 3.0:")
        print(f"    Defect Escape:  {escape_improvement:+.1f}% {'↓ (better)' if escape_improvement > 0 else '↑ (worse)'}")
        print(f"    Cost/Unit:      {cost_improvement:+.1f}% {'↓ (cheaper)' if cost_improvement > 0 else '↑ (costlier)'}")
        print(f"    CO₂/Unit:       {co2_improvement:+.1f}% {'↓ (greener)' if co2_improvement > 0 else '↑ (dirtier)'}")
        print(f"    Lead Time:      {lead_improvement:+.1f}% {'↓ (faster)' if lead_improvement > 0 else '↑ (slower)'}")


def export_data(results_dict: Dict[str, SimulationResults], save_path: str = 'simulation_data.csv'):
    """Export all unit-level data to CSV for further analysis."""
    all_records = []
    for paradigm, results in results_dict.items():
        for record in results.unit_records:
            record['paradigm'] = f'Industry {paradigm}'
            all_records.append(record)
    
    df = pd.DataFrame(all_records)
    df.to_csv(save_path, index=False)
    print(f"\n📁 Raw data exported to: {save_path}")
    print(f"   {len(df)} records × {len(df.columns)} columns")
    print(f"   Columns: {', '.join(df.columns)}")
    return df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run the complete simulation and generate outputs."""
    
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  HVAC Manufacturing Supply Chain Quality Simulation         ║")
    print("║  Comparing Industry 3.0 → 4.0 → 5.0 Quality Paradigms     ║")
    print("║  Novel Contribution: SCQRS Index                           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"\nSimulating {NUM_UNITS} HVAC units per paradigm...")
    
    results = {}
    
    for paradigm in ['3.0', '4.0', '5.0']:
        print(f"\n🔄 Running Industry {paradigm} simulation...", end=' ')
        sim = HVACManufacturingSimulation(paradigm=paradigm, num_units=NUM_UNITS)
        results[paradigm] = sim.run()
        print(f"✅ Complete ({results[paradigm].total_units} units processed)")
    
    # Print text summary
    print_summary(results)
    
    # Generate visualizations
    print("\n\n📊 Generating visualizations...")
    create_comparison_dashboard(results, 'simulation_results.png')
    create_scqrs_analysis(results, 'scqrs_analysis.png')
    
    # Export data
    df = export_data(results, 'simulation_data.csv')
    
    print("\n\n✅ SIMULATION COMPLETE!")
    print("="*60)
    print("Files generated:")
    print("  1. simulation_results.png  — Comparison dashboard")
    print("  2. scqrs_analysis.png      — SCQRS novel contribution analysis")
    print("  3. simulation_data.csv     — Raw data for further ML training")
    print("\nNext steps:")
    print("  → Use simulation_data.csv to train your XGBoost/RF model")
    print("  → Apply SHAP analysis for Industry 5.0 explainability")
    print("  → Write up comparative results for IEEE paper")
    
    return results, df


if __name__ == '__main__':
    results, df = main()