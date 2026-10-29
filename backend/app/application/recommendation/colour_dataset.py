"""Strict versioned sample import and experimental metrics, no fabricated labels."""
from collections import Counter
from pathlib import Path
import json
from app.application.nlp.vocabulary import Vocabulary
from app.application.recommendation.oklab import normalize_hex
from app.application.recommendation.prototype_colour_classifier import content_hash

PARTITIONS = ("development", "calibration", "validation")


def validate_dataset(raw):
    if not isinstance(raw,dict) or raw.get("schema_version") != "1.0.0" or not isinstance(raw.get("version"),str) or not raw["version"] or raw.get("validation_locked") is not True or not isinstance(raw.get("samples"),list):
        raise ValueError("Dataset requires version, samples and locked validation declaration.")
    colours = Vocabulary.load().values["colours"]
    seen_ids, partitions_by_group, partitions_by_hex, samples = set(), {}, {}, []
    for source in raw["samples"]:
        if not isinstance(source,dict):
            raise ValueError("Sample must be an object.")
        row = dict(source)
        for key in ("sample_id", "source_group", "provenance"):
            if not isinstance(row.get(key),str) or not row[key].strip():
                raise ValueError("Sample needs identity, source group and provenance.")
        if row["sample_id"] in seen_ids:
            raise ValueError("Duplicate sample identity.")
        seen_ids.add(row["sample_id"])
        row["hex"] = normalize_hex(row.get("hex"))
        partition, kind = row.get("partition"), row.get("reference_kind")
        if partition not in PARTITIONS or kind not in ("canonical", "ambiguous", "unknown"):
            raise ValueError("Invalid partition or reference kind.")
        if (kind == "canonical" and row.get("label") not in colours) or (kind != "canonical" and row.get("label") is not None):
            raise ValueError("Reference label must be an approved colour or explicit null.")
        reviewers = row.get("reviewer_ids")
        if not isinstance(reviewers,list) or any(not isinstance(x,str) or not x.strip() for x in reviewers) or len(set(reviewers)) != len(reviewers) or not isinstance(row.get("independently_reviewed"),bool):
            raise ValueError("Invalid review metadata.")
        if row["independently_reviewed"] and len(reviewers) < 2:
            raise ValueError("Independent review requires at least two declared reviewers.")
        for value, index in ((row["source_group"],partitions_by_group),(row["hex"],partitions_by_hex)):
            if value in index and index[value] != partition:
                raise ValueError("Cross-partition source/hex overlap; keep related samples together.")
            index[value] = partition
        samples.append(row)
    normalized = dict(raw, samples=sorted(samples,key=lambda item:item["sample_id"]))
    return normalized


def load_dataset(path):
    return validate_dataset(json.loads(Path(path).read_text(encoding="utf-8")))


def ratio(top, bottom):
    return top / bottom if bottom else None


def evaluate_dataset(dataset, classifier, partition):
    if partition not in PARTITIONS:
        raise ValueError("Select one explicit partition.")
    rows = [row for row in dataset["samples"] if row["partition"] == partition]
    predictions = [(row,classifier.classify(row["hex"])) for row in rows]
    states = Counter(result.status for _,result in predictions)
    correct = sum(result.status == "Recognised" and row["reference_kind"] == "canonical" and result.colour == row["label"] for row,result in predictions)
    per_class = {}
    for name in sorted(Vocabulary.load().values["colours"]):
        support = sum(row["reference_kind"] == "canonical" and row["label"] == name for row,_ in predictions)
        predicted = sum(result.colour == name for _,result in predictions)
        tp = sum(row["reference_kind"] == "canonical" and row["label"] == name and result.colour == name for row,result in predictions)
        precision, recall = ratio(tp,predicted), ratio(tp,support)
        per_class[name] = {"support":support,"predicted":predicted,"true_positive":tp,"precision":precision,"recall":recall,"f1":None if precision is None or recall is None else ratio(2*precision*recall,precision+recall) if precision+recall else 0.0}
    canonical = sum(row["reference_kind"] == "canonical" for row in rows)
    reviewed = sum(row["independently_reviewed"] for row in rows)
    reviewed_support = Counter(row["label"] for row in rows if row["reference_kind"] == "canonical" and row["independently_reviewed"])
    confusion = Counter((row["label"] if row["reference_kind"] == "canonical" else row["reference_kind"],result.colour or result.status) for row,result in predictions)
    return {"dataset_version":dataset["version"],"dataset_hash":content_hash(dataset),"partition_hash":content_hash(rows),"configuration_version":classifier.configuration_version,"configuration_hash":classifier.configuration_hash,
            "partition":partition,"sample_count":len(rows),"independently_reviewed_count":reviewed,
            "precision":ratio(correct,states["Recognised"]),"recall":ratio(correct,canonical),"coverage":ratio(states["Recognised"],len(rows)),
            "abstention_rate":ratio(len(rows)-states["Recognised"],len(rows)),"ambiguity_rate":ratio(states["Ambiguous"],len(rows)),"unknown_rate":ratio(states["Unknown"],len(rows)),
            "false_recognitions_on_uncertain_references":sum(result.status == "Recognised" and row["reference_kind"] != "canonical" for row,result in predictions),
            "per_class":per_class,"confusion":[{"reference":a,"prediction":b,"count":n} for (a,b),n in sorted(confusion.items())],
            "duplicate_hex_within_partition":len(rows)-len({row["hex"] for row in rows}),
            "independent_source_groups":len({row["source_group"] for row in rows}),
            "missing_reviewed_colours":sorted(set(per_class)-set(reviewed_support)),
            "release_validation_complete":False,"mandatory_evidence_enabled":False,
            "limitations":["Experimental diagnostics only; reviewer declarations are not independently verified.","No release precision requirement or calibration has been approved."]}
