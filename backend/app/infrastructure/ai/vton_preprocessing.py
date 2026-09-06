"""Stable image preparation and terminal generated-output checks."""
from io import BytesIO

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

from app.domain.value_objects.generated_visualisation import GeneratedVisualisation, VTONFailure
from app.domain.value_objects.visualisation_plan import VisualisationPlan


def decode_rgb(payload: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(payload)) as source:
            source.verify()
        with Image.open(BytesIO(payload)) as source:
            return ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise VTONFailure("unprocessable") from None


def prepare_person(payload: bytes, size: tuple[int, int]) -> Image.Image:
    image = decode_rgb(payload)
    if min(image.size) < 128 or image.width * image.height > 25_000_000:
        raise VTONFailure("unprocessable")
    return ImageOps.fit(image, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def prepare_garment(payload: bytes, size: tuple[int, int]) -> Image.Image:
    try:
        with Image.open(BytesIO(payload)) as source:
            rgba = source.convert("RGBA")
            white = Image.new("RGBA", rgba.size, "white")
            white.alpha_composite(rgba)
            image = white.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise VTONFailure("unprocessable") from None
    return ImageOps.pad(image, size, Image.Resampling.LANCZOS, color="white", centering=(0.5, 0.5))


def encode_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def validate_generated_output(
    result: GeneratedVisualisation, plan: VisualisationPlan, person_payload: bytes
) -> None:
    try:
        with Image.open(BytesIO(result.image)) as image:
            image.verify()
        with Image.open(BytesIO(result.image)) as image:
            image.load()
            if image.format != "PNG" or image.size != (result.width, result.height):
                raise VTONFailure("invalid_output")
            if image.size != (plan.configuration.width, plan.configuration.height):
                raise VTONFailure("invalid_output")
            if result.output_kind == "generated":
                extrema = image.convert("RGB").getextrema()
                if all(low == high for low, high in extrema):
                    raise VTONFailure("invalid_output")
                person = prepare_person(
                    person_payload, (plan.configuration.width, plan.configuration.height)
                )
                difference = ImageChops.difference(image.convert("RGB"), person)
                if difference.getbbox() is None:
                    raise VTONFailure("invalid_output")
    except VTONFailure:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise VTONFailure("invalid_output") from None
