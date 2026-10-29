"""Step 3: validate run identity/lineage and combine new outputs into result tables.

Usage:
    # Method 1
    python scripts/postprocess.py --method 1 --pdf-text <pdf_text.json> --prompt-1 <prompt_1.json> --out-csv <results.csv>

    # Method 2
    python scripts/postprocess.py --method 2 --pdf-text <pdf_text.json> --prompt-1-1 <prompt_1_1.json> --prompt-1-2 <prompt_1_2.json> \
        --prompt-2 <prompt_2.json> --out-csv <results.csv>

Writes <results.csv>, one row per article. For Method 2 it also writes
<results>_flatten.csv, one row per research goal aspect / finding.
The cleaning and merging functions retain the original notebook semantics.
Method 1 without --prompt-2 is partial: Q5-Q8 are synthetic placeholders,
identified as such in the output provenance sidecar.
"""
import argparse
import ast
import json
from pathlib import Path

from provenance import validate_chain, sha

import pandas as pd

# In Method 1, prompt 2 was run in a separate experiment; these placeholders keep the same columns.
METHOD_1_PROMPT_2_PLACEHOLDER = {"review_type": "NA", "statistical_significance": "NA",
                                 "lower_status_significance": "NA", "qualitative_assumption": "NA"}


def flatten_list(lst):
    """Flatten a list of lists into a single list, but do not flatten strings."""
    flat = []
    for item in lst:
        if isinstance(item, list):
            flat.extend(flatten_list(item))
        else:
            flat.append(item)
    return flat


def dedup_and_flatten_lists_in_df(df):
    """
    For all columns in the DataFrame:
    - If a cell is a list, deduplicate it.
    - If a cell is a list of lists, flatten it and deduplicate.
    """
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            def process_cell(cell):
                if isinstance(cell, list):
                    flat = flatten_list(cell)
                    return list(dict.fromkeys(flat))  # dedup and preserve order
                return cell
            df[col] = df[col].apply(process_cell)
    return df


def clean_NA_in_list(df):
    """
    Processes all columns in a DataFrame that contain lists.
    If a list contains only 'NA', it is left unchanged.
    If a list contains more than one item and includes 'NA', 'NA' is removed.
    """
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).all():
            df[col] = df[col].apply(
                lambda lst: lst if lst == ["NA"]
                else [item for item in lst if item != "NA"]
            )
    return df


def merge_dicts(dict_list):
    combined = {
        "research_goal": None,
        "research_goal_aspect": {},
        "research_finding": {},
        "research_finding_details": {},
        "pain_or_treatment_type": [],
        "aspect_type": [],
        "social_dimensions_type": [],
        "mechanism_type": [],
        "review_type": None,
        "statistical_significance": None,
        "lower_status_significance": None,
        "qualitative_assumption": None
    }

    type_keys = ["pain_or_treatment_type", "aspect_type", "social_dimensions_type", "mechanism_type"]

    for d in dict_list:
        for key, value in d.items():
            # Flat values
            if key in combined and not isinstance(combined[key], (dict, list)):
                combined[key] = value

            # Merge dicts
            elif key in ["research_goal_aspect", "research_finding", "research_finding_details"]:
                if isinstance(value, dict):
                    combined[key].update(value)

            # Handle dicts like {"research_finding_1": {type_keys...}}
            elif key.startswith("research_finding_") and isinstance(value, dict):
                for subkey in type_keys:
                    if subkey in value:
                        combined[subkey].append(value[subkey])

    return combined


def integrate_method_1(result_dict):
    """Collect each field of the per-finding answers of prompt 1 into a list (from the Method 1 notebook)."""
    integrated_dict = {}
    for sub_dict in result_dict.values():
        for key, value in sub_dict.items():
            integrated_dict.setdefault(key, []).append(value)
    return {**integrated_dict, **METHOD_1_PROMPT_2_PLACEHOLDER}


def flatten_nested_fields(df):
    flat_rows = []

    for _, row in df.iterrows():
        max_len = max(
            len(row.get("research_goal_aspect", {})),
            len(row.get("research_finding", {})),
            len(row.get("research_finding_details", {}))
        )

        for i in range(max_len):
            flat_row = {
                "paper_idx": row["paper_idx"] if i == 0 else "",
                "research_goal": row["research_goal"] if i == 0 else "",
                "research_goal_aspect": "",
                "research_finding": "",
                "research_finding_details": ""
            }

            # Fill indexed items if available
            rga_keys = list(row.get("research_goal_aspect", {}).values())
            rf_keys = list(row.get("research_finding", {}).values())
            rfd_keys = list(row.get("research_finding_details", {}).values())

            if i < len(rga_keys):
                flat_row["research_goal_aspect"] = rga_keys[i]

            if i < len(rf_keys):
                flat_row["research_finding"] = rf_keys[i]

            if i < len(rfd_keys):
                flat_row["research_finding_details"] = rfd_keys[i]

            flat_rows.append(flat_row)

    return pd.DataFrame(flat_rows)


def clean_list_like_columns(df):
    """
    Converts list-type or stringified list-type column values in a DataFrame
    into clean strings: no brackets/quotes, items separated by ', '.
    """
    def convert(val):
        # Try converting stringified lists to actual lists
        if isinstance(val, str):
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, list):
                    return ', '.join(str(item) for item in parsed)
            except (ValueError, SyntaxError):
                pass  # Leave as-is if not a valid list string
        elif isinstance(val, list):
            return ', '.join(str(item) for item in val)
        return val  # Return original if not list or list-like

    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list) or (isinstance(x, str) and x.strip().startswith('['))).any():
            df[col] = df[col].apply(convert)

    return df


def load_results(path):
    with open(path) as f:
        return {k: v["result"] for k, v in json.load(f)["results"].items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", required=True, choices=["1", "2"])
    ap.add_argument("--prompt-1", help="Method 1: run_llm.py output for prompt 1")
    ap.add_argument("--prompt-1-1", help="Method 2: run_llm.py output for prompt 1_1")
    ap.add_argument("--prompt-1-2", help="Method 2: run_llm.py output for prompt 1_2")
    ap.add_argument("--prompt-2", help="Method 2: run_llm.py output for prompt 2")
    ap.add_argument("--out-csv", required=True, help="Output CSV file")
    ap.add_argument("--pdf-text", required=True, help="Exact extracted-text JSON used for this run")
    args = ap.parse_args()

    if args.method == "1":
        if not args.prompt_1:
            ap.error("--method 1 needs --prompt-1")
        paths = {"1": args.prompt_1}
        if args.prompt_2:
            paths["2"] = args.prompt_2
        runs = validate_chain(paths, args.pdf_text)
        r1 = {k: v["result"] for k, v in runs["1"]["results"].items()}
        article_ids = sorted(r1)
        all_results = [integrate_method_1(r1[a]) for a in article_ids]
        if args.prompt_2:
            for a, result in zip(article_ids, all_results):
                result.update(runs["2"]["results"][a]["result"])
    else:
        if not (args.prompt_1_1 and args.prompt_1_2 and args.prompt_2):
            ap.error("--method 2 needs --prompt-1-1, --prompt-1-2 and --prompt-2")
        paths = {"1_1": args.prompt_1_1, "1_2": args.prompt_1_2, "2": args.prompt_2}
        runs = validate_chain(paths, args.pdf_text)
        r11, r12, r2 = ({k: v["result"] for k, v in runs[p]["results"].items()} for p in ["1_1", "1_2", "2"])
        article_ids = sorted(r11)
        missing = [a for a in article_ids if a not in r12 or a not in r2]
        if missing:
            raise SystemExit(f"Articles missing from prompt 1_2 or prompt 2 output: {missing}")
        all_results = [merge_dicts([r11[a], r12[a], r2[a]]) for a in article_ids]

    results_df = pd.DataFrame(all_results)
    results_df['paper_idx'] = article_ids
    results_df = results_df[['paper_idx'] + [col for col in results_df.columns if col != 'paper_idx']]
    results_df = dedup_and_flatten_lists_in_df(results_df)
    results_df = clean_NA_in_list(results_df)
    results_df = clean_list_like_columns(results_df)
    if Path(args.out_csv).resolve() in [Path(p).resolve() for p in [*paths.values(), args.pdf_text]]:
        ap.error("Output must differ from source JSON files")
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.out_csv, encoding="utf-8")
    print(f"Wrote {args.out_csv}")

    if args.method == "2":
        flat_path = args.out_csv[:-4] + "_flatten.csv" if args.out_csv.endswith(".csv") else args.out_csv + "_flatten.csv"
        flat_df = flatten_nested_fields(results_df)
        flat_df.to_csv(flat_path, encoding="utf-8")
        print(f"Wrote {flat_path}")
    manifest = {"release_postprocessing": "RR2 guards added after historical coding", "method": args.method,
                "coverage": "Q1-Q8" if args.prompt_2 else "Q1-Q4 only; Q5-Q8 are synthetic NA placeholders",
                "synthetic_placeholder_fields": list(METHOD_1_PROMPT_2_PLACEHOLDER) if not args.prompt_2 else [],
                "model": next(iter(runs.values()))["metadata"]["model"],
                "mode": next(iter(runs.values()))["metadata"]["mode"],
                "pdf_text_sha256": sha(args.pdf_text), "input_runs": {p: sha(path) for p, path in paths.items()},
                "output_sha256": sha(args.out_csv), "article_ids": article_ids}
    Path(args.out_csv + ".provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
