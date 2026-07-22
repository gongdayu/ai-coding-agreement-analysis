"""Shared agreement metric utilities for the public analysis scripts.

The functions in this module implement the final binary-expansion agreement
logic used for the paper tables. They intentionally calculate a broader set of
metrics than the public scripts export, because some retained public metrics
depend on the same TP/TN/FP/FN counts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


QUESTION_LABELS = {
    "Q1": ["AE", "AS", "AG", "CA", "CS", "CG", "PS", "PG", "SU", "TM", "TR"],
    "Q2": ["INC", "PR", "TH", "INT", "DU", "FN", "RX", "DO", "SP", "TT", "OT"],
    "Q3": ["AGE", "SEX", "RAC", "SES", "INS", "WCG", "CCG", "OTH"],
    "Q4": ["BG", "BH", "BN", "BO", "SC", "PS", "PF", "HS", "EN", "OT", "NA"],
}

QUESTIONS = ["Q1", "Q2", "Q3", "Q4"]
ARTICLE_TYPES = ["QA", "SRQual", "SRQuan", "MA"]
SINGLE_LABEL_CATEGORIES = {
    "Q5": ["QA", "SRQUAL", "SRQUAN", "MA"],
    "Q6": ["YES", "NO", "QA", "MIXED", "MIXEDOPP"],
    "Q7": ["YESWORSE", "MIXEDOPP", "MIXED", "NODIFF", "MIXEDBETTER", "BETTER", "QA"],
    "Q8": ["NO", "YES", "OPP", "UNC", "QT"],
}
Q5_LOOSE_GROUPS = {
    "MA/SRQuan": {"MA", "SRQUAN"},
    "QA/SRQual": {"QA", "SRQUAL"},
}
Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Counts:
    """Binary agreement counts for article-label or article-category pairs."""

    tp: int
    tn: int
    fp: int
    fn: int

    @property
    def n(self) -> int:
        return self.tp + self.tn + self.fp + self.fn


def split_outside_parentheses(value: object) -> list[str]:
    """Split a multi-label cell on commas that are not inside parentheses."""

    if value is None:
        return []

    text = str(value).strip()
    if not text:
        return []

    parts: list[str] = []
    current: list[str] = []
    depth = 0

    for char in text:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth = max(0, depth - 1)
            current.append(char)
        elif char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)

    final_part = "".join(current).strip()
    if final_part:
        parts.append(final_part)

    return parts


def extract_leading_codes(value: object) -> list[str]:
    """Return leading label-like codes from one multi-label spreadsheet cell."""

    codes: list[str] = []
    for part in split_outside_parentheses(value):
        match = re.match(r"^\s*([A-Za-z0-9]+)", part)
        if match:
            codes.append(match.group(1).upper())
    return codes


def parse_label_set(value: object, allowed_labels: Iterable[str]) -> set[str]:
    """Return allowed label codes found in one multi-label cell."""

    allowed = set(allowed_labels)
    return {code for code in extract_leading_codes(value) if code in allowed}


def clean_single_label(value: object) -> str:
    """Normalize one single-label spreadsheet response."""

    return str(value).strip().upper()


def count_question(df: pd.DataFrame, question: str, ai_suffix: str) -> Counts:
    """Count TP, TN, FP, and FN for one Q1-Q4 multi-label question."""

    labels = QUESTION_LABELS[question]
    human_col = f"{question}_Human"
    ai_col = f"{question}_{ai_suffix}"
    tp = tn = fp = fn = 0

    for _, row in df.iterrows():
        human_labels = parse_label_set(row[human_col], labels)
        ai_labels = parse_label_set(row[ai_col], labels)

        for label in labels:
            ai_selected = label in ai_labels
            human_selected = label in human_labels

            if ai_selected and human_selected:
                tp += 1
            elif not ai_selected and not human_selected:
                tn += 1
            elif ai_selected and not human_selected:
                fp += 1
            else:
                fn += 1

    return Counts(tp=tp, tn=tn, fp=fp, fn=fn)


def single_label_counts(df: pd.DataFrame, question: str, categories: list[str], ai_suffix: str) -> Counts:
    """Count agreement after expanding a single-label question into binaries."""

    human_col = f"{question}_Human"
    ai_col = f"{question}_{ai_suffix}"
    tp = tn = fp = fn = 0

    for _, row in df.iterrows():
        human_answer = clean_single_label(row[human_col])
        ai_answer = clean_single_label(row[ai_col])

        for category in [item.upper() for item in categories]:
            human_selected = human_answer == category
            ai_selected = ai_answer == category

            if ai_selected and human_selected:
                tp += 1
            elif not ai_selected and not human_selected:
                tn += 1
            elif ai_selected and not human_selected:
                fp += 1
            else:
                fn += 1

    return Counts(tp=tp, tn=tn, fp=fp, fn=fn)


def q5_loose_group_subset(df: pd.DataFrame, group_name: str, ai_suffix: str) -> pd.DataFrame:
    """Return rows where human and AI Q5 labels fall in the same broad group."""

    group = Q5_LOOSE_GROUPS[group_name]
    human_in_group = df["Q5_Human"].map(clean_single_label).isin(group)
    ai_in_group = df[f"Q5_{ai_suffix}"].map(clean_single_label).isin(group)
    return df[human_in_group & ai_in_group].copy()


def aggregate_counts(counts_list: Iterable[Counts]) -> Counts:
    """Sum multiple TP/TN/FP/FN count objects."""

    counts = list(counts_list)
    return Counts(
        tp=sum(item.tp for item in counts),
        tn=sum(item.tn for item in counts),
        fp=sum(item.fp for item in counts),
        fn=sum(item.fn for item in counts),
    )


def counts_from_binary_matrix(binary_matrix: pd.DataFrame, question: str | None = None) -> Counts:
    """Count TP/TN/FP/FN from an article-code binary matrix."""

    table = binary_matrix
    if question is not None:
        table = table[table["Question"].astype(str).str.strip() == question]

    ai = table["AI"].astype(int)
    human = table["Human"].astype(int)
    return Counts(
        tp=int(((ai == 1) & (human == 1)).sum()),
        tn=int(((ai == 0) & (human == 0)).sum()),
        fp=int(((ai == 1) & (human == 0)).sum()),
        fn=int(((ai == 0) & (human == 1)).sum()),
    )


def read_coding_workbook(path: Path | str) -> pd.DataFrame:
    """Read one public coding workbook while preserving valid labels such as NA."""

    df = pd.read_excel(path, keep_default_na=False)
    return df[df["Article Number"].astype(str).str.strip() != ""].copy()


def read_binary_matrix(path: Path | str) -> pd.DataFrame:
    """Read one public article-code binary matrix."""

    df = pd.read_excel(path, keep_default_na=False)
    return df[df["Article Number"].astype(str).str.strip() != ""].copy()


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def wilson_ci(metric: float, n: int) -> tuple[float, float]:
    """Wilson-style 95% interval used by the final Table 1 scripts."""

    if n <= 0:
        return (0.0, 0.0)

    p_hat = min(1.0, max(0.0, metric))
    denominator = 1.0 + Z_95**2 / n
    center = (p_hat + Z_95**2 / (2.0 * n)) / denominator
    half_width = (
        Z_95
        * math.sqrt((p_hat * (1.0 - p_hat) + Z_95**2 / (4.0 * n)) / n)
        / denominator
    )
    return (max(0.0, center - half_width), min(1.0, center + half_width))


def kappa_ci(kappa: float, n: int) -> tuple[float, float]:
    """Approximate 95% confidence interval for Cohen's kappa."""

    if n <= 0:
        return (0.0, 0.0)
    se = math.sqrt(max(0.0, 1.0 - kappa**2) / n)
    return (max(-1.0, kappa - Z_95 * se), min(1.0, kappa + Z_95 * se))


def pabak_ci(pabak: float, n: int) -> tuple[float, float]:
    """Approximate 95% confidence interval for PABAK."""

    if n <= 0:
        return (0.0, 0.0)
    po = (pabak + 1.0) / 2.0
    se_po = math.sqrt(max(0.0, po * (1.0 - po)) / n)
    se_pabak = 2.0 * se_po
    return (max(-1.0, pabak - Z_95 * se_pabak), min(1.0, pabak + Z_95 * se_pabak))


def krippendorff_alpha_nominal_binary(counts: Counts) -> float:
    """Compute nominal Krippendorff alpha for binary two-rater data."""

    n_units = counts.n
    if n_units == 0:
        return 0.0

    observed_disagreement = (counts.fp + counts.fn) / n_units
    total_ratings = 2 * n_units
    zero_count = 2 * counts.tn + counts.fp + counts.fn
    one_count = 2 * counts.tp + counts.fp + counts.fn
    expected_agreement = (
        zero_count * (zero_count - 1) + one_count * (one_count - 1)
    ) / (total_ratings * (total_ratings - 1))
    expected_disagreement = 1.0 - expected_agreement

    if expected_disagreement == 0:
        return 1.0 if observed_disagreement == 0 else 0.0

    return 1.0 - observed_disagreement / expected_disagreement


def calculate_metrics(
    counts: Counts,
    *,
    ci_method: str = "kappa_specific",
    alpha_method: str = "nominal_binary",
) -> dict[str, float | int | tuple[float, float]]:
    """Calculate agreement metrics from TP, TN, FP, and FN."""

    tp, tn, fp, fn, n = counts.tp, counts.tn, counts.fp, counts.fn, counts.n
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    over_coding = fp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    under_coding = fn / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    accuracy = (tp + tn) / n if n else 0.0
    jaccard = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    balanced_accuracy = (recall + specificity) / 2.0

    pe = ((tp + fp) * (tp + fn) + (tn + fp) * (tn + fn)) / (n * n) if n else 0.0
    kappa = (accuracy - pe) / (1.0 - pe) if pe != 1.0 else 0.0
    pabak = 2.0 * accuracy - 1.0
    alpha = kappa if alpha_method == "kappa" else krippendorff_alpha_nominal_binary(counts)

    if ci_method == "wilson":
        kappa_interval = wilson_ci(kappa, n)
        pabak_interval = wilson_ci(pabak, n)
    else:
        kappa_interval = kappa_ci(kappa, n)
        pabak_interval = pabak_ci(pabak, n)

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "N_Comparisons": n,
        "Precision": precision,
        "AI Over-coding Rate": over_coding,
        "AI Under-coding Rate": under_coding,
        "Jaccard Similarity": jaccard,
        "Specificity": specificity,
        "Recall": recall,
        "F-1 Score": f1,
        "Accuracy(po)": accuracy,
        "Balanced Accuracy": balanced_accuracy,
        "Cohen's Kappa": kappa,
        "Cohen's Kappa CI": kappa_interval,
        "PABAK": pabak,
        "PABAK CI": pabak_interval,
        "Krippendorff_Alpha": alpha,
    }


def macro_average(
    metric_rows: list[dict[str, float | int | tuple[float, float]]],
    *,
    ci_method: str = "kappa_specific",
) -> dict[str, float | int | tuple[float, float]]:
    """Average per-question metrics for macro-level summaries."""

    scalar_keys = [
        "Precision",
        "AI Over-coding Rate",
        "AI Under-coding Rate",
        "Jaccard Similarity",
        "Specificity",
        "Recall",
        "F-1 Score",
        "Accuracy(po)",
        "Balanced Accuracy",
        "Cohen's Kappa",
        "PABAK",
        "Krippendorff_Alpha",
    ]
    averaged: dict[str, float | int | tuple[float, float]] = {
        key: mean(float(row[key]) for row in metric_rows) for key in scalar_keys
    }
    total_n = sum(int(row["N_Comparisons"]) for row in metric_rows)
    averaged["N_Comparisons"] = total_n
    if ci_method == "wilson":
        averaged["Cohen's Kappa CI"] = wilson_ci(float(averaged["Cohen's Kappa"]), total_n)
        averaged["PABAK CI"] = wilson_ci(float(averaged["PABAK"]), total_n)
    else:
        averaged["Cohen's Kappa CI"] = kappa_ci(float(averaged["Cohen's Kappa"]), total_n)
        averaged["PABAK CI"] = pabak_ci(float(averaged["PABAK"]), total_n)
    return averaged


def format_number(value: float) -> str:
    """Format a table value with up to three decimals, trimming zeros."""

    rounded = round(float(value), 3)
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def format_ci(value: float, ci: tuple[float, float], *, digits: int = 3) -> str:
    """Format a metric with a bracketed confidence interval."""

    return f"{format_number(value)}[{ci[0]:.{digits}f},{ci[1]:.{digits}f}]"


def read_input(path: str) -> pd.DataFrame:
    """Backward-compatible alias for reading a public coding workbook."""

    return read_coding_workbook(path)
