"""Instance-restricted CatVTON processing for separate people in a photo."""
from io import BytesIO
from math import ceil

from PIL import Image, ImageChops, ImageFilter, ImageOps

from app.infrastructure.ai.group_vton_geometry import PersonCrop
from app.infrastructure.ai.vton_preprocessing import encode_png


def feather_edit_mask(mask, person_mask):
    """Soften the inner edge while keeping protected pixels exactly intact."""
    allowed = ImageChops.darker(mask.convert("L"), person_mask.convert("L"))
    bounds = allowed.getbbox()
    if bounds is None:
        return allowed
    radius = min(3.0, max(0.5, (bounds[2] - bounds[0]) * 0.008))
    return ImageChops.darker(allowed, allowed.filter(ImageFilter.GaussianBlur(radius)))


def crop_for_person(bounds, image_size):
    left, top, right, bottom = bounds
    width, height = image_size
    minimum = ceil(max((right - left) / 3, (bottom - top) / 4))
    maximum_unpadded = min(width // 3, height // 4)
    desired = ceil(minimum * 1.15)
    # Avoid unnecessary padding: reducing a small person within the model's
    # fixed input can make garment details and the clothing parser less reliable.
    units = min(maximum_unpadded, desired) if minimum <= maximum_unpadded else desired
    crop_width, crop_height = 3 * units, 4 * units
    x = max(0, min(width - crop_width, (left + right - crop_width) // 2)) if crop_width <= width else (width - crop_width) // 2
    y = max(0, min(height - crop_height, (top + bottom - crop_height) // 2)) if crop_height <= height else (height - crop_height) // 2
    return PersonCrop((x, y, x + crop_width, y + crop_height))


def render_group(payload, people, assignments, adapter, progress_callback=None):
    """Return a composite; assignments contain (person index, plan, garments)."""
    with Image.open(BytesIO(payload)) as source:
        original = ImageOps.exif_transpose(source).convert("RGB")
    if not 1 <= len(assignments) <= 2:
        raise ValueError("Choose one or two people.")
    indices = [item[0] for item in assignments]
    if len(set(indices)) != len(indices) or any(i < 0 or i >= len(people) for i in indices):
        raise ValueError("Invalid person selection.")
    # Ambiguous overlap can cause foreground people to be overwritten.
    for i, person in enumerate(people):
        if person.mask.size != original.size:
            raise ValueError("Person mask dimensions do not match the photo.")
        for other in people[i + 1:]:
            if ImageChops.multiply(person.mask, other.mask).getbbox():
                raise ValueError("People overlap. Choose a photo with more separation.")
    if not hasattr(adapter, "generate_for_person"):
        raise ValueError("A real CatVTON model is required for group try-on.")
    output = original.copy()
    for number, (index, plan, garments) in enumerate(assignments):
        person = people[index]
        crop = crop_for_person(person.box, original.size)
        # A neighbouring wearer in the crop can mislead the single-person
        # clothing parser. Hide their unambiguous pixels for inference only;
        # compositing still starts from the untouched original photograph.
        isolated = original.copy()
        neighbours = Image.new("L", original.size)
        for other_index, other in enumerate(people):
            if other_index != index:
                neighbours = ImageChops.lighter(neighbours, other.mask)
        isolated.paste((240, 240, 240), mask=neighbours)
        person_image = crop.extract(isolated)
        mask = person.mask.crop(crop.box).resize(crop.size, Image.Resampling.NEAREST)
        def report(current, total, phase):
            if progress_callback:
                progress_callback(number, len(assignments), current, total, phase)
        generated, edit_mask = adapter.generate_for_person(plan, encode_png(person_image), garments, mask, report)
        if generated.output_kind != "generated":
            raise ValueError("Group try-on requires generated output.")
        with Image.open(BytesIO(generated.image)) as rendered:
            if rendered.size != crop.size or edit_mask.size != crop.size or not edit_mask.getbbox():
                raise ValueError("Invalid generated person image or edit mask.")
            rgb = rendered.convert('RGB')
            channels = ImageChops.difference(rgb, person_image).split()
            difference = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            permitted_edit = ImageChops.darker(edit_mask.convert('L'), mask)
            changed = ImageChops.darker(difference, permitted_edit)
            if all(low == high for low, high in rgb.getextrema()) or not changed.getbbox():
                raise ValueError("The model did not produce a usable preview.")
            local_mask = permitted_edit.resize((crop.box[2] - crop.box[0], crop.box[3] - crop.box[1]), Image.Resampling.NEAREST)
            full_mask = Image.new("L", original.size)
            full_mask.paste(local_mask, crop.box[:2])
            full_mask = feather_edit_mask(full_mask, person.mask)
            output = crop.composite(output, rendered, full_mask)
    return encode_png(output)
