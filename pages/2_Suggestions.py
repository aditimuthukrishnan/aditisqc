"""
Page: Actionable Suggestions
"""

import streamlit as st
import pandas as pd
from theme import apply_theme, suggestion_card, section_divider

st.set_page_config(page_title="Suggestions", layout="wide")
apply_theme()

st.markdown('<div class="page-title">Recommendations</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Data-driven suggestions based on simulation results</div>', unsafe_allow_html=True)

if 'results' not in st.session_state:
    st.info("Run the simulation from the home page first.")
    st.stop()

results = st.session_state['results']
r50 = results['5.0']
r30 = results['3.0']
df = pd.DataFrame(r50.unit_records)

section_divider()

# --- Supplier Recommendations ---
st.markdown("##### Supplier Quality")

sup_stats = df.groupby('supplier').agg(
    defect_rate=('is_defective', 'mean'),
    avg_cost=('total_cost', 'mean'),
    avg_scqrs=('scqrs_score', 'mean'),
    count=('unit_id', 'count'),
).reset_index()

for _, row in sup_stats.iterrows():
    rate = row['defect_rate'] * 100
    if rate > 20:
        suggestion_card(
            f"{row['supplier']}: High defect rate ({rate:.1f}%)",
            f"Average SCQRS of {row['avg_scqrs']:.1f} indicates significant supply chain risk. "
            f"Consider requesting corrective action reports, increasing incoming inspection frequency, "
            f"or qualifying an alternative supplier. Average cost impact per unit: {row['avg_cost']:,.0f}.",
            level="critical"
        )
    elif rate > 12:
        suggestion_card(
            f"{row['supplier']}: Moderate defect rate ({rate:.1f}%)",
            f"SCQRS score of {row['avg_scqrs']:.1f}. Monitor closely and consider joint quality "
            f"improvement programs. A supplier development initiative could reduce defect rates "
            f"and associated rework costs.",
            level="warning"
        )
    else:
        suggestion_card(
            f"{row['supplier']}: Acceptable performance ({rate:.1f}%)",
            f"SCQRS score of {row['avg_scqrs']:.1f}. Continue current quality agreements. "
            f"Consider this supplier as a benchmark for best practices.",
            level="info"
        )

section_divider()

# --- Process Stage Recommendations ---
st.markdown("##### Manufacturing Process")

defective = df[df['is_defective'] == True]
if len(defective) > 0:
    stage_counts = defective['defect_stage'].value_counts()
    worst_stage = stage_counts.index[0]
    worst_count = stage_counts.iloc[0]
    total_defective = len(defective)

    suggestion_card(
        f"Brazing is the primary defect source ({worst_count}/{total_defective} defects)" if worst_stage == 'brazing'
        else f"{worst_stage.title()} accounts for {worst_count}/{total_defective} defects",
        f"The {worst_stage} stage contributes {worst_count/total_defective:.0%} of all defects. "
        f"This stage should be the priority for process improvement initiatives. "
        f"Consider implementing in-line sensors, operator training, or equipment maintenance schedules. "
        f"For brazing specifically, temperature control and flux quality are common root causes.",
        level="critical"
    )

    for stage, count in stage_counts.items():
        if stage != worst_stage and count > total_defective * 0.15:
            suggestion_card(
                f"{stage.title()} stage: {count} defects ({count/total_defective:.0%})",
                f"Secondary defect source. Review process parameters and operator procedures. "
                f"Implementing statistical process control charts at this stage could provide "
                f"early warning of process drift.",
                level="warning"
            )

section_divider()

# --- Cost Optimization ---
st.markdown("##### Cost Optimization")

n50 = max(r50.total_units, 1)
n30 = max(r30.total_units, 1)
cost_saved = (r30.total_cost / n30) - (r50.total_cost / n50)
rework_pct = r50.units_reworked / n50 * 100
scrap_pct = r50.units_scrapped / n50 * 100

if cost_saved > 0:
    suggestion_card(
        f"Industry 5.0 approach saves {cost_saved:,.0f} per unit vs traditional methods",
        f"The predictive quality system with human-AI collaboration reduces costs through "
        f"earlier defect detection, lower rework costs (caught before full assembly), and "
        f"reduced scrap rates. Current rework rate: {rework_pct:.1f}%, scrap rate: {scrap_pct:.1f}%.",
        level="info"
    )

if rework_pct > 5:
    suggestion_card(
        f"Rework rate at {rework_pct:.1f}% — opportunity for reduction",
        f"Each rework cycle adds cost, energy, and lead time. Focus on the top defect-contributing "
        f"stage and implement mistake-proofing (poka-yoke) to prevent defects rather than detect them.",
        level="warning"
    )

section_divider()

# --- Sustainability ---
st.markdown("##### Environmental Impact")

co2_saved = (r30.total_co2_kg / n30) - (r50.total_co2_kg / n50)
energy_saved = (r30.total_energy_kwh / n30) - (r50.total_energy_kwh / n50)
waste_reduced = r30.material_waste_kg - r50.material_waste_kg

if co2_saved > 0:
    suggestion_card(
        f"CO2 reduction: {co2_saved:.1f} kg per unit with Industry 5.0",
        f"Early defect detection prevents unnecessary energy consumption from rework and scrap. "
        f"Over {n50} units, this represents {co2_saved * n50:.0f} kg total CO2 avoided. "
        f"Additionally, {r50.co2_saved_kg:.1f} kg CO2 was saved through sustainability-weighted "
        f"detection prioritizing high-impact defects like brazing leaks.",
        level="info"
    )

if waste_reduced > 0:
    suggestion_card(
        f"Material waste reduced by {waste_reduced:.0f} kg",
        f"Fewer scrapped units means less raw material waste. For HVAC equipment, "
        f"this includes copper, aluminium, steel, and refrigerants — all resource-intensive materials. "
        f"Consider feeding waste data back to suppliers for closed-loop quality improvement.",
        level="info"
    )

section_divider()

# --- SCQRS Threshold Recommendation ---
st.markdown("##### SCQRS Monitoring Thresholds")

avg_scqrs_defective = df[df['is_defective'] == True]['scqrs_score'].mean() if len(df[df['is_defective'] == True]) > 0 else 0
avg_scqrs_good = df[df['is_defective'] == False]['scqrs_score'].mean() if len(df[df['is_defective'] == False]) > 0 else 0

suggested_threshold = (avg_scqrs_defective + avg_scqrs_good) / 2

suggestion_card(
    f"Set SCQRS alert threshold at {suggested_threshold:.0f}",
    f"Defective units average a SCQRS of {avg_scqrs_defective:.1f}, while non-defective units "
    f"average {avg_scqrs_good:.1f}. Setting the alert threshold at {suggested_threshold:.0f} would "
    f"flag high-risk units for additional inspection without excessive false alarms. "
    f"Units scoring above {avg_scqrs_defective:.0f} should trigger mandatory review.",
    level="info"
)
