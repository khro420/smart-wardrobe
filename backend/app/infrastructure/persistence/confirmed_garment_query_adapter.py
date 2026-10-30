"""Digital Wardrobe read adapter: legacy IDs and strictly confirmed snapshots."""

from __future__ import annotations

from functools import lru_cache
from contextlib import nullcontext
from dataclasses import replace
import json

from app.infrastructure.persistence.postgresql_repository import connection
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot, GarmentPaletteEntry
from app.domain.value_objects.garment_attributes import GARMENT_STRUCTURE
from app.domain.value_objects.contextual_garment_evidence import KEY, project_contextual_evidence
from app.domain.value_objects.general_context_evidence import KEY as APPEARANCE_KEY, AppearanceEvidence, project_appearance_evidence
from app.domain.value_objects.saved_attribute_evidence import KEY as SOURCE_KEY, SavedAttributeEvidence, project_saved_attribute_evidence


def _json(value):
    try:
        return json.loads(value) if isinstance(value, str) else None
    except (ValueError, TypeError):
        return None


def _text(value):
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _tags(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(raw, str) or not raw.strip() for raw in value):
        raise ValueError("Invalid tag collection.")
    return tuple(dict.fromkeys(raw.strip() for raw in value))


def _descriptions(value):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, list) and all(item is None or isinstance(item, str) for item in value):
        return tuple(value)
    raise ValueError("Invalid description value.")


def _snapshot(row):
    invalid = []
    attrs = _json(row["attributes_json"])
    if row["attributes_json"] is not None and not isinstance(attrs, dict):
        invalid.append("attributes_json")
    attrs = attrs if isinstance(attrs, dict) else {}
    extra = _json(row["additional_attributes"])
    if row["additional_attributes"] is not None and not isinstance(extra, dict):
        invalid.append("additional_attributes")
    extra = extra if isinstance(extra, dict) else {}
    appearance = project_appearance_evidence(attrs.get(APPEARANCE_KEY, extra.get(APPEARANCE_KEY)), APPEARANCE_KEY in attrs or APPEARANCE_KEY in extra)
    if (APPEARANCE_KEY in attrs) != (APPEARANCE_KEY in extra) or attrs.get(APPEARANCE_KEY) != extra.get(APPEARANCE_KEY) or invalid:
        appearance = AppearanceEvidence(state='Malformed')
    contextual = project_contextual_evidence(attrs.get(KEY, extra.get(KEY)), KEY in attrs or KEY in extra)
    if (KEY in attrs and KEY in extra and attrs[KEY] != extra[KEY]) or invalid:
        other = project_contextual_evidence(extra.get(KEY), KEY in extra)
        contextual = replace(contextual, state='Malformed', wedding_decisions=tuple(sorted(set(contextual.wedding_decisions + other.wedding_decisions))))
    # Canonical attribute JSON wins over its mirrored additional_attributes.
    attrs = {**extra, **attrs}
    role, layer = GARMENT_STRUCTURE.get(row["category"], (None, None))
    raw_palette = attrs.get("color_palette")
    palette = None
    if raw_palette is not None:
        try:
            if not isinstance(raw_palette, list):
                raise ValueError("Invalid palette.")
            palette = tuple(GarmentPaletteEntry(value["hex"], value.get("coverage")) for value in raw_palette)
        except (ValueError, TypeError, KeyError):
            invalid.append("colour_palette")
    def project(name, value, parser):
        try:
            return parser(value)
        except ValueError:
            invalid.append(name)
            return None
    def stored_tags(name, fallback):
        raw = row[name]
        value = _json(raw)
        # Absent/JSON-null columns may use the existing attribute representation;
        # malformed non-null JSON is not silently replaced by the mirror.
        if raw is not None and value is None and raw.strip() != "null":
            invalid.append(name)
            return None
        return project(name, attrs.get(fallback) if value is None else value, _tags)
    style = stored_tags("style_tags", "style")
    saved = project_saved_attribute_evidence(attrs.get(SOURCE_KEY), SOURCE_KEY in attrs,
                                            style, row['category'], row['preferred_media_id'], row['user_id'])
    # New source records are always mirrored; absence on legacy rows is permitted.
    original = _json(row['attributes_json'])
    mirror = _json(row['additional_attributes'])
    original = original if isinstance(original, dict) else {}
    mirror = mirror if isinstance(mirror, dict) else {}
    if (SOURCE_KEY in original) != (SOURCE_KEY in mirror) or original.get(SOURCE_KEY) != mirror.get(SOURCE_KEY):
        saved = SavedAttributeEvidence('Malformed')
    custom = stored_tags("custom_tags", "custom_tags")
    fit = project("fit", attrs.get("fit"), _descriptions)
    material = project("material", attrs.get("material"), _descriptions)
    temperature = attrs.get("color_temperature")
    return ConfirmedGarmentSnapshot(
        garment_id=row["id"], user_id=row["user_id"], status=row["status"],
        category=row["category"], name=row["name"], preferred_media_id=row["preferred_media_id"],
        is_favourite=bool(row["is_favourite"]), updated_at=row["updated_at"],
        structural_role=role, layering_index=layer,
        primary_colour=_text(row["primary_colour"]) or _text(attrs.get("primary_colour")) or _text(attrs.get("primary_color")),
        secondary_colour=_text(row["secondary_colour"]), colour_palette=palette,
        style_tags=style,
        pattern=_text(row["pattern"]) or _text(attrs.get("pattern")),
        fit=fit, material=material,
        colour_temperature=temperature if temperature in ("warm", "cool", "neutral") else None,
        is_dominant=attrs.get("is_dominant") if isinstance(attrs.get("is_dominant"), bool) else None,
        custom_tags=custom, invalid_attributes=tuple(invalid), contextual_suitability=contextual, appearance_evidence=appearance,
        saved_attribute_evidence=saved,
    )


class SqliteConfirmedGarmentQuery(ConfirmedGarmentQuery):
    """Keep legacy ID behavior and provide the stronger snapshot contract."""

    def __init__(self, transaction_connection=None):
        self.transaction_connection = transaction_connection

    def _connection(self):
        # Injected connections remain entirely owned by the caller.
        return nullcontext(self.transaction_connection) if self.transaction_connection is not None else connection()

    def list_available_garment_ids(self, user_id: str) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id FROM garments WHERE user_id=? AND status='available' "
                "ORDER BY is_favourite DESC, updated_at DESC, id ASC",
                (user_id,),
            ).fetchall()
        return [str(row["id"]) for row in rows]

    def get_confirmed_available_garments(self, user_id: str) -> tuple[ConfirmedGarmentSnapshot, ...]:
        """Strict confirmation, with processing ownership verified internally."""
        with self._connection() as conn:
            sql = (
                "SELECT g.* FROM garments g "
                "JOIN processing_items p ON p.id=g.processing_item_id "
                "JOIN processing_jobs j ON j.id=p.job_id "
                "WHERE g.user_id=? AND g.status='available' "
                "AND p.review_status='confirmed' AND j.user_id=g.user_id AND j.status='completed' "
            )
            rows = conn.execute(
                sql + " ORDER BY g.is_favourite DESC, g.updated_at DESC, g.id ASC",
                (user_id,),
            ).fetchall()
        return tuple(_snapshot(row) for row in rows)


@lru_cache(maxsize=1)
def get_confirmed_garment_query() -> ConfirmedGarmentQuery:
    return SqliteConfirmedGarmentQuery()
