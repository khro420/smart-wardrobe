"""Versioned newline identity, separate from immutable raw-file provenance.

Only CRLF becomes LF. Whitespace, JSON ordering, BOMs and lone CR bytes are
not rewritten. Existing LF resource digests therefore retain their values.
Historical digests are never passed through this contract during replay.
"""
from dataclasses import dataclass
import hashlib

RESOURCE_CONTRACT = 'crlf-to-lf-sha256-1.0.0'
FINGERPRINT_CONTRACT = 'conversational-grammar-fingerprint-2.0.0'


def canonical_bytes(raw):
    if type(raw) is not bytes:
        raise TypeError('Grammar identity requires bytes.')
    return raw.replace(b'\r\n', b'\n')


@dataclass(frozen=True)
class ResourceIdentity:
    raw_sha256: str
    semantic_sha256: str
    contract: str = RESOURCE_CONTRACT

    @classmethod
    def capture(cls, raw):
        canonical = canonical_bytes(raw)
        return cls(hashlib.sha256(raw).hexdigest(), hashlib.sha256(canonical).hexdigest())


def semantic_fingerprint(parts):
    """Closed caller-owned component order; version separates old raw hashes."""
    return hashlib.sha256(FINGERPRINT_CONTRACT.encode('ascii') + b'\0' + b''.join(
        hashlib.sha256(canonical_bytes(raw)).digest() for raw in parts)).hexdigest()
