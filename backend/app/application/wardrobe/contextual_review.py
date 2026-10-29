"""Owner review projection; no automatic annotation of historical records."""
import hashlib
import json
from app.application.recommendation.garment_evidence_mapper import GarmentEvidenceMapper
from app.application.nlp.vocabulary import Vocabulary
from app.domain.value_objects.contextual_garment_evidence import KEY


def revision(row):
    basis = [row[k] for k in ('id', 'user_id', 'category', 'style_tags', 'attributes_json', 'additional_attributes')]
    return hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def view(row):
    from app.infrastructure.persistence.confirmed_garment_query_adapter import _snapshot
    garment = _snapshot(row)
    styles = GarmentEvidenceMapper().classify(garment).style
    evidence = garment.contextual_suitability
    valid = (evidence.state == 'Known' and evidence.review_state == 'Known'
             and evidence.reviewed_category == garment.category and evidence.reviewed_styles == styles.values
             and styles.state == 'Known' and len(styles.values) == 1)
    return {'revision': revision(row), 'styles': list(styles.values), 'style_state': styles.state,
            'style_options': sorted(Vocabulary.load().values['style']), 'review_current': valid,
            'wedding_choice': 'deny' if 'deny' in evidence.wedding_decisions else 'allow' if evidence.wedding_decisions == ('allow',) else 'unknown',
            'evidence_state': evidence.state}


def invalidate_review(attrs):
    value = attrs.get(KEY)
    if isinstance(value, dict) and 'style_review' in value:
        attrs[KEY] = {**value, 'style_review': None}
