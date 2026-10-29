"""Validate original text and normalize only a separate matching copy."""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class PreprocessedRequest:
    original: str
    normalized: str


class InvalidRequestText(ValueError):
    pass


class RequestPreprocessor:
    def __init__(self, max_length: int = 500):
        self.max_length = max_length

    def preprocess(self, request_text: object) -> PreprocessedRequest:
        if not isinstance(request_text, str):
            raise InvalidRequestText("Request must be text.")
        if not request_text.strip():
            raise InvalidRequestText("Enter an outfit request.")
        if len(request_text) > self.max_length:
            raise InvalidRequestText(f"Shorten your request to {self.max_length} characters.")
        text = unicodedata.normalize("NFKC", request_text).casefold()
        text = text.replace("’", "'")
        text = re.sub(r"[-‐‑–—_]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return PreprocessedRequest(request_text, text)
