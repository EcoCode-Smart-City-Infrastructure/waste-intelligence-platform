"""Environmental accounting (directive 9.5).

Transparent, versioned method WIN-ENV-ACCT-1.0. Factors are simplified
planning estimates aligned to EPA WARM v15 category directions (diverting
material from landfill vs landfilling it). They are NOT WARM outputs and
must be re-based on the current WARM release before any external or
regulatory claim. Every stored record keeps quantity, factor, formula,
method version and assumptions so the number can be re-derived or disputed.
"""
from __future__ import annotations

METHODOLOGY_VERSION = "WIN-ENV-ACCT-1.0"
ASSUMPTIONS = ("Net kg CO2e per kg of material managed by the stated pathway "
               "versus landfilling the same material. Simplified planning "
               "factors (EPA WARM v15-aligned categories); excludes "
               "collection transport. Verify against the current WARM "
               "release before external reporting.")

# net kg CO2e avoided per kg diverted (positive) - planning estimates
DIVERSION_FACTORS = {
    "food_organics": {"composting": 0.12, "anaerobic_digestion": 0.18},
    "yard_organics": {"composting": 0.10},
    "paper": {"recycling": 1.10},
    "cardboard": {"recycling": 1.05},
    "plastic_pet": {"recycling": 0.85},
    "plastic_mixed": {"recycling": 0.55},
    "metal": {"recycling": 1.60},
    "glass": {"recycling": 0.30},
    "mixed_recyclables": {"recycling": 0.80},
    "mixed_waste": {"energy_recovery": 0.05, "landfill": 0.0},
}

def compute_co2e(material: str, pathway_type: str, quantity_kg: float) -> dict:
    pathways = DIVERSION_FACTORS.get(material)
    if pathways is None or pathway_type not in pathways:
        raise ValueError(
            f"No WIN-ENV-ACCT-1.0 factor for material={material} pathway={pathway_type}. "
            f"Known materials: {sorted(DIVERSION_FACTORS)}")
    factor = pathways[pathway_type]
    co2e = round(quantity_kg * factor, 4)
    return {"material": material, "pathway_type": pathway_type,
            "quantity_kg": quantity_kg, "factor_kg_co2e_per_kg": factor,
            "co2e_kg": co2e,
            "formula": f"co2e_kg = quantity_kg ({quantity_kg}) x factor ({factor} kg CO2e/kg, {material} via {pathway_type})",
            "methodology_version": METHODOLOGY_VERSION,
            "assumptions": ASSUMPTIONS, "data_status": "derived"}
