"""Offline compatibility audit and streaming profile sensitivity; no live writes.

Captured evaluation wardrobes are offline fixtures, not proof of current Phase 1
confirmation. Runtime recommendations must still use the genuine injected query.
"""
import argparse
import json
from pathlib import Path
import platform
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.application.recommendation.compatibility_reference_policy import CompatibilityReferencePolicy,DEFAULT_REFERENCES,artifact_hash
from app.application.recommendation.holistic_scoring_profile import DEFAULT_HOLISTIC_PROFILES
from app.application.recommendation.holistic_recommendation_scorer import HolisticRecommendationScorer
from app.application.recommendation.request_candidate_engine import RequestCandidateEngine
from app.application.recommendation.suitability_request_evaluator import SuitabilityRequestEvaluator
from app.shared_contracts.confirmed_garment_query import ConfirmedGarmentQuery
from app.shared_contracts.confirmed_garment_snapshot import ConfirmedGarmentSnapshot
from app.application.ports.active_preference_query import ActivePreferenceQuery
from app.domain.value_objects.preference_snapshot import PreferenceSnapshot
from app.domain.value_objects.structured_outfit_request import StructuredOutfitRequest,GarmentCategoryConstraint
from app.domain.value_objects.compatibility_signature import STRUCTURES


class OfflineWardrobe(ConfirmedGarmentQuery):
    def __init__(self,rows): self.rows = tuple(rows)
    def get_confirmed_available_garments(self,user_id): return tuple(x for x in self.rows if x.user_id == user_id and x.status == "available")
    def list_available_garment_ids(self,user_id): return [x.garment_id for x in self.get_confirmed_available_garments(user_id)]


class OfflinePreferences(ActivePreferenceQuery):
    def __init__(self,rows): self.rows = tuple(rows)
    def get_active_preferences(self,user_id): return tuple(x for x in self.rows if x.user_id == user_id and x.is_active)


def load_cases(path,allow_synthetic,policy):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw,dict) or raw.get("schema_version") != "1.0.0" or not isinstance(raw.get("version"),str) or not raw["version"] or raw.get("validation_locked") is not True or not isinstance(raw.get("cases"),list):
        raise ValueError("Versioned cases and a locked-validation declaration are required.")
    synthetic = raw.get("kind") == "synthetic_fixture"
    if raw.get("kind") not in ("synthetic_fixture","held_out_review_dataset") or (synthetic and not allow_synthetic) or (policy.synthetic and not synthetic):
        raise ValueError("Synthetic fixtures require explicit opt-in and cannot claim real validation.")
    ids,source_partitions = set(),{}
    reference_sources = {source for item in policy.references for source in item.source_ids}
    for item in raw["cases"]:
        if not isinstance(item,dict) or not isinstance(item.get("case_id"),str) or not item["case_id"] or item["case_id"] in ids or item.get("partition") not in ("development","validation"):
            raise ValueError("Invalid/duplicate case ID or partition.")
        ids.add(item["case_id"])
        sources = item.get("source_ids")
        if not isinstance(sources,list) or not sources or any(not isinstance(x,str) or not x for x in sources):
            raise ValueError("Evaluation source identifiers required.")
        if item["partition"] == "validation" and set(sources)&reference_sources:
            raise ValueError("Validation source overlaps reviewed-reference sources.")
        for source in sources:
            if source in source_partitions and source_partitions[source] != item["partition"]:
                raise ValueError("Source leakage across development/validation partitions.")
            source_partitions[source] = item["partition"]
        if not isinstance(item.get("user_id"),str) or not item["user_id"] or not isinstance(item.get("wardrobe"),list) or not isinstance(item.get("request"),dict) or not isinstance(item.get("preferences",[]),list):
            raise ValueError("Malformed offline evaluation inputs.")
    return raw,synthetic


def evaluate(reference_path=DEFAULT_REFERENCES,case_path=None,profile_path=DEFAULT_HOLISTIC_PROFILES,profiles=("holistic_experimental",),partition="development",allow_synthetic=False):
    policy = CompatibilityReferencePolicy.load(reference_path,allow_synthetic)
    report = {"reference_version":policy.version,"reference_hash":policy.hash,"synthetic_references":policy.synthetic,
              "approved_reference_count":len(policy.approved),"approved_references_by_structure":{name:sum(x.signature.structure == name for x in policy.approved.values()) for name in STRUCTURES},
              "profile_hash":artifact_hash(json.loads(Path(profile_path).read_text())),"python":platform.python_version(),
              "activation_approved":False,"independent_validation_complete":False,"fashion_accuracy":None,"cases":[]}
    if case_path is None:
        report.update({"evaluated_case_count":0,"candidate_coverage":None,"limitations":["Reference configuration audit only; no reviewed outfit evaluation dataset supplied."]})
        return report
    raw,synthetic = load_cases(case_path,allow_synthetic,policy)
    if partition not in ("development","validation"):
        raise ValueError("Choose an explicit evaluation partition.")
    report.update({"dataset_version":raw["version"],"dataset_hash":artifact_hash(raw),"partition":partition,"synthetic_cases":synthetic})
    selected = sorted((x for x in raw["cases"] if x["partition"] == partition),key=lambda x:x["case_id"])
    for item in selected:
        fields = dict(item["request"])
        if fields.get("garment_categories") is not None:
            fields["garment_categories"] = tuple(GarmentCategoryConstraint(**x) for x in fields["garment_categories"])
        request = StructuredOutfitRequest(**fields)
        rows = tuple(ConfirmedGarmentSnapshot(**x) for x in item["wardrobe"])
        preferences = tuple(PreferenceSnapshot(**x) for x in item.get("preferences",[]))
        results = []
        for name in profiles:
            # Recreate session/cache for each explicitly selected fixed profile.
            engine = RequestCandidateEngine(OfflineWardrobe(rows),evaluator_factory=SuitabilityRequestEvaluator)
            outcome = HolisticRecommendationScorer(engine,OfflinePreferences(preferences),policy,profile_path,allow_synthetic).rank(item["user_id"],request,name)
            winner = outcome.winner
            coverage = {s:{"examined":0,"reviewed":0,"unknown":0,"unavailable":0,"incomplete":0} for s in STRUCTURES}
            for code,value in outcome.diagnostics:
                if code.startswith("coverage:"):
                    key,count = value.split("=")
                    coverage[code.split(":",1)[1]][key] = int(count)
            for counts in coverage.values():
                counts["reviewed_fraction"] = counts["reviewed"]/counts["examined"] if counts["examined"] and outcome.complete else None
            results.append({"profile":name,"status":outcome.status,"complete":outcome.complete,"scored_count":outcome.scored_count,
                            "winner_key":winner.verified.candidate.key if winner else None,"total_exact":str(winner.score.total) if winner else None,
                            "components_exact":[str(x.contribution) for x in (winner.score.request_match,winner.score.compatibility,winner.score.preference)] if winner else None,
                            "coverage_by_structure":coverage})
        winners = {json.dumps(x["winner_key"]) for x in results if x["status"] == "Selected"}
        report["cases"].append({"case_id":item["case_id"],"results":results,"winner_changes_across_profiles":len(winners)>1})
    report.update({"evaluated_case_count":len(selected),"limitations":["Exact synthetic/metadata policy diagnostics are not independent fashion-compatibility accuracy.","Source IDs and review provenance require external audit; no automatic activation decision."]})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references",type=Path,default=DEFAULT_REFERENCES)
    parser.add_argument("--cases",type=Path)
    parser.add_argument("--profiles-file",type=Path,default=DEFAULT_HOLISTIC_PROFILES)
    parser.add_argument("--profiles",nargs="+",default=["holistic_experimental"])
    parser.add_argument("--partition",choices=("development","validation"),default="development")
    parser.add_argument("--confirm-locked-validation",action="store_true")
    parser.add_argument("--allow-synthetic-fixtures",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args(argv)
    try:
        if args.partition == "validation" and not args.confirm_locked_validation:
            raise ValueError("Locked validation access requires explicit acknowledgement; never tune against it.")
        if args.output.resolve() in {x.resolve() for x in (args.references,args.profiles_file,args.cases) if x is not None}:
            raise ValueError("Output cannot overwrite input artifacts.")
        report = evaluate(args.references,args.cases,args.profiles_file,args.profiles,args.partition,args.allow_synthetic_fixtures)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        print(json.dumps({"approved_reference_count":report["approved_reference_count"],"evaluated_case_count":report["evaluated_case_count"],"independent_validation_complete":False}))
    except (ValueError,OSError,TypeError,KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
