"""Compile the active binding once per evaluation preparation, never per candidate."""
from dataclasses import dataclass
from app.domain.value_objects.general_context_request import GeneralContextRequest


@dataclass(frozen=True)
class ContextPlan:
    available: bool
    reason: str
    binding: object = None
    predicate: object = None
    assumptions: tuple[str, ...] = ()
    secondary: tuple = ()


def compile_context(registry, request):
    from dataclasses import replace
    from app.domain.value_objects.general_context_request import ContextSlot
    plan=_compile_single(registry,request)
    if not plan.available:return plan
    facets=request.context.facets
    if not facets.values:return plan
    frame=request.context;sid=frame.situation.value
    if len(facets.values)!=1:return ContextPlan(False,'unsupported_constraint')
    facet=facets.values[0]
    if facet.startswith('transport:'):
        return plan if sid=='travel.journey' else ContextPlan(False,'unsupported_constraint')
    secondary_id={('social.date','meal:dinner'):'social.meal',('social.meal','celebration:birthday'):'social.birthday_gathering'}.get((sid,facet))
    if secondary_id is None:return ContextPlan(False,'unsupported_constraint')
    situation=next((s for s in registry.situations if s.identifier==secondary_id),None)
    if situation is None:return ContextPlan(False,'capability_not_enabled')
    secondary_frame=replace(frame,situation=ContextSlot('Known',(secondary_id,),facets.spans),activity=ContextSlot('Known',(situation.activity,),facets.spans),facets=ContextSlot())
    secondary_request=replace(request,occasion=situation.projection_occasion,context=secondary_frame)
    second=_compile_single(registry,secondary_request)
    if not second.available:return second
    return replace(plan,secondary=((secondary_request,second),))


def _compile_single(registry, request):
    if type(request) is not GeneralContextRequest:
        raise ValueError('General frame required.')
    frame = request.context
    if frame.bundle_id!=registry.bundle_id:return ContextPlan(False,'invalid_context_projection')
    if frame.taxonomy_sha256 != registry.taxonomy_hash:
        return ContextPlan(False, 'invalid_context_projection')
    if (tuple(frame.style.values) != ((request.style,) if request.style else ())
            or tuple(frame.colours.values) != (request.colours or ())
            or tuple(frame.categories.values) != tuple(c.kind+':'+c.value for c in request.garment_categories or ())):
        return ContextPlan(False, 'invalid_context_projection')
    binding = registry.binding_for(frame.situation.value)
    if binding is None:
        return ContextPlan(False, 'capability_not_enabled')
    if any(getattr(frame, slot).state != 'Known' for slot in binding.required_context):
        return ContextPlan(False, 'required_context_missing')
    situation = next(s for s in registry.situations if s.identifier == frame.situation.value)
    if frame.activity.value != situation.activity:
        return ContextPlan(False, 'unsupported_constraint')
    if any(getattr(frame, slot).state in ('Ambiguous', 'Conflicting', 'Unsupported') for slot in frame.__dataclass_fields__ if hasattr(getattr(frame, slot), 'state')):
        return ContextPlan(False, 'unsupported_constraint')
    if frame.role.value is not None and frame.role.value not in binding.roles:
        return ContextPlan(False, 'unsupported_role')
    if any(getattr(frame, slot).state != 'Unspecified' for slot in ('environment', 'soft_preferences', 'goals')):
        return ContextPlan(False, 'unsupported_constraint')
    if (frame.venue.state != 'Unspecified' and frame.venue.value not in binding.allowed_venues
            or frame.companions.state != 'Unspecified' and frame.companions.value not in binding.allowed_companions):
        return ContextPlan(False, 'unsupported_constraint')
    code = frame.dress_code.value
    formality = frame.formality.value
    if code is not None and formality is not None and code != formality:
        return ContextPlan(False, 'conflicting_context')
    effective = code if code is not None else formality
    if request.occasion != binding.declaration_target or request.formality != effective:
        return ContextPlan(False, 'invalid_context_projection')
    if binding.appearance_required and effective is None:
        return ContextPlan(False, 'required_context_missing')
    predicate = next((p for p in binding.predicates if p.dress_code == effective and (p.role is None or p.role == frame.role.value)), None)
    if predicate is None:
        return ContextPlan(False, 'unsupported_dress_code')
    assumptions = ('Guest role assumed because you did not specify your role.',) if frame.role.state == 'Unspecified' and binding.assumed_role == 'guest' else ()
    if effective is None and binding.unspecified_note:
        assumptions = (*assumptions, binding.unspecified_note)
    if effective is None and binding.role_notes:
        assumptions = (*assumptions, dict(binding.role_notes)[frame.role.value])
    return ContextPlan(True, 'approved_binding', binding, predicate, assumptions)
