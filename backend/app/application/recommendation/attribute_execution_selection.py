"""Explicit default-off B1 selection; configured only at composition time."""
from dataclasses import dataclass
from app.domain.value_objects.attribute_conditions import AttributeRequestError

ENVIRONMENT_KEY='SMART_WARDROBE_ASSISTANT_ATTRIBUTE_PROFILE'
PROFILE='attribute_requests_v1'


@dataclass(frozen=True)
class AttributeExecutionSelection:
    profile: str='disabled'

    def __post_init__(self):
        if self.profile not in ('disabled',PROFILE):raise AttributeRequestError('AttributeUnavailable','invalid_attribute_profile')

    @property
    def enabled(self):return self.profile==PROFILE

    def validate_dependencies(self,description_policy,interpreter):
        if not self.enabled:return
        from app.application.wardrobe.description_policy import DescriptionPolicy
        if type(description_policy) is not DescriptionPolicy or getattr(interpreter,'bundle_id',None)!='context_18_v1':
            raise AttributeRequestError('AttributeUnavailable','attribute_dependencies_unavailable')
