"""Immutable, model-independent input snapshot for one visualisation."""
from dataclasses import asdict, dataclass
from typing import Literal

CATEGORY_MODES = {
    "short_sleeve_top": "upper", "long_sleeve_top": "upper", "vest": "upper", "sling": "upper",
    "short_sleeve_outwear": "upper", "long_sleeve_outwear": "upper",
    "shorts": "lower", "trousers": "lower", "skirt": "lower",
    "short_sleeve_dress": "overall", "long_sleeve_dress": "overall",
    "vest_dress": "overall", "sling_dress": "overall",
}
_OUTERWEAR_CATEGORIES = frozenset({"short_sleeve_outwear", "long_sleeve_outwear"})
_LOWER_CATEGORIES = frozenset({"shorts", "trousers", "skirt"})
_BASE_UPPER_CATEGORIES = frozenset({"short_sleeve_top", "long_sleeve_top", "vest", "sling"})
CAPTURE_GUIDANCE = (
    "Use a clear photograph of one person facing the camera, with the relevant "
    "body region visible and no severe occlusion."
)


@dataclass(frozen=True)
class VTONConfiguration:
    width: int = 768
    height: int = 1024
    steps: int = 50
    guidance: float = 2.5
    seed: int = 42
    precision: str = "bf16"
    preprocessing_version: str = "catvton-crop-pad-automask-v1"

    def __post_init__(self):
        if (self.width, self.height) != (768, 1024) or self.precision != "bf16":
            raise ValueError("Only the documented 768x1024 BF16 profile is supported.")
        if not 1 <= self.steps <= 100 or not 0 <= self.guidance <= 10 or not 0 <= self.seed < 2**32:
            raise ValueError("Invalid generation configuration.")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class VisualisationGarment:
    garment_id: str
    source_media_id: str
    category: str
    role: str
    item_order: int


@dataclass(frozen=True)
class VisualisationRenderStep:
    """One VTON pass, retaining the garments used to form its condition image."""

    garments: tuple[VisualisationGarment, ...]
    mode: str
    composition: Literal["single", "layered_upper"] = "single"


@dataclass(frozen=True)
class VisualisationPlan:
    source_type: Literal["outfit", "recommendation"]
    source_id: str
    person_image_id: str
    person_media_id: str
    garments: tuple[VisualisationGarment, ...]
    configuration: VTONConfiguration

    @property
    def render_garments(self) -> tuple[VisualisationGarment, ...]:
        """Return the immutable source garments in deliberate try-on layer order.

        The saved outfit order remains unchanged for display and provenance.  The
        VTON model, however, renders one garment per pass, so base garments are
        applied first, bottoms next, and outerwear last over the upper body.
        """
        def layer_rank(garment: VisualisationGarment) -> int:
            if garment.category in _OUTERWEAR_CATEGORIES or garment.role == "outerwear":
                return 3
            if garment.category in _LOWER_CATEGORIES:
                return 2
            return 1

        return tuple(sorted(self.garments, key=lambda garment: (layer_rank(garment), garment.item_order)))

    @property
    def render_steps(self) -> tuple[VisualisationRenderStep, ...]:
        """Build VTON passes, merging a base top and outerwear into one condition.

        CatVTON uses an entire upper-body mask per upper pass. Passing a shirt
        and jacket separately lets the jacket pass overwrite the shirt. When
        both are present, their transparent product images are composed into
        one upper-garment reference and applied once to the original person.
        """
        ordered = self.render_garments
        base_uppers = tuple(item for item in ordered if item.category in _BASE_UPPER_CATEGORIES)
        outerwear = tuple(
            item for item in ordered
            if item.category in _OUTERWEAR_CATEGORIES or item.role == "outerwear"
        )
        layered = base_uppers + outerwear if base_uppers and outerwear else ()
        steps: list[VisualisationRenderStep] = []
        for item in ordered:
            if item in layered:
                if item is base_uppers[0]:
                    steps.append(VisualisationRenderStep(layered, "upper", "layered_upper"))
                continue
            try:
                steps.append(VisualisationRenderStep((item,), CATEGORY_MODES[item.category]))
            except KeyError:
                raise ValueError(
                    "This garment category is not supported for try-on. "
                    "Choose a confirmed garment from a supported wardrobe category."
                ) from None
        return tuple(steps)

    @property
    def mode(self) -> str:
        try:
            return CATEGORY_MODES[self.garments[0].category]
        except KeyError:
            raise ValueError(
                "This garment category is not supported for try-on. "
                "Choose a confirmed garment from a supported wardrobe category."
            ) from None

    @property
    def modes(self) -> tuple[str, ...]:
        """CatVTON mask modes, one for each ordered outfit layer."""
        if not self.garments:
            raise ValueError("Select an outfit containing at least one garment.")
        modes = []
        for garment in self.garments:
            try:
                modes.append(CATEGORY_MODES[garment.category])
            except KeyError:
                raise ValueError(
                    "This garment category is not supported for try-on. "
                    "Choose a confirmed garment from a supported wardrobe category."
                ) from None
        return tuple(modes)

    @property
    def render_modes(self) -> tuple[str, ...]:
        """VTON modes aligned with :attr:`render_steps`, not source order."""
        return tuple(step.mode for step in self.render_steps)
