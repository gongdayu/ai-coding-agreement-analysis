# Public Agreement Analysis Code

This repository contains the public coding workbooks and reproducible analysis
code for the GPT-4.1 and GPT-5.4 human-vs-AI agreement analyses.

Associated conference abstract:

Chang Yu, Mo Han, Rui Huang, Hanna Grol-Prokopczyk, and GONGDA YU. "Human vs.
AI in Conducting Scoping Reviews: Evaluating Large Language Model Accuracy
Across Article and Task Type." Innovation in Aging, 9(Supplement_2),
igaf122.2181. https://doi.org/10.1093/geroni/igaf122.2181

## Repository Contents

- `data/coding_workbooks/`: public human-vs-AI coding workbooks used for the
  row-level agreement analysis.
- `data/article_code_binary_datasets/`: public article-code binary datasets
  used for the GPT-4.1 Q1-Q4 agreement calculations.
- `analysis_code/`: reproducible agreement-analysis scripts and shared metric
  utilities for generating the public manuscript tables and local audit outputs.
- `gpt_codings/`: collaborator notebooks used to generate GPT coding outputs
  from article PDFs.
- `METHODOLOGY.md`: describes the binary expansion, TP/TN/FP/FN definitions,
  metric formulas, grouping rules, and cascaded accuracy calculation.
- `requirements.txt`: Python dependencies.

Generated public outputs are not committed because they can be regenerated from
the released scripts and datasets.

## Data and Code Availability

The public data workbooks, GPT coding notebooks, and reproducible analysis code
are available in this repository. Generated output files are not committed
because they can be reproduced by running the scripts below.

## Setup

Use Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

## Reproduce Public Tables

From this repository folder:

```bash
python analysis_code/calculate_gpt41_public_tables.py
python analysis_code/calculate_gpt54_public_tables.py
```

By default, local verification outputs are written to:

- `outputs/gpt41/`
- `outputs/gpt54/`

Each script writes both an Excel workbook and separate CSV files for local
checking. These generated outputs are excluded from version control.

The default outputs are generated directly from the released public datasets.

## Export Detailed Audit Tables

To generate detailed TP/TN/FP/FN audit outputs from the released public
datasets:

```bash
python analysis_code/recalculate_agreement_audit.py
```

By default, outputs are written to:

```text
outputs/audit_counts/
```

The audit output is local only and is excluded from version control.

## GPT Coding Notebooks

The `gpt_codings/` notebooks reproduce the GPT coding workflow. They expect
article PDFs to be placed locally under:

```text
gpt_codings/data/pdf_to_review/
```

Before running the notebooks, set `OPENAI_API_KEY` in your environment. Do not
hardcode API keys in notebooks or commit generated JSON/CSV outputs. The
`gpt_codings/data/` folder and generated `.json`/`.csv` files are excluded from
version control.

## Public Output Policy

The released public table scripts write the public manuscript table outputs.
Generated output tables are not committed.

TP/TN/FP/FN details are calculated by the code for auditability, but they are
not added to the default public result tables unless they are part of the
manuscript table format.

## Method Summary

For Q1-Q4, each allowed code is expanded into a binary article-code comparison
against the human coding. GPT-4.1 Q1-Q4 uses the released article-code binary
matrices. GPT-5.4 Q1-Q4 is expanded from the released row-level coding workbook.
TP, TN, FP, and FN are counted across these comparisons, and retained agreement
metrics are calculated from those counts.

For Q5-Q8, each single-label question is expanded into one binary comparison per
allowed category. Q5 is evaluated on all articles. Q6 and Q7 use articles where
human and AI Q5 labels are both in the broad MA/SRQuan group. Q8 uses articles
where human and AI Q5 labels are both in the broad QA/SRQual group.

GPT-5.4 Q8 uses five categories: `NO`, `YES`, `OPP`, `UNC`, and `QT`.

Multi-label cells may include parenthetical explanations after a leading code.
The parser keeps the leading code and ignores parenthetical explanatory text.

The scripts preserve `NA` as a valid code when reading Excel workbooks.
