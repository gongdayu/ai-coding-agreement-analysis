"""Generate public GPT-4.1 agreement tables from released datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from agreement_metrics import (
    ARTICLE_TYPES,
    QUESTIONS,
    SINGLE_LABEL_CATEGORIES,
    aggregate_counts,
    calculate_metrics,
    counts_from_binary_matrix,
    format_ci,
    format_number,
    macro_average,
    q5_loose_group_subset,
    read_binary_matrix,
    read_coding_workbook,
    single_label_counts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_SUFFIX = "GPT 4.1"
ARTICLE_DISPLAY_ORDER = {"QA": 0, "SRQual": 1, "SRQuan": 2, "MA": 3}


def display_article_type(value: str) -> str:
    mapping = {"QA": "QA", "SRQUAL": "SRQual", "SRQUAN": "SRQuan", "MA": "MA"}
    return mapping[str(value).strip().upper()]


def metric_ci(value: Any, ci: tuple[float, float]) -> str:
    return format_ci(float(value), ci)


def question_metrics(binary_matrix: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for question in QUESTIONS:
        counts = counts_from_binary_matrix(binary_matrix, question)
        metrics = calculate_metrics(counts, alpha_method="kappa")
        metrics["Question"] = question
        rows.append(metrics)
    return rows


def table1_public(binary_matrix: pd.DataFrame, *, adjusted_column: str, method1_legacy_macro_ci: bool) -> pd.DataFrame:
    metric_rows = question_metrics(binary_matrix)
    macro = macro_average(metric_rows, ci_method="wilson")
    if method1_legacy_macro_ci:
        macro["Cohen's Kappa CI"] = (
            sum(row["Cohen's Kappa CI"][0] for row in metric_rows) / len(metric_rows),
            sum(row["Cohen's Kappa CI"][1] for row in metric_rows) / len(metric_rows),
        )
    micro = calculate_metrics(
        aggregate_counts(
            counts_from_binary_matrix(binary_matrix, question)
            for question in QUESTIONS
        ),
        ci_method="wilson",
        alpha_method="kappa",
    )

    rows: list[dict[str, Any]] = []
    for item in metric_rows + [
        {"Question": "Macro-level average", **macro},
        {"Question": "Micro-level average", **micro},
    ]:
        rows.append(
            {
                "Question": item["Question"],
                "Precision": format_number(item["Precision"]),
                "AI Over-coding Rate": format_number(item["AI Over-coding Rate"]),
                "AI Under-coding Rate": format_number(item["AI Under-coding Rate"]),
                "Jaccard Similarity": format_number(item["Jaccard Similarity"]),
                "Recall": format_number(item["Recall"]),
                "F-1 Score": format_number(item["F-1 Score"]),
                "Cohens_Kappa_CI": metric_ci(item["Cohen's Kappa"], item["Cohen's Kappa CI"]),
                adjusted_column: metric_ci(item["PABAK"], item["PABAK CI"]),
                "N Articles": 100,
            }
        )
    return pd.DataFrame(rows)


def table2b_public(binary_matrix: pd.DataFrame, coding_df: pd.DataFrame) -> pd.DataFrame:
    q5_lookup = coding_df[["Article Number", "Q5_Human"]].copy()
    q5_lookup["Article Number"] = q5_lookup["Article Number"].astype(str)
    q5_lookup["Article"] = q5_lookup["Q5_Human"].map(display_article_type)
    matrix = binary_matrix.copy()
    matrix["Article Number"] = matrix["Article Number"].astype(str)
    matrix = matrix.merge(q5_lookup[["Article Number", "Article"]], on="Article Number", how="left")

    rows = []
    for article_type in ARTICLE_TYPES:
        subset = matrix[matrix["Article"] == article_type]
        metrics = []
        for question in QUESTIONS:
            counts = counts_from_binary_matrix(subset, question)
            metrics.append(calculate_metrics(counts, alpha_method="kappa"))
        macro = macro_average(metrics)
        rows.append(
            {
                "Article": article_type,
                "Precision": format_number(macro["Precision"]),
                "Recall": format_number(macro["Recall"]),
                "Jaccard Similarity": format_number(macro["Jaccard Similarity"]),
                "AI Over-coding Rate": format_number(macro["AI Over-coding Rate"]),
                "AI Under-coding Rate": format_number(macro["AI Under-coding Rate"]),
                "Cohen Kappa [CI]": metric_ci(macro["Cohen's Kappa"], macro["Cohen's Kappa CI"]),
                "Adjusted kappa [CI]": metric_ci(macro["PABAK"], macro["PABAK CI"]),
                "Number of articles": len(set(subset["Article Number"])),
            }
        )
    table = pd.DataFrame(rows)
    return table.sort_values(by="Article", key=lambda col: col.map(ARTICLE_DISPLAY_ORDER)).reset_index(drop=True)


def single_label_table(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    q8_categories = ["NO", "YES", "UNC", "QT"]
    specifications = {
        "Q5": (df, SINGLE_LABEL_CATEGORIES["Q5"]),
        "Q6": (q5_loose_group_subset(df, "MA/SRQuan", AI_SUFFIX), SINGLE_LABEL_CATEGORIES["Q6"]),
        "Q7": (q5_loose_group_subset(df, "MA/SRQuan", AI_SUFFIX), SINGLE_LABEL_CATEGORIES["Q7"]),
        "Q8": (q5_loose_group_subset(df, "QA/SRQual", AI_SUFFIX), q8_categories),
    }

    metrics_by_question: dict[str, dict[str, Any]] = {}
    rows = []
    for question, (subset, categories) in specifications.items():
        counts = single_label_counts(subset, question, categories, AI_SUFFIX)
        metrics = calculate_metrics(counts)
        metrics_by_question[question] = metrics
        kappa_ci = metrics["Cohen's Kappa CI"]
        pabak_ci = metrics["PABAK CI"]
        rows.append(
            {
                "Question": question,
                "F1_Score": format_number(metrics["F-1 Score"]),
                "Cohen_Kappa": format_number(metrics["Cohen's Kappa"]),
                "Cohen_Kappa_CI": f"[{kappa_ci[0]:.3f},{kappa_ci[1]:.3f}]",
                "PABAK": format_number(metrics["PABAK"]),
                "PABAK_CI": f"[{pabak_ci[0]:.3f},{pabak_ci[1]:.3f}]",
                "N_Articles": len(subset),
            }
        )
    return pd.DataFrame(rows), metrics_by_question


def table5_public(metrics_by_question: dict[str, dict[str, Any]]) -> pd.DataFrame:
    q5_f1 = float(metrics_by_question["Q5"]["F-1 Score"])
    return pd.DataFrame(
        {
            "Question": ["Q6", "Q7", "Q8"],
            "Cascaded accuracy": [
                format_number(q5_f1 * float(metrics_by_question[question]["F-1 Score"]))
                for question in ["Q6", "Q7", "Q8"]
            ],
        }
    )


def write_outputs(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = output_dir / "gpt41_public_tables.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        for sheet_name, table in tables.items():
            table.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            table.to_csv(output_dir / f"{sheet_name}.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate public GPT-4.1 agreement tables.")
    parser.add_argument(
        "--method1-binary-matrix",
        default="data/article_code_binary_datasets/gpt41_method1_q1q4_binary_matrix.xlsx",
        help="Released GPT-4.1 Method 1 Q1-Q4 article-code binary matrix.",
    )
    parser.add_argument(
        "--method2-binary-matrix",
        default="data/article_code_binary_datasets/gpt41_method2_q1q4_binary_matrix.xlsx",
        help="Released GPT-4.1 Method 2 Q1-Q4 article-code binary matrix.",
    )
    parser.add_argument(
        "--method2-coding-workbook",
        default="data/coding_workbooks/100 Articles_Human VS GPT-4.1_Method2.xlsx",
        help="Released GPT-4.1 Method 2 public coding workbook.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/gpt41",
        help="Directory where public output tables will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    method1_matrix = read_binary_matrix((REPOSITORY_ROOT / args.method1_binary_matrix).resolve())
    method2_matrix = read_binary_matrix((REPOSITORY_ROOT / args.method2_binary_matrix).resolve())
    method2_coding = read_coding_workbook((REPOSITORY_ROOT / args.method2_coding_workbook).resolve())
    output_dir = (REPOSITORY_ROOT / args.output_dir).resolve()

    table4, single_metrics = single_label_table(method2_coding)
    tables = {
        "table1a_method1_questions": table1_public(
            method1_matrix,
            adjusted_column="Adjusted kappa_CI",
            method1_legacy_macro_ci=True,
        ),
        "table1b_method2_questions": table1_public(
            method2_matrix,
            adjusted_column="PABAK_CI",
            method1_legacy_macro_ci=False,
        ),
        "table2b_method2_macro_by_type": table2b_public(method2_matrix, method2_coding),
        "table4_single_label": table4,
        "table5_cascaded_accuracy": table5_public(single_metrics),
    }
    write_outputs(tables, output_dir)
    print(f"Public GPT-4.1 tables written to: {output_dir}")


if __name__ == "__main__":
    main()
