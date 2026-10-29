"""Isolated differential/benchmark worker; frozen app imports before live app.

Synthetic fixtures only. No production DB or feature flag changes.
"""
import argparse
import dataclasses
import hashlib
from fractions import Fraction
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile

BACKEND = Path(__file__).resolve().parents[1]
REFERENCE = BACKEND / "tests/fixtures/performance_reference"


def canonical(value):
    if isinstance(value, Fraction):
        return {"fraction": [value.numerator, value.denominator]}
    if dataclasses.is_dataclass(value):
        return {f.name: canonical(getattr(value, f.name)) for f in dataclasses.fields(value)
                if f.name not in ("context_id", "_seal")}
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    return value


def run(args, directory):
    global REFERENCE
    if args.reference:
        REFERENCE = args.reference
    frozen = Path(directory) / "reference"
    with zipfile.ZipFile(REFERENCE / "app.zip") as archive:
        manifest = json.loads((REFERENCE / "manifest.json").read_text())
        if set(archive.namelist()) != set(manifest) or any(hashlib.sha256(archive.read(name)).hexdigest() != digest for name,digest in manifest.items()):
            raise RuntimeError("Frozen reference integrity failure")
        archive.extractall(frozen)
    sys.path.insert(0, str(BACKEND))
    sys.path.insert(0, str(frozen if args.variant == "original" else BACKEND))
    os.environ.update(SMART_WARDROBE_DATA_DIR=directory,
                      SMART_WARDROBE_DATABASE=str(Path(directory) / "test.db"),
                      SMART_WARDROBE_VTOFF_ENABLED="off")
    import app.application.recommendation.recommendation_scorer as scoring
    from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
    from app.application.recommendation.recommendation_engine import RecommendationEngine
    from app.application.recommendation.candidate_generator import CandidateGenerator
    from app.application.recommendation.request_constraint_evaluator import RequestConstraintEvaluator
    from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
    from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
    from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest, GarmentCategoryConstraint
    from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
    from app.domain.value_objects.recommendation_score import ScoreEvidence, ComponentScore

    def reference_module(name):
        spec = importlib.util.spec_from_file_location("reference_" + name,
            frozen / "app/application/recommendation" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if name == "compatibility_scorer":
            module.ProfileUnavailable = scoring.ProfileUnavailable
        return module

    if args.variant in ("request", "preference", "prepared"):
        if args.variant == "preference":
            scoring.RequestMatchScorer = reference_module("request_match_scorer").RequestMatchScorer
        if args.variant == "request":
            scoring.PreferenceScorer = reference_module("preference_scorer").PreferenceScorer
        scoring.ExactScoreReuse.enabled = False
    elif args.variant not in ("original", "combined"):
        old_ranker = reference_module("candidate_ranker").CandidateRanker
        old_preferences = reference_module("preference_scorer").PreferenceScorer
        old_compatibility = reference_module("compatibility_scorer").CompatibilityScorer
        new_preferences = scoring.PreferenceScorer
        if args.variant != "key":
            scoring.CandidateRanker = old_ranker
        if args.variant == "key":
            scoring.PreferenceScorer = old_preferences
            scoring.CompatibilityScorer = old_compatibility
        elif args.variant == "preferences":
            class PreparedOnly(new_preferences):
                def score(self, verified, preferences):
                    if not preferences.preferences:
                        return old_preferences.score(self, verified, preferences)
                    return super().score(verified, preferences)
            scoring.PreferenceScorer = PreparedOnly
            scoring.CompatibilityScorer = old_compatibility
        elif args.variant == "constants":
            class ConstantsOnly(new_preferences):
                def score(self, verified, preferences):
                    if preferences.preferences:
                        return old_preferences.score(self, verified, preferences)
                    return super().score(verified, preferences)
            scoring.PreferenceScorer = ConstantsOnly

    class Query:
        def __init__(self, rows): self.rows = rows
        def get_confirmed_available_garments(self, user_id): return self.rows

    class Preferences:
        def __init__(self, rows): self.rows = rows
        def get_active_preferences(self, user_id): return self.rows

    class Digest(list):
        """Bounded-memory ordered transcript of every mandatory/score event."""
        def clear(self):
            self.hasher, self.events = hashlib.sha256(), 0
        def append(self, value):
            self.hasher.update(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
            self.hasher.update(b"\n")
            self.events += 1
        def result(self):
            return {"sha256": self.hasher.hexdigest(), "events": self.events}
    trace = Digest() if args.digest else []
    # Separate channel: historical mandatory/score fingerprints stay unchanged.
    progress = Digest() if args.progress_digest else []
    if args.progress or args.progress_digest:
        from app.domain.value_objects.candidate_generation_result import CandidateGenerationResult
        from app.domain.value_objects.request_candidate_evaluation import RequestGenerationResult
        for cls in (CandidateGenerationResult, RequestGenerationResult):
            original = cls.__post_init__
            def validated(self, _original=original, _name=cls.__name__):
                _original(self)
                progress.append({"type": _name, "result": canonical(self)})
            cls.__post_init__ = validated
        from app.application.recommendation.recommendation_engine import CandidateGenerationSession
        from app.application.recommendation.request_candidate_session import RequestCandidateSession
        for cls in (CandidateGenerationSession, RequestCandidateSession):
            original_next = cls.__next__
            def yielded(self, _next=original_next, _name=cls.__name__):
                value = _next(self)
                candidate = getattr(value, "candidate", value)
                progress.append({"yield": _name, "result": canonical(self.result),
                                 "key": canonical(candidate.key)})
                return value
            cls.__next__ = yielded
    retained = {}
    if args.diagnostics:
        # Separate instrumentation runs only; never used as latency evidence.
        for name in ("RequestMatchScorer", "PreferenceScorer", "ExactScoreReuse"):
            if not hasattr(scoring, name):
                continue
            cls = getattr(scoring, name)
            def capture(*positional, _cls=cls, _name=name, **keywords):
                instance = _cls(*positional, **keywords)
                retained[_name] = instance
                return instance
            setattr(scoring, name, capture)

    def diagnostics():
        seen = set()
        def deep_size(value):
            if id(value) in seen:
                return 0
            seen.add(id(value))
            result = sys.getsizeof(value)
            if isinstance(value, dict):
                result += sum(deep_size(k)+deep_size(v) for k,v in value.items())
            elif isinstance(value, (tuple,list,set,frozenset)):
                result += sum(deep_size(v) for v in value)
            elif hasattr(value,"__dict__") and not isinstance(value,type):
                result += deep_size(vars(value))
            return result
        result = {}
        for name,instance in retained.items():
            result[name] = {"retained_bytes": deep_size(instance),
                "counters": {k:v for k,v in vars(instance).items() if k.endswith(("hits","misses"))},
                "collections": {k:len(v) for k,v in vars(instance).items() if isinstance(v,dict)}}
            for key,cache in vars(instance).items():
                if hasattr(cache,"cache_info"):
                    result[name][key] = cache.cache_info()._asdict()
                if key == "_reuse":
                    result[name][key] = {n:c.cache_info()._asdict() for n,c in vars(cache).items()
                        if n.startswith("_") and hasattr(c,"cache_info")}
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            class Counters(ctypes.Structure):
                _fields_ = [("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD)] + [(n,ctypes.c_size_t) for n in
                    ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage",
                     "QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
            counters = Counters(); counters.cb = ctypes.sizeof(counters)
            kernel = ctypes.windll.kernel32
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
            get_memory.argtypes = (wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD)
            get_memory.restype = wintypes.BOOL
            if get_memory(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
                result["peak_working_set_bytes"] = counters.PeakWorkingSetSize
        return result
    original_evaluate = RequestConstraintEvaluator.evaluate
    original_scored = scoring.ScoredCandidate
    if args.trace or args.digest:
        def evaluate(self, candidate, request):
            decision = original_evaluate(self, candidate, request)
            trace.append({"mandatory": canonical(decision), "key": canonical(candidate.key)})
            return decision
        RequestConstraintEvaluator.evaluate = evaluate
        def scored(verified, score):
            item = original_scored(verified, score)
            assert verified.user_id == "owner" and verified.context_id
            trace.append({"scored": canonical(item)})
            return item
        scoring.ScoredCandidate = scored

    fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
    results = []
    for fixture in fixtures:
        trace.clear()
        progress.clear()
        rows = [ConfirmedGarmentSnapshot(**row) for row in fixture["garments"]]
        repository = None
        if fixture.get("persist") or fixture.get("service"):
            from app.infrastructure.persistence import postgresql_repository as db
            from app.infrastructure.persistence.confirmed_garment_query_adapter import SqliteConfirmedGarmentQuery
            from app.infrastructure.persistence.recommendation_repository_adapter import SqliteRecommendationRepository
            db.initialise_database()
            with db.connection() as conn:
                conn.execute("INSERT INTO users VALUES('owner','synthetic@example.test','','Synthetic','active','time','time')")
                conn.execute("INSERT INTO processing_jobs(id,user_id,source_media_id,status,created_at,updated_at) VALUES('job','owner','synthetic-media','completed','time','time')")
                for row in rows:
                    conn.execute("INSERT INTO processing_items(id,job_id,detected_category,confidence,crop_media_id,preferred_media_id,attributes_json,review_status,created_at) VALUES(?,'job',?,1,'synthetic-media','synthetic-media','{}','confirmed','time')", (row.garment_id,row.category))
                    conn.execute("INSERT INTO garments(id,user_id,processing_item_id,preferred_media_id,name,category,attributes_json,primary_colour,style_tags,created_at,updated_at) VALUES(?,'owner',?,'synthetic-media',?,?,'{}',?,?,'time','time')", (row.garment_id,row.garment_id,row.name,row.category,row.primary_colour,json.dumps(row.style_tags)))
            rows = SqliteConfirmedGarmentQuery().get_confirmed_available_garments("owner")
            repository = SqliteRecommendationRepository(db.DATABASE_PATH)
        data = dict(fixture.get("request", {}))
        if data.get("garment_categories"):
            data["garment_categories"] = tuple(GarmentCategoryConstraint(**c) for c in data["garment_categories"])
        request = StructuredOutfitRequest(**data)
        preferences = tuple(PreferenceSnapshot(**row) for row in fixture.get("preferences", []))
        fault = fixture.get("fault")
        class Generator(CandidateGenerator):
            def enumerate(self, garments, evaluator):
                if fault == "early": raise RuntimeError("synthetic early failure")
                yield from super().enumerate(garments, evaluator)
                if fault == "late": raise RuntimeError("synthetic late failure")
                if fault == "interrupt": raise KeyboardInterrupt()
                if fault == "generator_exit": raise GeneratorExit()
        factory = SuitabilityRequestEvaluator if fixture.get("suitability") else RequestConstraintEvaluator
        engine = RequestCandidateEngine(structural_engine=RecommendationEngine(Query(rows), generator=Generator()), evaluator_factory=factory)
        original_generate = engine.generate_candidates
        sessions = []
        def generate(user_id, current_request):
            session = original_generate(user_id, current_request)
            if fault == "incomplete":
                from app.application.recommendation.request_candidate_session import RequestCandidateSession
                class Incomplete(RequestCandidateSession):
                    def __next__(self): raise StopIteration
                session = Incomplete(session.structural_session, session.request, session.evaluator)
            if fault == "tampered":
                from app.domain.value_objects.request_candidate_evaluation import RequestEvaluation
                session.evaluator.evaluate = lambda *_: RequestEvaluation(())
            sessions.append(session)
            if fault == "close":
                def close(): raise RuntimeError("synthetic close failure")
                session.close = close
            return session
        engine.generate_candidates = generate
        runner = scoring.RecommendationScorer(engine, Preferences(preferences))
        samples = []
        profile = fixture.get("profile", "compatibility_deferred")
        if fixture.get("service"):
            from app.application.nlp.nlp_interpreter import NLPInterpreter
            from app.application.recommendation.outfit_assistant_service import OutfitAssistantService
            service = OutfitAssistantService(NLPInterpreter(), RequestCandidateEngine(SqliteConfirmedGarmentQuery()),
                                             Preferences(preferences), repository)
            # This retained hot-path oracle instruments reference scorer methods.
            # Older frozen services predate this selector; keep both arms on the
            # same reference implementation rather than silently tracing compact.
            if hasattr(service, "execution_engine"):
                service.execution_engine = "reference"
            for index in range(-args.warmups, args.repeats):
                wall, cpu = time.perf_counter(), time.process_time()
                value = service.recommend("owner", "synthetic-" + str(index + args.warmups), "Suggest an outfit with vintage style")
                elapsed, used = time.perf_counter()-wall, time.process_time()-cpu
                if value["status"] != "Selected" or not value["complete"] or value["replayed"]:
                    raise RuntimeError("Incomplete or replayed benchmark")
                if index >= 0: samples.append({"wall": elapsed, "cpu": used, "stages": value["timings"]})
            record = {"name": fixture["name"], "timings": samples,
                "scored_count": value["provenance"]["scored_count"],
                "winner": [(item["garment_id"], item["garment_role"], item["item_order"]) for item in value["items"]],
                "score_metadata": value["score_metadata"]}
            if args.digest: record["transcript"] = trace.result()
            if args.progress or args.progress_digest:
                record["progress"] = progress.result() if args.progress_digest else list(progress)
            if args.diagnostics: record["cache_diagnostics"] = diagnostics()
            results.append(record)
            continue
        # Benchmarks use fresh sessions/scorers/caches for every timed interaction.
        for index in range(-args.warmups, args.repeats):
            runner = scoring.RecommendationScorer(engine, Preferences(preferences))
            wall, cpu = time.perf_counter(), time.process_time()
            outcome = runner.rank("owner", request, profile)
            elapsed, used = time.perf_counter() - wall, time.process_time() - cpu
            if index >= 0: samples.append({"wall": elapsed, "cpu": used})
        result = {"name": fixture["name"], "outcome": canonical(outcome),
                  "session": canonical(sessions[-1].result), "trace": list(trace) if args.trace else [],
                  "timings": samples}
        if args.digest: result["transcript"] = trace.result()
        if args.progress or args.progress_digest:
            result["progress"] = progress.result() if args.progress_digest else list(progress)
        if args.diagnostics: result["cache_diagnostics"] = diagnostics()
        if repository is not None:
            from app.domain.value_objects.recommendation_persistence import RecommendationWrite
            winner = outcome.winner
            command = RecommendationWrite("owner", "assistant", "synthetic-submission", json.dumps(dataclasses.asdict(request)),
                winner.verified.candidate, '{"synthetic":true}', "Synthetic outfit request", winner.score)
            record, replay = repository.persist_assistant(command)
            second, replayed = repository.persist_assistant(command)
            assert not replay and replayed and record["id"] == second["id"]
            result["persisted"] = {k: canonical(record[k]) for k in ("user_id", "items", "score_metadata", "provenance")}
            with db.connection() as conn:
                result["persisted"]["counts"] = [conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                    for table in ("recommendations", "recommendation_items", "nlp_chats")]
        results.append(result)
    args.output.write_text(json.dumps(results, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("original", "key", "preferences", "constants", "combined", "request", "preference", "prepared"), required=True)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--diagnostics", action="store_true")
    progress_options = parser.add_mutually_exclusive_group()
    progress_options.add_argument("--progress", action="store_true")
    progress_options.add_argument("--progress-digest", action="store_true")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    tracing = parser.add_mutually_exclusive_group()
    tracing.add_argument("--trace", action="store_true")
    tracing.add_argument("--digest", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--warmups", type=int, default=0)
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="assistant-equivalence-") as temporary:
        run(options, temporary)
