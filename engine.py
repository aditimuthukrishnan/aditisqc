"""
Shared simulation engine and utilities for the HVAC Quality Dashboard.
All pages import from this module.
"""

import simpy
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ============================================================================
# CONFIGURATION
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

DEFAULT_SUPPLIERS = {
    'Supplier_A': {'quality_score': 0.92, 'material_cost': 8500, 'lead_time_mean': 30},
    'Supplier_B': {'quality_score': 0.85, 'material_cost': 7200, 'lead_time_mean': 25},
    'Supplier_C': {'quality_score': 0.78, 'material_cost': 6000, 'lead_time_mean': 20},
}

DEFAULT_BOM = {
    'Split_AC':    {'complexity': 0.4, 'components': 45,  'base_defect_prob': 0.08},
    'Cassette_AC': {'complexity': 0.6, 'components': 68,  'base_defect_prob': 0.12},
    'VRF_System':  {'complexity': 0.9, 'components': 120, 'base_defect_prob': 0.18},
}

# ============================================================================
# DATA CLASSES
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
# SCQRS INDEX
# ============================================================================

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


# ============================================================================
# SIMULATION ENGINE
# ============================================================================

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
        if np.random.random() < prob:
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


def run_all_paradigms(num_units, suppliers, bom_profiles):
    results = {}
    for paradigm in ['3.0', '4.0', '5.0']:
        sim = HVACSimulation(paradigm, num_units, suppliers, bom_profiles)
        results[paradigm] = sim.run()
    return results
