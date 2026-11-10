"""Compatibility import path for the pinned lower-level context resource contract."""
import sys
from app.shared_contracts import context_bundle as _contract
sys.modules[__name__]=_contract
