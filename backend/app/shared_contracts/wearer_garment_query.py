"""One frozen account source and its derived wearer-usable acquisition view."""
from dataclasses import dataclass
from app.domain.value_objects.wearer_category_eligibility import EligibilityWriteDraft

@dataclass(frozen=True)
class WearerGarmentQuery:
    owner_id:str
    account_rows:tuple
    account_descriptions:tuple
    usable_rows:tuple
    usable_descriptions:tuple
    eligibility:EligibilityWriteDraft
    account_subtypes:tuple=()
    usable_subtypes:tuple=()

    def _owner(self,owner):
        if owner!=self.owner_id:raise ValueError('Captured wardrobe owner mismatch.')
    def get_confirmed_available_garments(self,owner):self._owner(owner);return self.usable_rows
    def list_available_garment_ids(self,owner):return [g.garment_id for g in self.get_confirmed_available_garments(owner)]
    def get_confirmed_garment_descriptions(self,owner,policy):
        self._owner(owner)
        if len(self.account_descriptions)!=len(self.account_rows):raise ValueError('Captured descriptions unavailable.')
        return self.usable_descriptions

    def get_confirmed_garment_subtypes(self,owner):self._owner(owner);return self.usable_subtypes
