"""Identity and lineage checks for new runs; never retrospective evidence."""
import hashlib
import json
from pathlib import Path

MODELS = ("gpt-4.1-2025-04-14", "gpt-5.4-2026-03-05")
FIELDS = ("review_type", "statistical_significance", "lower_status_significance", "qualitative_assumption")
TYPE_FIELDS = ("pain_or_treatment_type", "aspect_type", "social_dimensions_type", "mechanism_type")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj: raise ValueError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)

def require_ids(obj, label):
    if not isinstance(obj, dict) or not obj or any(not isinstance(k, str) or not k.strip() for k in obj):
        raise ValueError(f"{label}: expected a nonempty mapping with nonempty string article IDs")
    return set(obj)

def validate_result(prompt, result):
    if not isinstance(result, dict) or not result: raise ValueError(f"Prompt {prompt}: expected a nonempty dictionary")
    if prompt == "2":
        if any(not isinstance(result.get(k), str) or not result[k].strip() for k in FIELDS):
            raise ValueError("Prompt 2: all four Q5-Q8 fields must be nonempty strings")
    elif prompt == "1_1":
        if not isinstance(result.get("research_goal"), str) or not result["research_goal"].strip(): raise ValueError("Prompt 1_1: missing research_goal")
        for k in ("research_goal_aspect", "research_finding", "research_finding_details"):
            if not isinstance(result.get(k), dict): raise ValueError(f"Prompt 1_1: {k} must be a dictionary")
    else:
        for key, value in result.items():
            if not key.startswith("research_finding_") or not isinstance(value, dict): raise ValueError(f"Prompt {prompt}: expected per-finding dictionaries")
            if any(k not in value or not isinstance(value[k], (str, list)) or not value[k] for k in TYPE_FIELDS): raise ValueError(f"Prompt {prompt}: missing Q1-Q4 field in {key}")

def load_run(path, prompt, *, complete=True):
    data = read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("metadata"), dict): raise ValueError(f"{path}: missing run metadata")
    meta = data["metadata"]
    if meta.get("schema_version") != "rr2-generation-v1" or meta.get("prompt") != prompt: raise ValueError(f"{path}: wrong schema or prompt; expected {prompt}")
    if meta.get("model") not in MODELS or meta.get("mode") not in ("api", "mock"): raise ValueError(f"{path}: unsupported requested model or run mode")
    for key in ("input_sha256", "pdf_text_sha256"):
        if not isinstance(meta.get(key), str) or len(meta[key]) != 64 or any(c not in '0123456789abcdef' for c in meta[key]): raise ValueError(f"{path}: invalid {key}")
    from prompts import load_template, sha256_text
    if meta.get("prompt_template_sha256") != sha256_text(load_template(prompt)): raise ValueError(f"{path}: prompt template differs from release")
    ids = meta.get("selected_article_ids")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)) or any(not isinstance(k, str) or not k.strip() for k in ids): raise ValueError(f"{path}: invalid selected IDs")
    records = data.get("results")
    if not isinstance(records, dict) or not set(records) <= set(ids): raise ValueError(f"{path}: result IDs outside planned input")
    if complete and set(records) != set(ids): raise ValueError(f"{path}: incomplete result IDs")
    for article_id, rec in records.items():
        if not isinstance(rec, dict) or not isinstance(rec.get("response"), str): raise ValueError(f"{article_id}: missing original response")
        if not isinstance(rec.get("returned_model"), str) or not rec["returned_model"]: raise ValueError(f"{article_id}: missing returned model")
        if rec["returned_model"] != meta["model"]: raise ValueError(f"{article_id}: returned model differs from requested snapshot")
        from llm import extract_string
        if extract_string(rec["response"]) != rec.get("result"): raise ValueError(f"{article_id}: parsed result differs from response")
        validate_result(prompt, rec["result"])
    return data

def validate_chain(paths, pdf_text_path):
    runs = {p: load_run(path, p) for p, path in paths.items()}
    first = next(iter(runs.values()))
    pdf_text = read_json(pdf_text_path); require_ids(pdf_text, "pdf_text")
    if first["metadata"]["pdf_text_sha256"] != sha(pdf_text_path): raise ValueError("Extracted text differs from the recorded input")
    if not set(first["results"]) <= set(pdf_text): raise ValueError("Output includes articles absent from extracted text")
    for p, run in runs.items():
        for key in ("model", "temperature", "mode", "pdf_text_sha256"):
            if run["metadata"].get(key) != first["metadata"].get(key): raise ValueError(f"Prompt {p}: incompatible {key}")
        if set(run["results"]) != set(first["results"]): raise ValueError(f"Prompt {p}: article ID sets differ")
    if "1_2" in runs and ("1_1" not in runs or runs["1_2"]["metadata"].get("input_sha256") != sha(paths["1_1"])): raise ValueError("Prompt 1_2 does not identify this exact prompt 1_1 output")
    for p, run in runs.items():
        if p != "1_2" and run["metadata"].get("input_sha256") != run["metadata"].get("pdf_text_sha256"): raise ValueError(f"Prompt {p}: inconsistent PDF-text lineage")
        from prompts import fill_prompt, load_template, sha256_text
        for article_id, rec in run["results"].items():
            value = runs["1_1"]["results"][article_id]["result"] if p == "1_2" else pdf_text[article_id]
            expected = sha256_text(fill_prompt(load_template(p), p, value))
            if rec.get("prompt_sha256") != expected: raise ValueError(f"{article_id}: prompt content differs from upstream input")
    return runs
