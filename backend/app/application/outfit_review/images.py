"""Non-persisting reuse of Student 1 EXIF/RGB decoding, with bounded inputs."""
from hashlib import sha256
from io import BytesIO
import warnings
from PIL import Image, JpegImagePlugin, PngImagePlugin
from app.infrastructure.ai.vton_preprocessing import decode_rgb
from .contract import ImageIdentity


def prepare_image(payload: bytes) -> tuple[ImageIdentity, bytes]:
    """Return oriented PNG for inference/preview and coordinate-bound identity.

    Does not call store_image/store_media_bytes, register garments, or open a DB.
    Protected-media ownership remains the future calling endpoint's obligation.
    """
    if not isinstance(payload, bytes) or not 0 < len(payload) <= 20 * 1024 * 1024:
        raise ValueError("Image must be bounded JPEG/PNG bytes")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        if payload.startswith(b"\x89PNG\r\n\x1a\n"):
            decoder = PngImagePlugin.PngImageFile
        elif payload.startswith(b"\xff\xd8"):
            decoder = JpegImagePlugin.JpegImageFile
        else:
            raise ValueError("JPEG/PNG required")
        with decoder(BytesIO(payload)) as header:
            if min(header.size) < 128 or header.width * header.height > 25_000_000:
                raise ValueError("Image dimensions outside review bounds")
            header.verify()
        image = decode_rgb(payload)
    encoded = BytesIO()
    image.save(encoded, format="PNG")
    pixels = str(image.size).encode("ascii") + b"\0RGB\0" + image.tobytes()
    identity = ImageIdentity(original_sha256=sha256(payload).hexdigest(), oriented_pixels_sha256=sha256(pixels).hexdigest(), width=image.width, height=image.height)
    return identity, encoded.getvalue()
