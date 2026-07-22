# Methodology and Audit Logic

This repository separates two reproducibility layers:

1. Public table scripts generate agreement table outputs from the released
   public datasets.
2. The audit script exports detailed TP, TN, FP, FN, retained metrics, and
   unknown-label audit sheets from the same public datasets.

Generated outputs are not committed to the repository.

## Binary Expansion

For Q1-Q4, each article can have multiple labels. Each allowed label is expanded
into one binary comparison:

- TP: AI selected the label and the human coder selected the label.
- TN: AI did not select the label and the human coder did not select the label.
- FP: AI selected the label but the human coder did not select the label.
- FN: AI did not select the label but the human coder selected the label.

For Q5-Q8, each single-label response is expanded into one binary comparison
per allowed category using the same TP/TN/FP/FN definitions.

## Multi-label Parsing

Multi-label spreadsheet cells are split on commas outside parentheses. If a
cell contains a parenthetical explanation after a leading code, only the leading
code is used for agreement counting.

Example:

```text
TT (religion, herbal remedies, vitamins)
```

is counted as:

```text
TT
```

The code `NA` is preserved as a valid label when Excel files are read.

## Metric Formulas

The shared metric code computes agreement metrics from TP, TN, FP, and FN:

```text
Precision = TP / (TP + FP)
AI Over-coding Rate = FP / (TP + FP)
Recall = TP / (TP + FN)
AI Under-coding Rate = FN / (TP + FN)
Jaccard Similarity = TP / (TP + FP + FN)
F-1 Score = 2 * Precision * Recall / (Precision + Recall)
Observed Agreement = (TP + TN) / N
Cohen's Kappa = (Observed Agreement - Expected Agreement) / (1 - Expected Agreement)
PABAK = 2 * Observed Agreement - 1
```

The shared implementation is in `analysis_code/agreement_metrics.py`. The
public table and audit scripts read the released coding workbooks and binary
matrices directly.

## Aggregation

Macro-level values are calculated by first calculating each question-level
metric and then averaging the retained metric values.

Micro-level values are calculated by summing TP, TN, FP, and FN across the
included questions or groups, then recalculating the metrics from those summed
counts.

For Q6 and Q7, the single-label audit uses articles where both human and AI Q5
labels fall in the broad MA/SRQuan group. For Q8, it uses articles where both
human and AI Q5 labels fall in the broad QA/SRQual group.

GPT-5.4 Q8 uses five categories: `NO`, `YES`, `OPP`, `UNC`, and `QT`.

For GPT-5.4, cascaded accuracy is calculated as:

```text
Q5 Precision * downstream question Precision
```

For GPT-4.1, cascaded accuracy is calculated from the single-label F-1 values:

```text
Q5 F1_Score * downstream question F1_Score
```

## Local Audit Command

The public table outputs can be reproduced with:

```bash
python analysis_code/calculate_gpt41_public_tables.py
python analysis_code/calculate_gpt54_public_tables.py
```

To generate local TP/TN/FP/FN audit outputs from the released datasets, run:

```bash
python analysis_code/recalculate_agreement_audit.py
```

By default, outputs are written to:

```text
outputs/audit_counts/
```

The output directory is ignored by Git.
