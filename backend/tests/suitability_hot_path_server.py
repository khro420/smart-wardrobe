"""Disposable J8 server; optional byte-frozen J7 numeric facts for baseline only."""
import sys,os,hashlib,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests import evidence_diversity_server as base
app,fixture=base.app,base.fixture
if os.getenv('SMART_WARDROBE_J8_FROZEN_FACTS')=='true':
 path=Path(__file__).parent/'fixtures/invariant_request_reference/compact_scoring_facts.py'
 assert hashlib.sha256(path.read_bytes()).hexdigest()=='612bf357c8f1c27edb6344297f4c45358f23546f212b29ebdedf1a263b7d3128'
 spec=importlib.util.spec_from_file_location('j8_frozen_baseline',path);frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
 import app.application.recommendation.compact_exhaustive_scorer as kernel
 kernel.CompactScoringFacts=frozen.CompactScoringFacts
if __name__=='__main__':
 try:fixture.uvicorn.run(app,host='127.0.0.1',port=3201,access_log=False)
 finally:fixture.temporary.cleanup()
