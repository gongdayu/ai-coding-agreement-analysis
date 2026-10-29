"""Run one prompt with provenance guards. API requires --execute-api.

--mock-responses takes a local {ID: response} mapping, never creates a client,
and marks all outputs as mock. New records are not historical run evidence.
"""
import argparse
import datetime
from importlib import metadata
import json
from pathlib import Path
import platform
from llm import extract_string, new_message_object, run_completion_gpt
from prompts import PROMPT_NAMES, fill_prompt, load_template, sha256_text
from provenance import MODELS, read_json, require_ids, load_run, sha, validate_result

def save(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(path)

def load_inputs(prompt, path):
    if prompt == "1_2":
        source = load_run(path, "1_1")
        return {k: v["result"] for k, v in sorted(source["results"].items())}, source["metadata"]
    source = read_json(path); require_ids(source, "pdf_text")
    if any(not isinstance(t, str) or not t.strip() for t in source.values()): raise ValueError("Every article must have nonempty extracted text")
    return dict(sorted(source.items())), None

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompt", required=True, choices=PROMPT_NAMES); ap.add_argument("--input", required=True)
    ap.add_argument("--model", required=True, choices=MODELS); ap.add_argument("--temperature", type=float, default=0)
    ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int)
    group = ap.add_mutually_exclusive_group(required=True); group.add_argument("--execute-api", action="store_true"); group.add_argument("--mock-responses")
    args = ap.parse_args()
    if args.limit is not None and args.limit <= 0: ap.error("--limit must be positive")
    if Path(args.input).resolve() == Path(args.out).resolve(): ap.error("--out must differ from --input")
    inputs, upstream = load_inputs(args.prompt, args.input); mode = "mock" if args.mock_responses else "api"
    if upstream and any(upstream.get(k) != v for k, v in (("model", args.model), ("temperature", args.temperature), ("mode", mode))): ap.error("Prompt 1_2 settings must match prompt 1_1")
    if args.limit: inputs = dict(list(inputs.items())[:args.limit])
    template = load_template(args.prompt)
    meta = {"schema_version": "rr2-generation-v1", "prompt": args.prompt, "prompt_template_sha256": sha256_text(template), "model": args.model,
            "temperature": args.temperature, "mode": mode, "input_sha256": sha(args.input), "pdf_text_sha256": upstream["pdf_text_sha256"] if upstream else sha(args.input),
            "selected_article_ids": list(inputs), "mock_responses_sha256": sha(args.mock_responses) if args.mock_responses else None}
    logs = {"metadata": dict(meta), "results": {}, "failures": []}
    if Path(args.out).exists():
        logs = read_json(args.out)
        if any(logs.get("metadata", {}).get(k) != v for k, v in meta.items()): ap.error("Existing output has different inputs/settings; choose new --out")
        load_run(args.out, args.prompt, complete=False)
    mock = read_json(args.mock_responses) if args.mock_responses else None
    if mock is not None and set(mock) != set(inputs): ap.error("Mock IDs must exactly match selected input IDs")
    packages = {"python": platform.python_version()}
    for p in ("openai", "pandas", "pypdf", "langchain-community"):
        try: packages[p] = metadata.version(p)
        except metadata.PackageNotFoundError: packages[p] = None
    logs["metadata"]["packages"] = packages; save(args.out, logs)
    for article_id, value in inputs.items():
        text = fill_prompt(template, args.prompt, value); digest = sha256_text(text)
        if article_id in logs["results"]:
            if logs["results"][article_id].get("prompt_sha256") != digest: raise ValueError(f"{article_id}: saved prompt hash differs")
            continue
        when = datetime.datetime.now(datetime.timezone.utc).isoformat(); rec = {"prompt_sha256": digest, "timestamp_utc": when}
        try:
            if mock is not None:
                raw = mock[article_id]
                rec.update({"response": raw if isinstance(raw, str) else raw["response"], "returned_model": args.model if isinstance(raw, str) else raw.get("returned_model", args.model), "response_id": None, "finish_reason": "mock", "usage": None})
            else: rec.update(run_completion_gpt([new_message_object("user", text)], args.model, args.temperature))
            if rec.get("returned_model") != args.model: raise ValueError("Returned model differs from the requested snapshot; record preserved for review")
            if rec.get("finish_reason") not in ("stop", "mock"): raise ValueError("Completion was not marked stop; record preserved for review")
            result = extract_string(rec["response"]); validate_result(args.prompt, result); rec["result"] = result
            logs["results"][article_id] = rec; save(args.out, logs)
        except Exception as exc:
            logs["failures"].append({"article_id": article_id, "timestamp_utc": when, "error_type": type(exc).__name__, "message": str(exc), "attempt": rec})
            save(args.out, logs); raise SystemExit(f"{article_id}: failure saved; stopped without retry ({type(exc).__name__})") from exc
    print(f"Saved {len(logs['results'])} {mode} results to {args.out}")

if __name__ == "__main__": main()
