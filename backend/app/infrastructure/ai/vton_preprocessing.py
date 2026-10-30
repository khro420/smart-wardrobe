"""Stable image preparation and terminal generated-output checks."""
from collections import deque
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


def _transparent_edge_background(image: Image.Image) -> Image.Image:
    """Turn only edge-connected near-white pixels transparent.

    This protects a white garment in the middle of a product image while
    removing the common studio-white background from an otherwise opaque crop.
    """
    pixels = image.load()
    alpha = image.getchannel("A").copy()
    queue = deque()
    seen: set[tuple[int, int]] = set()

    def is_background(x: int, y: int) -> bool:
        red, green, blue, opacity = pixels[x, y]
        return opacity > 0 and min(red, green, blue) >= 240 and max(red, green, blue) - min(red, green, blue) <= 18

    for x in range(image.width):
        queue.extend(((x, 0), (x, image.height - 1)))
    for y in range(1, image.height - 1):
        queue.extend(((0, y), (image.width - 1, y)))
    while queue:
        x, y = queue.popleft()
        if (x, y) in seen or not is_background(x, y):
            continue
        seen.add((x, y))
        alpha.putpixel((x, y), 0)
        for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= next_x < image.width and 0 <= next_y < image.height:
                queue.append((next_x, next_y))
    image.putalpha(alpha)
    return image


def compose_layered_upper_garments(payloads: tuple[bytes, ...]) -> bytes:
    """Make one transparent product reference from an inner layer and outerwear.

    Inputs are centred garment crops. The inner garment is placed slightly
    smaller, then transparent outerwear is placed over it. This preserves the
    selected inner garment through open jacket areas without synthesising a
    person image before the final VTON pass.
    """
    if len(payloads) < 2:
        raise VTONFailure("unprocessable")
    canvas = Image.new("RGBA", (768, 1024), (0, 0, 0, 0))
    for index, payload in enumerate(payloads):
        try:
            with Image.open(BytesIO(payload)) as source:
                has_alpha = source.mode in {"RGBA", "LA"} or "transparency" in source.info
                layer = ImageOps.exif_transpose(source).convert("RGBA")
                if not has_alpha:
                    layer = _transparent_edge_background(layer)
                alpha_box = layer.getchannel("A").getbbox()
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
            raise VTONFailure("unprocessable") from None
        if alpha_box is None:
            raise VTONFailure("unprocessable")
        layer = layer.crop(alpha_box)
        # The jacket sits a little wider than the inner garment. Further
        # outerwear layers remain at this outer size.
        layer.thumbnail((570, 810) if index == 0 else (650, 880), Image.Resampling.LANCZOS)
        canvas.alpha_composite(layer, ((canvas.width - layer.width) // 2, (canvas.height - layer.height) // 2))
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


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
