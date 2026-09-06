"""Private media validation and opaque-storage service."""

from io import BytesIO
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, JpegImagePlugin, PngImagePlugin, UnidentifiedImageError

from app.infrastructure.config import MAX_IMAGE_BYTES, MEDIA_DIR, MIN_IMAGE_DIMENSION, ORPHAN_MEDIA_RETENTION_HOURS
from app.infrastructure.persistence.postgresql_repository import connection, utcnow


ALLOWED_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}


def _decode_supported_image(payload: bytes):
    # Use the supported decoders directly. Some model libraries replace
    # Image.open globally with an opener that installs HEIF support on failure.
    # Upload validation must stay deterministic and must never install software.
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return PngImagePlugin.PngImageFile(BytesIO(payload))
    if payload.startswith(b"\xff\xd8"):
        return JpegImagePlugin.JpegImageFile(BytesIO(payload))
    if payload.startswith((b"GIF87a", b"GIF89a", b"RIFF", b"II*\x00", b"MM\x00*")):
        raise HTTPException(415, "The decoded image must be JPEG or PNG.")
    raise UnidentifiedImageError("No supported image signature.")


async def store_image(upload: UploadFile, user_id: str, media_type: str) -> str:
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, "Only JPEG and PNG images are supported.")
    payload = await upload.read(MAX_IMAGE_BYTES + 1)
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"Image must be between 1 byte and {MAX_IMAGE_BYTES // 1024 // 1024} MB.")
    try:
        image = _decode_supported_image(payload)
        if image.format not in {"JPEG", "PNG"}:
            raise HTTPException(415, "The decoded image must be JPEG or PNG.")
        if ("image/png" if image.format == "PNG" else "image/jpeg") != upload.content_type:
            raise HTTPException(415, "The image format does not match its declared content type.")
        image.verify()
        image = _decode_supported_image(payload)
        if image.width * image.height > 25_000_000:
            raise HTTPException(422, "Image resolution must not exceed 25 megapixels.")
        image.load()
        if min(image.size) < MIN_IMAGE_DIMENSION:
            raise HTTPException(422, f"Image must be at least {MIN_IMAGE_DIMENSION}px on each side.")
        # Normalise orientation before inference and remove private EXIF metadata.
        normalised = ImageOps.exif_transpose(image).convert("RGB")
        encoded = BytesIO()
        normalised.save(encoded, format="PNG" if upload.content_type == "image/png" else "JPEG")
        payload = encoded.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "The uploaded file could not be decoded as an image.") from exc

    return store_media_bytes(payload, user_id, media_type, upload.content_type, upload.filename)


def store_media_bytes(payload: bytes, user_id: str, media_type: str, content_type: str = "image/png", original_filename: str | None = None) -> str:
    """Persist trusted, internally encoded media with the same ownership boundary."""
    media_id, storage_key = str(uuid.uuid4()), f"{uuid.uuid4()}{ALLOWED_CONTENT_TYPES[content_type]}"
    with _decode_supported_image(payload) as image:
        width, height = image.size
    target = MEDIA_DIR / storage_key
    target.write_bytes(payload)
    try:
        with connection() as conn:
            conn.execute(
                "INSERT INTO media_assets (id, user_id, media_type, storage_key, content_type, size_bytes, status, created_at, width, height, original_filename) VALUES (?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?)",
                (media_id, user_id, media_type, storage_key, content_type, len(payload), utcnow(), width, height, original_filename),
            )
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return media_id


def media_path_for_owner(media_id: str, user_id: str) -> tuple[Path, str]:
    with connection() as conn:
        row = conn.execute(
            "SELECT storage_key, content_type FROM media_assets WHERE id = ? AND user_id = ? AND status = 'available'",
            (media_id, user_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Media asset was not found.")
    path = MEDIA_DIR / row["storage_key"]
    if not path.exists():
        raise HTTPException(404, "Media asset is unavailable.")
    return path, row["content_type"]


def copy_as_media(source_media_id: str, user_id: str, media_type: str) -> str:
    source, content_type = media_path_for_owner(source_media_id, user_id)
    return store_media_bytes(source.read_bytes(), user_id, media_type, content_type)


def find_orphaned_media(retention_hours: int = ORPHAN_MEDIA_RETENTION_HOURS) -> list[dict]:
    """Return aged media that no persisted workflow record still references.

    Processing can create crops, masks, and VTOFF intermediates immediately before
    a user cancels a job.  We retain those private files for a short grace period
    to support investigation/retry, then make them eligible for explicit cleanup.
    """
    if retention_hours < 0:
        raise ValueError("retention_hours must be zero or greater")
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=retention_hours)).isoformat()
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.storage_key, m.media_type, m.created_at
            FROM media_assets AS m
            WHERE m.status = 'available' AND m.created_at < ?
              AND NOT EXISTS (SELECT 1 FROM processing_jobs p WHERE p.source_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM processing_items p WHERE p.crop_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM processing_items p WHERE p.mask_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM processing_items p WHERE p.vtoff_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM processing_items p WHERE p.preferred_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM garments g WHERE g.preferred_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM person_images p WHERE p.media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM visualisations v WHERE v.output_media_id = m.id)
              AND NOT EXISTS (SELECT 1 FROM visualisation_items v WHERE v.source_media_id = m.id)
            ORDER BY m.created_at
            """,
            (cutoff,),
        ).fetchall()
    return [dict(row) for row in rows]


def purge_orphaned_media(retention_hours: int = ORPHAN_MEDIA_RETENTION_HOURS, *, dry_run: bool = True) -> list[dict]:
    """Archive aged unreferenced media, deleting files only when explicitly applied.

    The default dry-run makes scheduled/administrative use auditable.  Metadata is
    retained with status ``archived`` after application, so a cleanup run never
    silently loses the record that a file existed.
    """
    candidates = find_orphaned_media(retention_hours)
    if dry_run:
        return candidates
    for media in candidates:
        (MEDIA_DIR / media["storage_key"]).unlink(missing_ok=True)
    if candidates:
        with connection() as conn:
            conn.executemany("UPDATE media_assets SET status='archived' WHERE id=? AND status='available'", [(media["id"],) for media in candidates])
    return candidates
