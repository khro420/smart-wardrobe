"""sRGB -> Oklab, Ottosson 2021 matrices; https://bottosson.github.io/posts/oklab/.

Channels are encoded sRGB, D65. Delta is Euclidean on L/a/b in native units,
not a probability, CSS gamut threshold, or colour-name acceptance threshold.
"""
import math
import re


def normalize_hex(value):
    if not isinstance(value, str):
        raise ValueError("Hex colour must be text.")
    value = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(c * 2 for c in value[1:])
    if not re.fullmatch(r"#[0-9a-f]{6}", value):
        raise ValueError("Expected #RGB or #RRGGBB without alpha.")
    return value


def hex_to_oklab(value):
    value = normalize_hex(value)
    channels = [int(value[i:i+2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    l = (0.4122214708*r + 0.5363325363*g + 0.0514459929*b) ** (1/3)
    m = (0.2119034982*r + 0.6806995451*g + 0.1073969566*b) ** (1/3)
    s = (0.0883024619*r + 0.2817188376*g + 0.6299787005*b) ** (1/3)
    return (0.2104542553*l + 0.7936177850*m - 0.0040720468*s,
            1.9779984951*l - 2.4285922050*m + 0.4505937099*s,
            0.0259040371*l + 0.7827717662*m - 0.8086757660*s)


def oklab_distance(first, second):
    if len(first) != 3 or len(second) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (*first, *second)):
        raise ValueError("Oklab coordinates must be three finite numbers.")
    return math.sqrt(sum((a-b)**2 for a,b in zip(first,second)))
