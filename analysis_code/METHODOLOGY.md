# Evaluation methodology

## Data and analysis units

The fixed study contains 100 reviews, with 25 in each Human Q5 stratum: QA, SRQual, SRQuan and MA. The same author-confirmed Human coding is used for all three configurations. Analyses join on the new public article IDs. The old-to-new ID crosswalk is not distributed.

Q1–Q4 allow multiple labels. Codes are case-normalized and deduplicated; commas and semicolons separate codes only outside explanatory parentheses. The parser extracts the leading code, retaining the supplied explanations in the raw data. An empty or unparseable answer is an error, not a negative response. Each allowed label is evaluated as a binary Human/GPT pair. Single-label Q5–Q8 use the same one-versus-rest counting scheme.

The allowed pools are the supplied `gpt_codings/Codebook_Coding Questions Q1-Q8.docx` and `agreement_metrics.py`. Q6 has YES, NO, QA, MIXED and NA; MIXEDOPP is not a valid Q6 label. Q7 includes NODIFF and QA. Q8 has NO, YES, OPP, UNC and QT. Capitalization is normalized during analysis (SRQual/SRQuan → SRQUAL/SRQUAN); category membership is unchanged.

## Counts and out-of-codebook responses

For each allowed label, TP is Human=1/GPT=1; TN is 0/0; FP is 0/1; FN is 1/0. A predicted out-of-codebook (OOC) code is retained and audited, without remapping or excluding the article. It has no corresponding allowed-label binary column, so it does not itself add an FP. Any omitted Human allowed label contributes an FN. One OOC code therefore need not correspond to exactly one FN. Legal co-predictions remain counted. OOC is a codebook-compliance measure, not a measurement of factual hallucination.

`out_of_codebook_audit.csv` lists all Q1–Q8 OOC responses in all three fixed datasets, irrespective of the performance-analysis subsets. `ooc_summary.csv` uses the supplementary table's analysis-specific scope: Q1–Q5 cover all 100 articles; Method 2 Q6–Q8 cover their conditional subsets below; Method 1 Q6–Q8 are `/` because they are outside the downstream comparative analysis. Response frequency counts a question answer once if it contains one or more OOC codes. Assignment frequency counts individual distinct OOC labels divided by all predicted label assignments. These denominators are different and must not be interchanged. Overall response benchmarks are 11/500, 11/631 and 2/629 for Method 1 GPT-4.1, Method 2 GPT-4.1 and Method 2 GPT-5.4, respectively. The differing task coverage prevents a direct interpretation of these totals as an overall model ranking.

## Metrics and aggregation

Precision=TP/(TP+FP); recall=TP/(TP+FN); specificity=TN/(TN+FP); F1=2TP/(2TP+FP+FN); accuracy=(TP+TN)/N; balanced accuracy=(recall+specificity)/2; Jaccard=TP/(TP+FP+FN); over-coding=FP/(TP+FP); under-coding=FN/(TP+FN). Undefined denominators are not replaced with zero.

Cohen's kappa=(Po−Pe)/(1−Pe), where Po=(TP+TN)/N and Pe=[(TP+FP)(TP+FN)+(TN+FP)(TN+FN)]/N². Binary PABAK=2Po−1. Nominal Krippendorff's alpha is computed separately, with Do=(FP+FN)/N, total ratings R=2N, n0=2TN+FP+FN, n1=2TP+FP+FN, De=2n0n1/[R(R−1)], and alpha=1−Do/De. Alpha is not substituted by kappa. This is binary pooled label agreement, rather than a separate multiclass alpha estimator.

Table 1 reports each Q1–Q4, an unweighted mean of their metrics (macro), and pooled counts (micro). Table 2 reports macro metrics across Q1–Q4 within each Human review-type stratum. Table 3 provides the corresponding micro aggregation as a reproducible companion output. Q5 uses all 100 articles. Q6 and Q7 are evaluated where both Human and GPT Q5 belong to {MA, SRQuan}; Q8 requires both to belong to {QA, SRQual}. Agreement means agreement on this broad review group, not necessarily on the exact Q5 category. Method 2 subset sizes are 48/48/35 (GPT-4.1) and 49/49/31 (GPT-5.4).

Composite F1 is Q5 F1 × conditional downstream F1. It is a descriptive product, not joint correctness or cascaded accuracy. Per-category F1 is exported with TP/TN/FP/FN; 0/0 is NE, not zero.

## Intervals and reproducibility boundary

Use 10,000 paired article-level bootstrap samples, seed 20261013, stratified by the four Human Q5 categories. Resample 25 articles with replacement within each stratum, using the same replicate weights across questions and configurations. Aggregate metrics after sampling; reselect conditional subsets in each replicate. The 95% percentile intervals for kappa and PABAK use NumPy linear quantiles. An undefined bootstrap estimate triggers an error rather than replacement or unreported deletion. Composite-product interval endpoints are exported for audit only; their inclusion does not imply they were reported in the manuscript. No Wilson proportion interval is applied to kappa or PABAK.

The intervals quantify article sampling variation conditional on the fixed prompts and fixed responses. They do not include prompt-selection uncertainty or variation from new API calls.

Only the fixed Human/GPT data are required for this analysis. Copyrighted PDFs and extracted full text are neither included nor needed. Remote coding provenance and current rerun limitations are described separately in `gpt_codings/README.md`.
