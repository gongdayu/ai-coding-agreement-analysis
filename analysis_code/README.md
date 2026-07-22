# Analysis Code

This folder contains the reproducible agreement-analysis code used to generate
the public manuscript tables and local audit outputs.

## Scripts

- `calculate_gpt41_public_tables.py`: reproduces the GPT-4.1 public agreement
  tables from the released coding workbook and article-code binary matrices.
- `calculate_gpt54_public_tables.py`: reproduces the GPT-5.4 public agreement
  tables from the released coding workbook.
- `recalculate_agreement_audit.py`: exports detailed local audit tables with
  TP/TN/FP/FN counts, retained metrics, and unknown-label audit sheets.
- `agreement_metrics.py`: shared parsing, binary-expansion, TP/TN/FP/FN, and
  agreement metric utilities.

## Run From the Repository Root

```bash
python analysis_code/calculate_gpt41_public_tables.py
python analysis_code/calculate_gpt54_public_tables.py
python analysis_code/recalculate_agreement_audit.py
```

Generated outputs are written under `outputs/` and are excluded from version
control.
