# AI-assisted review coding: RR2 reproducibility materials

This package separates fixed-data statistical reproduction from optional remote GPT coding. The fixed-data workflow reproduces the current 100-review analyses for GPT-4.1 Method 1, GPT-4.1 Method 2 and GPT-5.4 Method 2. No API key, Word installation, PDF collection or unpublished intermediate file is required for that workflow.

## Contents

- `data/articles.csv`: 100 renumbered article IDs and bibliographic metadata.
- `data/coding_workbooks/`: three fixed coding tables, exported as UTF-8 CSV with unchanged GPT answer strings and the common Human reference.
- `data/article_code_binary_datasets/`: rebuilt Method 1/2 GPT-4.1 Q1–Q4 binary tables.
- `analysis_code/`: one analysis entry point, agreement calculations and evaluation methodology.
- `gpt_codings/`: [independent codebook](gpt_codings/Codebook_Coding%20Questions%20Q1-Q8.docx), exact supplied prompt templates, coding scripts and reference notebooks. See its README before any remote run.

The manuscript, supplementary Word document, internal guidelines, comments, audit reports, old-ID mapping, copyrighted PDFs and extracted full texts are not part of this package. Bibliographic identifiers provide a way to obtain articles through lawful access; their full texts are not licensed by the code license.

## Install and reproduce the fixed-data analysis

Use Python 3.12. From the package root, create a new virtual environment and install the tested dependencies. Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe analysis_code/run_analysis.py --out ../rr2_results
```

On macOS/Linux use `python3.12 -m venv .venv` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`. Inputs are located relative to the script, not the current working directory. The output path is explicit; the same commands can be launched from another directory using absolute script and output paths.

The default run calculates all three 100-review configurations using 10,000 bootstrap replicates with seed 20261013. It writes `statistics.json`, long-form `metrics.csv`, `per_label_metrics.csv`, `ooc_summary.csv`, `out_of_codebook_audit.csv`, `analysis_input.csv`, the binary matrices and `bootstrap_indices.npy`. Table names 1–5 in `statistics.json` follow the recalculation output convention, rather than the supplementary document's table numbering.

## Scope and interpretation

Read [`analysis_code/METHODOLOGY.md`](analysis_code/METHODOLOGY.md) for legal label pools, aggregation, eligibility, OOC handling and uncertainty. Q6 includes NA, and Q8 includes OPP. OOC labels are preserved and reported; they are not silently converted into legal answers. Method 1 downstream performance is outside the comparison. Composite F1 is a descriptive product, not cascaded accuracy.

Optional new coding calls are separate from fixed-data reproduction. The supplied model identifiers specify rerun configurations; historical returned model IDs and identical text reuse across all original conditions could not be independently confirmed without request/response and cache records. New remote responses can vary with service availability and model behavior. No claim is made that rerunning GPT will reproduce every historical answer.

## Replacing the previous release

Replace the previous release tree as a whole; copying only matching filenames would leave obsolete calculation entry points and binary data. The old Wilson-based agreement intervals, alpha-as-kappa options, old label pools and outdated binaries are not supported alternatives in this package. `analysis_code/run_analysis.py` is the sole supported statistical entry point.

The file names listed in the revision guidelines correspond to the following implementations in this release:

| Listed item | Current implementation or location |
| --- | --- |
| `Calculate_gpt41` | `analysis_code/run_analysis.py`: GPT-4.1 Method 1 and Method 2 analyses. |
| `Calculate_gpt54` | `analysis_code/run_analysis.py`: GPT-5.4 Method 2 analysis. |
| `Recalculate_agreement` | `analysis_code/run_analysis.py` and `analysis_code/agreement_metrics.py`: counts, agreement metrics, bootstrap intervals and OOC summaries. |
| `analysis_code/README` | Installation and execution instructions in this README; evaluation methods in `analysis_code/METHODOLOGY.md`. |
| `Gitignore`, `Citation`, `License` | Repository-wide `.gitignore`, `CITATION.cff` and `LICENSE` in the package root. |

The three calculation entry points are consolidated; their former command-line interfaces and Excel output layouts are not retained. Use the command above and the outputs described here.

## Attribution

The existing software LICENSE and CITATION.cff are retained from the prior public release. The citation describes the referenced conference abstract, not an assertion that the revision manuscript has been published. Third-party libraries retain their respective licenses. The code license does not confer rights to the source articles or their full text.
