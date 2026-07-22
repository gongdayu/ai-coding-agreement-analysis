# Coding Workbooks

This folder contains the public coding workbooks used for the agreement
analysis.

## Files

- `100 Articles_Human VS GPT-4.1_Method1.xlsx`: human coding compared with
  GPT-4.1 Method 1 coding.
- `100 Articles_Human VS GPT-4.1_Method2.xlsx`: human coding compared with
  GPT-4.1 Method 2 coding.
- `100 Articles_Human VS GPT-5.4_Method2.xlsx`: human coding compared with
  GPT-5.4 Method 2 coding.

Each workbook contains one row per article and paired human/AI coding columns
for Q1-Q8. Q1-Q4 are multi-label questions. Q5-Q8 are single-label questions.

These files provide row-level coding transparency. To reproduce the finalized
public manuscript tables exactly, use the public table scripts and detailed
audit script in `analysis_code/`. GPT-4.1 Q1-Q4 also uses the released
article-code binary datasets in `data/article_code_binary_datasets/`.

This release includes the files needed for public reproducibility.
