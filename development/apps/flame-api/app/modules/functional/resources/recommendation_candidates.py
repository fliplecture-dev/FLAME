"""Historical helper imports retained for callers during B11 migration."""
from app.modules.functional.resources.candidates import playable
from app.modules.functional.activity_kits.candidates import eligible_candidates as kit_candidates, kit_card


def candidate_rows(resources, teachers, kits, **kwargs):
    return [candidate.selection_data() for candidate in [*resources, *teachers, *kits]]
