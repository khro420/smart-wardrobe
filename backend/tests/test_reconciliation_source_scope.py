"""Exact approved descendant and independently rejected authority mutations."""
import copy
import pytest
from tests import integration_source_guard as guard


def test_exact_reconciliation_scope():
    data=guard.reconciliation_manifest()
    assert len(data['replacements'])<=37 and len(data['additions'])<=11
    assert data['default_activation'] is False


@pytest.mark.parametrize('field',['version','scope','activation','before','protected','addition','exception'])
def test_reconciliation_rejects_unapproved_mutations(field):
    data=copy.deepcopy(guard.reconciliation_manifest())
    if field=='version':data['version']='unapproved'
    elif field=='scope':data['scope_sha256']='0'*64
    elif field=='activation':data['default_activation']=True
    elif field=='before':next(iter(data['replacements'].values()))['before']='0'*64
    elif field=='protected':data['files']['backend/app/application/recommendation/preference_scorer.py']='0'*64
    elif field=='addition':data['additions']['backend/app/unapproved.py']='0'*64
    else:data['additional_historical_exceptions']=['unapproved']
    with pytest.raises(AssertionError):guard.validate_reconciliation_manifest(data)


def test_unknown_historical_and_reconciliation_ancestors_are_rejected():
    with pytest.raises(AssertionError):guard.source_hash('app/application/recommendation/preference_scorer.py','0'*64)
    with pytest.raises(AssertionError):guard.reconciliation_digest('backend/tests/integration_source_guard.py','0'*64)
