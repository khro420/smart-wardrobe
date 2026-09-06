from dataclasses import dataclass, field


@dataclass(frozen=True)
class GeneratedVisualisation:
    image: bytes
    width: int
    height: int
    model_version: str
    latency_ms: float
    output_kind: str = "generated"
    content_type: str = "image/png"
    metadata: dict = field(default_factory=dict)
    is_measurement_accurate: bool = False


class VTONFailure(Exception):
    """Allowlisted public error codes; model exception text stays in server logs."""

    MESSAGES = {
        "unavailable": "Try-on is unavailable because the model environment is not ready. Please try again later.",
        "unprocessable": "Use a clear photo of one person with the relevant body region visible, then try again.",
        "invalid_output": "The generated image could not be validated. Please try again or choose another image.",
        "inference_failed": "Try-on could not finish. Please try again or choose another image.",
        "out_of_memory": "There was not enough GPU memory to finish. Please try again when other processing has finished.",
    }

    def __init__(self, code: str):
        self.code = code if code in self.MESSAGES else "inference_failed"
        super().__init__(self.MESSAGES[self.code])
