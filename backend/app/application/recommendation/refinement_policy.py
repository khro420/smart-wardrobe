"""Pinned refinement definitions; loading never activates a service."""
from dataclasses import dataclass
from pathlib import Path
from app.application.recommendation.context_relevance_policy import _read
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.recommendation_refinement import CATEGORIES, POLICY_VERSION, PROFILE, CATEGORY_VERSION

POLICY_SHA256 = 'f347c29e22fdd9cd8947e2b70322118d26a0d47c0380c64ab0faf65f1d26f0e4'
CONFIG = Path(__file__).with_name('config') / 'recommendation_refinement.v1.json'
ORDINARY_SITUATIONS = tuple(sorted((
    'everyday.shopping', 'everyday.academic_attendance', 'everyday.casual_outing',
    'social.date', 'social.meal', 'academic.library_study', 'academic.group_study',
    'professional.office_day', 'professional.workplace_meeting',
    'social.birthday_gathering', 'social.house_gathering', 'leisure.cinema_outing',
    'social.cafe_meetup', 'leisure.city_sightseeing', 'travel.journey',
)))


@dataclass(frozen=True)
class RefinementPolicy:
    version: str = POLICY_VERSION
    sha256: str = POLICY_SHA256
    ordinary_situations: tuple = ORDINARY_SITUATIONS
    max_results: int = 10

    @classmethod
    def load(cls, path=CONFIG):
        raw, _ = _read(path, POLICY_SHA256)
        expected = dict(version=POLICY_VERSION, profile=PROFILE, default_activation=False,
            category_version=CATEGORY_VERSION, categories=list(CATEGORIES),
            ordinary_situations=list(ORDINARY_SITUATIONS), max_results=10,
            root_mode='initial_permitted_optimum_v1', alternative_mode='same_R_floor_base_distinct_v1',
            maximum_configuration_bytes=65536, supplement_bytes=32768,
            relative_proof_bytes=294912, provenance_bytes=327680, integer_digits=4096)
        if raw != expected or tuple(sorted(GARMENT_STRUCTURE)) != CATEGORIES:
            raise ValueError('Unsupported refinement policy or category contract.')
        return cls()
