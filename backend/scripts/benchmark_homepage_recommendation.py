"""Synthetic confirmed SQLite wardrobes; full Homepage backend, no browser/CV."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
from time import perf_counter

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from app.infrastructure.persistence import postgresql_repository as db
from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
from app.application.recommendation.recommendation_engine import RecommendationEngine
from app.application.recommendation.homepage_recommendation_service import HomepageRecommendationService
from app.application.recommendation.reservoir_selector import ReservoirSelector


class TimedSession:
    def __init__(self, wrapped):
        self.wrapped, self.enumeration_seconds = wrapped, 0.0
    @property
    def result(self):
        return self.wrapped.result
    def __iter__(self):
        return self
    def __next__(self):
        start = perf_counter()
        try:
            return next(self.wrapped)
        finally:
            self.enumeration_seconds += perf_counter()-start
    def close(self):
        self.wrapped.close()


class TimedEngine:
    def __init__(self):
        self.wrapped = RecommendationEngine(SqliteConfirmedGarmentQuery())
        self.generator = self.wrapped.generator
    def generate_homepage_candidates(self,user_id):
        self.session = TimedSession(self.wrapped.generate_homepage_candidates(user_id))
        return self.session


def seed(size):
    counts = {'top':int(size*.4),'bottom':int(size*.4),'dress':int(size*.1)}
    counts['outerwear'] = size-sum(counts.values())
    with db.connection() as c:
        c.execute("INSERT INTO users VALUES('benchmark','benchmark@test','','Benchmark','active','now','now')")
        c.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES('job','benchmark','synthetic-media','completed','now','now')")
        for role,category in [('top','vest'),('bottom','trousers'),('dress','vest_dress'),('outerwear','long_sleeve_outwear')]:
            for index in range(counts[role]):
                identifier = f'{role}-{index:06d}'
                c.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'job',?,1,'synthetic-media','synthetic-media','{}','confirmed','now')", (identifier,category))
                c.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,attributes_json,created_at,updated_at) VALUES(?,'benchmark',?,'synthetic-media',?,?,'{}','now','now')", (identifier,identifier,identifier,category))
    return counts


def run(sizes,repeats):
    records = []
    original = db.DATABASE_PATH
    try:
        with tempfile.TemporaryDirectory(prefix='homepage-benchmark-') as directory:
            for size in sizes:
                db.DATABASE_PATH = Path(directory)/f'wardrobe-{size}.db'
                db.initialise_database()
                counts = seed(size)
                expected = (counts['top']*counts['bottom']+counts['dress'])*(1+counts['outerwear'])
                trials = []
                for trial in range(repeats):
                    timing = {}
                    def checkpoint(stage,conn):
                        if stage == 'revalidated':
                            timing['revalidation_and_lock_seconds'] = perf_counter()-timing['write_start']
                    class TimedRepository(SqliteRecommendationRepository):
                        def persist_homepage(self,command):
                            timing['write_start'] = perf_counter()
                            result = super().persist_homepage(command)
                            timing['write_readback_commit_seconds'] = perf_counter()-timing['write_start']-timing['revalidation_and_lock_seconds']
                            return result
                    engine = TimedEngine()
                    repository = TimedRepository(db.DATABASE_PATH,checkpoint)
                    service = HomepageRecommendationService(engine,repository,ReservoirSelector())
                    start = perf_counter()
                    result = service.recommend('benchmark',f'size-{size}-trial-{trial}')
                    elapsed = perf_counter()-start
                    if result['status'] != 'Selected' or not result['complete'] or result['recommendation']['provenance']['candidate_count'] != expected:
                        raise RuntimeError('Incomplete/incorrect benchmark result.')
                    trials.append({'total_seconds':elapsed,**result['timings'],
                        'enumeration_seconds':engine.session.enumeration_seconds,
                        'selection_and_stream_control_seconds':result['timings']['enumeration_selection_seconds']-engine.session.enumeration_seconds,
                        'revalidation_and_lock_seconds':timing['revalidation_and_lock_seconds'],
                        'write_readback_commit_seconds':timing['write_readback_commit_seconds']})
                record = {'garments':size,'role_counts':counts,'candidates':expected,'trials':trials,
                          'median_seconds':statistics.median(t['total_seconds'] for t in trials)}
                records.append(record)
                print(json.dumps(record),flush=True)
    finally:
        db.DATABASE_PATH = original
    sources = [Path(__file__),BACKEND/'app/application/recommendation/homepage_recommendation_service.py',BACKEND/'app/application/recommendation/reservoir_selector.py',BACKEND/'app/infrastructure/persistence/recommendation_repository_adapter.py']
    return {'python':platform.python_version(),'platform':platform.platform(),'logical_cpu_count':os.cpu_count(),
            'source_sha256':{str(p.relative_to(BACKEND)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'method':'Temporary SQLite database per size, synthetic strict-confirmed fixtures, exhaustive generation, production secrets.randbelow reservoir and real revalidation/commit. Three trials by default, no candidate materialization. Enumeration instrumented per next(); residual selection timing includes instrumentation overhead. Fixture creation/migration, HTTP, authentication, CV/media and browser excluded. No browser target claim.',
            'records':records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes',type=int,nargs='+',default=[20,50,100,200])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if len(set(args.sizes)) != len(args.sizes) or min(args.sizes)<10 or args.repeats<1:
        parser.error('Use unique sizes >=10 and positive repeats.')
    result = run(args.sizes,args.repeats)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
