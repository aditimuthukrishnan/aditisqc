# SCQRS — Simulation-Optimized Green VSM for HVAC Manufacturing

A BTech research project combining **Value Stream Mapping**, **Discrete Event Simulation**, and **Multi-Objective Optimization (NSGA-II)** for lean-green manufacturing in the Indian HVAC industry.

> **Novel contribution:** The first study to integrate VSM + simulation + NSGA-II optimization for HVAC manufacturing globally — incorporating refrigerant leakage emissions (R-410A, GWP 2088) as a manufacturing metric.

---

## Research Context

India's HVAC market ($12B, growing at 7.5–16% CAGR) faces mounting pressure from BEE star ratings, the Kigali Amendment's HFC phase-down, and India's net-zero 2070 commitment. Despite this, no academic research exists on lean-green manufacturing optimization for Indian HVAC facilities.

This project fills that gap with real factory data from an Indian HVAC facility.

---

## Methodology

| Phase | Approach | Tools |
|-------|----------|-------|
| 1 | Green Value Stream Mapping (E-VSM) | Lean + environmental metrics |
| 2 | Discrete Event Simulation | Arena / FlexSim |
| 3 | Multi-Objective Optimization | NSGA-II (Pareto front) |
| 4 | Solution Selection | AHP-TOPSIS |

**Optimization objectives:**
- Minimize production lead time
- Minimize WIP inventory
- Minimize energy consumption per unit
- Minimize CO₂-equivalent emissions (including refrigerant leakage)

---

## Dashboard & Simulation

An interactive dashboard built with **Streamlit** visualizes:
- Current vs future state value stream maps
- Simulation results and scenario analysis
- Pareto-optimal lean-green trade-offs
- HVAC-specific environmental metrics (refrigerant emissions, VOC, energy per station)

## Running the Dashboard

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit dashboard
streamlit run app.py
```

---

## Project Structure

```
aditisqc/
├── app.py                   # Streamlit entry point
├── dashboard.py             # Dashboard layout and components
├── engine.py                # Simulation and optimization engine
├── theme.py                 # UI theme configuration
├── pages/                   # Multi-page Streamlit views
├── hvac_simulation.py       # HVAC DES simulation model
├── simulation_data.csv      # Simulation output data
├── simulation_results.png   # Results visualization
└── scqrs_analysis.png       # SCQRS analysis chart
```

---

## Key Findings

- HVAC manufacturing process cycle efficiency: < 0.05% (customer needs ~20 min value-added work; delivery takes ~32 days)
- Refrigerant emissions (R-410A): GWP of 2,088 — a critical and previously unmeasured manufacturing metric
- NSGA-II generates Pareto-optimal solutions balancing lean and green objectives simultaneously

---

## Target Publication

**IEEE IEEM 2026 / IEEE Access**

*"A Simulation-Optimized Green Value Stream Mapping Framework Using NSGA-II for Lean-Green Manufacturing: A Case Study in the Indian HVAC Industry"*

---

## Tech Stack

`Python` · `Streamlit` · `Pandas` · `Plotly` · `NSGA-II` · `Discrete Event Simulation`
