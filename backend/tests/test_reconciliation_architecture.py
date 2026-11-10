"""Original layering guards plus independent contract/adapter equivalence."""
from tests.retained_evidence import review_path, review_reference
import ast
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest


def test_context_resource_contract_identity_and_frozen_archive_constants():
    from app.shared_contracts import context_bundle as lower
    from app.application.recommendation import context_bundle as compatibility
    assert compatibility is lower
    original=review_path('phase_regression_contract_reconciliation_20261107/frozen-baseline/backend/app/application/recommendation/context_bundle.py')
    tree=ast.parse(original.read_text(encoding='utf-8'))
    frozen={target.id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) for target in n.targets if isinstance(target,ast.Name) and target.id in ('ARCHIVES','ACTIVE_WAVE','LEGACY','EXPANDED')}
    for name,value in frozen.items():assert getattr(lower,name)==value
    assert lower.ContextBundle.load('context_18_v1')==compatibility.ContextBundle.load('context_18_v1')
    assert lower.APP==Path(lower.__file__).parents[1]


@pytest.mark.parametrize('side',['left','right'])
def test_mirror_port_forwards_exact_input_and_same_immutable_result(monkeypatch,side):
    from app.application.ports import workflow_runtime as port
    calls=[];result=SimpleNamespace(png_bytes=b'unchanged-output',seam_side='same',source_size=(2,3),edge_coverage={'edge':0.5})
    def provider(payload,mirrored_side):calls.append((payload,mirrored_side));return result
    monkeypatch.setattr(port,'_runtime',SimpleNamespace(mirror=provider))
    assert port.reconstruct_mirrored_garment_png(b'exact-input',side) is result
    assert calls==[(b'exact-input',side)]


def test_mirror_port_preserves_absence_and_fails_closed_unconfigured(monkeypatch):
    from app.application.ports import workflow_runtime as port
    monkeypatch.setattr(port,'_runtime',SimpleNamespace(mirror=lambda *_:None))
    assert port.reconstruct_mirrored_garment_png(b'empty') is None
    monkeypatch.setattr(port,'_runtime',SimpleNamespace(mirror=None))
    with pytest.raises(RuntimeError):port.reconstruct_mirrored_garment_png(b'empty')
