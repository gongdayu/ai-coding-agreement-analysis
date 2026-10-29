# GPT coding materials and guarded execution

This directory contains the supplied coding prompts, the Q1–Q8 Codebook, reference notebooks, and a guarded command-line implementation. The fixed workbook analyses in the parent repository are the offline evidence for the paper's reported statistics. Running this directory against an API generates **new** coding outputs; it does not establish the provenance of the historical workbooks or reproduce a historical model service exactly.

The dated model IDs below are explicit configurations for new runs: `gpt-4.1-2025-04-14` and `gpt-5.4-2026-03-05`. Their presence in a script or filename is not evidence of the model actually returned in a historical request. New logs save both requested and returned model IDs and reject a returned snapshot mismatch. Model access and future availability have not been tested with a live API in this release.

## Materials and actual conditions

- `prompts/`: four supplied UTF-8 templates, copied byte for byte. Filling uses the notebook's `str(value)` and `replace`, including Python dictionary representation for prompt 1_2.
- `Codebook_Coding Questions Q1-Q8.docx`: unchanged supplied Codebook. Its definitions describe Method 2 prompt 1_2 (Q1–Q4) and prompt 2 (Q5–Q8). Method 1 has shorter RX and DO examples; the other Q1–Q4 definition blocks agree.
- `scripts/`: PDF text extraction, one-prompt execution, postprocessing, and provenance checks.
- `reference_notebooks/`: source cells retained from the supplied three notebooks. Saved outputs, execution counts, and nonessential notebook metadata were removed. These notebooks were **not executed** for this release and are reference material, not supported fresh-run entry points.

| Configuration | Q1–Q4 workflow | Q5–Q8 workflow |
|---|---|---|
| Method 1, gpt-4.1-2025-04-14 | Prompt 1 reads full extracted text and classifies findings | Supplied notebook substitutes four `NA` placeholders and says prompt 2 was a separate experiment. New CLI can explicitly merge a separately run prompt 2. |
| Method 2, gpt-4.1-2025-04-14 | Prompt 1_1 extracts goals/findings; prompt 1_2 reads its result and classifies findings | Independent prompt 2 reads the full extracted text |
| Method 2, gpt-5.4-2026-03-05 | Same three-prompt structure | Same independent prompt 2 |

Prompt 1_1 does not perform the Q5–Q8 single-label tasks. The supplied Method 1 workbook's Q5–Q8 values are retained historical data, not evidence that this notebook generated them. Its raw separate prompt-2 responses are not supplied here. A partial Method 1 CSV's `NA` values must not be scored as actual model responses.

## Install

Use Python 3.12. From this directory, create a fresh virtual environment:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip check
```

On macOS/Linux use `.venv/bin/python`. From any other working directory, pass absolute paths to these files. `requirements.txt` is unchanged from the supplied six direct pins.

## Extract article text

```text
python scripts/parse_pdfs.py --pdf-dir <local-pdf-directory> --out <work-directory>/pdf_text.json
```

The JSON maps the PDF filename stem to extracted text. For runs intended to match this public dataset, obtain each article using `../data/articles.csv`, verify its title/DOI, and name the local PDF with its public numeric ID (for example `1.pdf`, through `100.pdf`) before extraction. The resulting JSON keys then match the coding tables. Keep this local preparation record; do not join outputs by lexical filename order. Other filename stems are permitted for separate studies, but require an explicit ID mapping before comparison; lexical filename sorting is not a numbering rule. All models should receive the same frozen `pdf_text.json`. Empty text and duplicate IDs are rejected. The output has a SHA-256 sidecar.

The loader concatenates `page_content` exactly as in the supplied implementation, without adding page separators. This is PDF **text** extraction: no OCR, image interpretation, or guarantee that every table/figure is represented. PDF bytes and extracted-text versions can affect results. Input PDF copyrights and distribution permissions are separate from the released code; full article PDFs are not included.

## New API runs (optional; requires your own access)

API execution is explicit through `--execute-api`. These commands incur the provider's charges and were not run for this release. Set `OPENAI_API_KEY` in your environment; do not put a key in code. Each command stops at its first failure and saves the attempt. SDK retries are disabled. Reissuing an identical command is a deliberate resume: successful IDs are skipped; failed IDs may be attempted again and failure records remain.

Method 2, using the same extracted text for every full-text step:

```text
python scripts/run_llm.py --prompt 1_1 --input <work>/pdf_text.json --model gpt-4.1-2025-04-14 --out <work>/m2_11.json --execute-api
python scripts/run_llm.py --prompt 1_2 --input <work>/m2_11.json --model gpt-4.1-2025-04-14 --out <work>/m2_12.json --execute-api
python scripts/run_llm.py --prompt 2 --input <work>/pdf_text.json --model gpt-4.1-2025-04-14 --out <work>/m2_2.json --execute-api
python scripts/postprocess.py --method 2 --pdf-text <work>/pdf_text.json --prompt-1-1 <work>/m2_11.json --prompt-1-2 <work>/m2_12.json --prompt-2 <work>/m2_2.json --out-csv <work>/m2.csv
```

For the GPT-5.4 condition, use `gpt-5.4-2026-03-05` in all three commands and distinct output paths. Do not mix models or API/mock runs in one merged output.

Method 1:

```text
python scripts/run_llm.py --prompt 1 --input <work>/pdf_text.json --model gpt-4.1-2025-04-14 --out <work>/m1_1.json --execute-api
python scripts/postprocess.py --method 1 --pdf-text <work>/pdf_text.json --prompt-1 <work>/m1_1.json --out-csv <work>/m1_partial.csv
```

The second command preserves the notebook's four synthetic `NA` placeholders and labels them in `m1_partial.csv.provenance.json` as **Q1–Q4 only**. For complete new Q1–Q8 output, run prompt 2 independently on the same `pdf_text.json` with the same model/temperature, then include `--prompt-2 <work>/m1_2.json` in Method 1 postprocessing. This is an explicit new run, not reconstructed historical evidence.

For a local mocked run, replace `--execute-api` with `--mock-responses <responses.json>`. That file must map exactly the selected article IDs to raw response strings (or objects with `response` and `returned_model`). `--limit N` selects the first N lexical IDs; use the same selection for every merged step and a distinct output file. `mode: mock` is saved and cannot be silently merged with API results.

## Output and guard semantics

`run_llm.py` saves raw response text, parsed dictionary, filled-prompt hash, UTC timestamp, requested model, returned model, response ID, finish reason, token usage if provided, package versions, input/template hashes, and failures. Completion records are saved atomically after each article. The new logging and guards were added for this release and are **not historical execution records**.

Resume requires exactly the same model, temperature, template, input bytes, selected IDs, and mock responses (when applicable). Postprocessing verifies exact article-set equality across steps, template hashes, original response/parsed-result agreement, model and mode identity, extracted-text bytes, per-article prompt hashes, and the exact prompt-1_1 output consumed by prompt 1_2. It requires the original `--pdf-text` file for these checks. Editing an upstream output after a downstream run invalidates its lineage; rerun the downstream step deliberately with a new output path.

Postprocessing retains the original merge, flatten, de-duplication, and NA-list cleaning rules. It does not silently repair out-of-codebook predictions. JSON is parsed first; the original Python literal format remains supported. Final result fields are structurally validated. Out-of-pool codes remain present for separate evaluation/audit. The CSV is an intermediate coding export; it is not an automatic replacement for the fixed coding workbooks or the evaluation pipeline.

The original notebooks expect pre-existing JSON files, initialize an API client, run installation cells, and resume by result-list length rather than article ID. Running them top to bottom in a fresh directory can fail or misassociate changed input sets. Use the CLI for new runs. This release has verified offline execution only; no claim is made that the reference notebooks, a remote model service, or historical generation can be recreated exactly.
