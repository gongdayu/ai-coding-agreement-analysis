"""Export TP/TN/FP/FN audit tables from the released public datasets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from agreement_metrics import (
    ARTICLE_TYPES,
    QUESTIONS,
    SINGLE_LABEL_CATEGORIES,
    calculate_metrics,
    count_question,
    counts_from_binary_matrix,
    extract_leading_codes,
    q5_loose_group_subset,
    read_binary_matrix,
    read_coding_workbook,
    single_label_counts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DISPLAY_ORDER = {"QA": 0, "SRQual": 1, "SRQuan": 2, "MA": 3}


def display_article_type(value: str) -> str:
    mapping = {"QA": "QA", "SRQUAL": "SRQual", "SRQUAN": "SRQuan", "MA": "MA"}
    return mapping[str(value).strip().upper()]


def metric_row(
    *,
    dataset: str,
    section: str,
    question: str,
    counts: Any,
    n_articles: int | str = "",
    n_categories: int | str = "",
    article: str = "",
    level: str = "",
    alpha_method: str = "kappa",
) -> dict[str, Any]:
    metrics = calculate_metrics(counts, alpha_method=alpha_method)
    return {
        "Dataset": dataset,
        "Section": section,
        "Question": question,
        "Article": article,
        "Level": level,
        "N_Articles": n_articles,
        "N_Categories": n_categories,
        "TP": counts.tp,
        "TN": counts.tn,
        "FP": counts.fp,
        "FN": counts.fn,
        "N_Comparisons": counts.n,
        "Precision": metrics["Precision"],
        "AI Over-coding Rate": metrics["AI Over-coding Rate"],
        "AI Under-coding Rate": metrics["AI Under-coding Rate"],
        "Jaccard Similarity": metrics["Jaccard Similarity"],
        "Specificity": metrics["Specificity"],
        "Recall": metrics["Recall"],
        "F-1 Score": metrics["F-1 Score"],
        "Accuracy(po)": metrics["Accuracy(po)"],
        "Balanced Accuracy": metrics["Balanced Accuracy"],
        "Cohen's Kappa": metrics["Cohen's Kappa"],
        "Cohen's Kappa CI": metrics["Cohen's Kappa CI"],
        "PABAK": metrics["PABAK"],
        "PABAK CI": metrics["PABAK CI"],
        "Krippendorff_Alpha": metrics["Krippendorff_Alpha"],
    }


def q1q4_counts_from_binary_matrix(binary_matrix: pd.DataFrame, dataset: str) -> pd.DataFrame:
    rows = []
    for question in QUESTIONS:
        rows.append(
            metric_row(
                dataset=dataset,
                section="Q1-Q4 article-code binary matrix counts",
                question=question,
                counts=counts_from_binary_matrix(binary_matrix, question),
            )
        )
    return pd.DataFrame(rows)


def q1q4_counts_from_coding_workbook(df: pd.DataFrame, ai_suffix: str, dataset: str) -> pd.DataFrame:
    rows = []
    for question in QUESTIONS:
        rows.append(
            metric_row(
                dataset=dataset,
                section="Q1-Q4 coding workbook counts",
                question=question,
                counts=count_question(df, question, ai_suffix),
            )
        )
    return pd.DataFrame(rows)


def article_type_counts_from_binary_matrix(
    binary_matrix: pd.DataFrame,
    coding_df: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    q5_lookup = coding_df[["Article Number", "Q5_Human"]].copy()
    q5_lookup["Article Number"] = q5_lookup["Article Number"].astype(str)
    q5_lookup["Article"] = q5_lookup["Q5_Human"].map(display_article_type)
    matrix = binary_matrix.copy()
    matrix["Article Number"] = matrix["Article Number"].astype(str)
    matrix = matrix.merge(q5_lookup[["Article Number", "Article"]], on="Article Number", how="left")

    rows = []
    for article in ARTICLE_TYPES:
        subset = matrix[matrix["Article"] == article]
        for question in QUESTIONS:
            rows.append(
                metric_row(
                    dataset=dataset,
                    section="Q1-Q4 article-type counts",
                    question=question,
                    article=article,
                    counts=counts_from_binary_matrix(subset, question),
                    n_articles=len(set(subset["Article Number"])),
                )
            )
    return pd.DataFrame(rows)


def article_type_counts_from_coding_workbook(df: pd.DataFrame, ai_suffix: str, dataset: str) -> pd.DataFrame:
    rows = []
    typed = df.copy()
    typed["Article"] = typed["Q5_Human"].map(display_article_type)
    for article in ARTICLE_TYPES:
        subset = typed[typed["Article"] == article]
        for question in QUESTIONS:
            rows.append(
                metric_row(
                    dataset=dataset,
                    section="Q1-Q4 article-type counts",
                    question=question,
                    article=article,
                    counts=count_question(subset, question, ai_suffix),
                    n_articles=len(subset),
                )
            )
    return pd.DataFrame(rows)


def single_label_counts_table(
    df: pd.DataFrame,
    ai_suffix: str,
    dataset: str,
    *,
    q8_categories: list[str],
) -> pd.DataFrame:
    specifications = {
        "Q5": ("All articles", df, SINGLE_LABEL_CATEGORIES["Q5"]),
        "Q6": ("Loose MA/SRQuan Q5 group", q5_loose_group_subset(df, "MA/SRQuan", ai_suffix), SINGLE_LABEL_CATEGORIES["Q6"]),
        "Q7": ("Loose MA/SRQuan Q5 group", q5_loose_group_subset(df, "MA/SRQuan", ai_suffix), SINGLE_LABEL_CATEGORIES["Q7"]),
        "Q8": ("Loose QA/SRQual Q5 group", q5_loose_group_subset(df, "QA/SRQual", ai_suffix), q8_categories),
    }
    rows = []
    for question, (section, subset, categories) in specifications.items():
        rows.append(
            metric_row(
                dataset=dataset,
                section=section,
                question=question,
                counts=single_label_counts(subset, question, categories, ai_suffix),
                n_articles=len(subset),
                n_categories=len(categories),
                alpha_method="nominal_binary",
            )
        )
    return pd.DataFrame(rows)


def unknown_multi_label_codes(df: pd.DataFrame, ai_suffix: str, dataset: str) -> pd.DataFrame:
    rows = []
    for question in QUESTIONS:
        allowed = set(SINGLE_LABEL_CATEGORIES.get(question, []))
        if question in {"Q1", "Q2", "Q3", "Q4"}:
            from agreement_metrics import QUESTION_LABELS

            allowed = set(QUESTION_LABELS[question])
        for _, row in df.iterrows():
            for source, column in [("Human", f"{question}_Human"), ("AI", f"{question}_{ai_suffix}")]:
                codes = extract_leading_codes(row[column])
                unknown = sorted(set(codes) - allowed)
                if unknown:
                    rows.append(
                        {
                            "Dataset": dataset,
                            "Article Number": row["Article Number"],
                            "Question": question,
                            "Source": source,
                            "Column": column,
                            "Cell Value": row[column],
                            "Unknown Codes": ", ".join(unknown),
                            "Handling": "Ignored because the code is outside the fixed public codebook.",
                        }
                    )
    return pd.DataFrame(rows)


def write_table(output_dir: Path, name: str, table: pd.DataFrame, writer: pd.ExcelWriter) -> None:
    table.to_excel(writer, sheet_name=name[:31], index=False)
    table.to_csv(output_dir / f"{name}.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export final agreement audit tables.")
    parser.add_argument(
        "--output-dir",
        default="outputs/audit_counts",
        help="Directory where detailed audit outputs will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = (REPOSITORY_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    coding_dir = REPOSITORY_ROOT / "data" / "coding_workbooks"
    binary_dir = REPOSITORY_ROOT / "data" / "article_code_binary_datasets"

    gpt41_method1_matrix = read_binary_matrix(binary_dir / "gpt41_method1_q1q4_binary_matrix.xlsx")
    gpt41_method2_matrix = read_binary_matrix(binary_dir / "gpt41_method2_q1q4_binary_matrix.xlsx")
    gpt41_method2_coding = read_coding_workbook(coding_dir / "100 Articles_Human VS GPT-4.1_Method2.xlsx")
    gpt54_coding = read_coding_workbook(coding_dir / "100 Articles_Human VS GPT-5.4_Method2.xlsx")

    tables: dict[str, pd.DataFrame] = {
        "gpt41_method1_q1q4_counts": q1q4_counts_from_binary_matrix(gpt41_method1_matrix, "GPT-4.1 Method 1"),
        "gpt41_method2_q1q4_counts": q1q4_counts_from_binary_matrix(gpt41_method2_matrix, "GPT-4.1 Method 2"),
        "gpt41_method2_by_type": article_type_counts_from_binary_matrix(
            gpt41_method2_matrix,
            gpt41_method2_coding,
            "GPT-4.1 Method 2",
        ),
        "gpt41_method2_single_label": single_label_counts_table(
            gpt41_method2_coding,
            "GPT 4.1",
            "GPT-4.1 Method 2",
            q8_categories=["NO", "YES", "UNC", "QT"],
        ),
        "gpt54_q1q4_counts": q1q4_counts_from_coding_workbook(gpt54_coding, "GPT 5.4", "GPT-5.4 Method 2"),
        "gpt54_by_type": article_type_counts_from_coding_workbook(gpt54_coding, "GPT 5.4", "GPT-5.4 Method 2"),
        "gpt54_single_label": single_label_counts_table(
            gpt54_coding,
            "GPT 5.4",
            "GPT-5.4 Method 2",
            q8_categories=["NO", "YES", "OPP", "UNC", "QT"],
        ),
        "gpt54_unknown_labels": unknown_multi_label_codes(gpt54_coding, "GPT 5.4", "GPT-5.4 Method 2"),
    }

    workbook = output_dir / "public_dataset_audit_tables.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        for name, table in tables.items():
            write_table(output_dir, name, table, writer)

    print(f"Agreement audit tables written to: {output_dir}")


if __name__ == "__main__":
    main()
