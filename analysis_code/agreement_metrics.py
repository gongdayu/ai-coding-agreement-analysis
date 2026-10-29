"""Fixed-codebook binary agreement and article-level bootstrap helpers."""
from __future__ import annotations
import re
import numpy as np
CODEBOOK = {
    "Q1": ["AE", "AS", "AG", "CA", "CS", "CG", "PS", "PG", "SU", "TM", "TR"],
    "Q2": ["INC", "PR", "TH", "INT", "DU", "FN", "RX", "DO", "SP", "TT", "OT"],
    "Q3": ["AGE", "SEX", "RAC", "SES", "INS", "WCG", "CCG", "OTH"],
    "Q4": ["BG", "BH", "BN", "BO", "SC", "PS", "PF", "HS", "EN", "OT", "NA"],
    "Q5": ["QA", "SRQUAL", "SRQUAN", "MA"],
    "Q6": ["YES", "NO", "QA", "MIXED", "NA"],
    "Q7": ["YESWORSE", "MIXEDOPP", "MIXED", "NODIFF", "MIXEDBETTER", "BETTER", "QA"],
    "Q8": ["NO", "YES", "OPP", "UNC", "QT"],
}
METRIC_NAMES = ["Precision", "AI Over-coding Rate", "AI Under-coding Rate", "Jaccard Similarity", "Specificity", "Recall", "F-1 Score", "Accuracy", "Balanced Accuracy", "Cohen's Kappa", "PABAK", "Krippendorff's Alpha"]
COUNT_NAMES = ["TP", "TN", "FP", "FN"]
STRATA = ["MA", "QA", "SRQUAL", "SRQUAN"]
B = 10000

def parse(value: object) -> set[str]:
    if value is None or not str(value).strip():
        raise ValueError("Missing answer")
    depth = 0
    chunks, current = [], []
    for char in str(value).strip():
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError(f"Unbalanced parentheses: {value}")
        if char in ",;" and depth == 0:
            chunks.append("".join(current)); current = []
        else:
            current.append(char)
    if depth:
        raise ValueError(f"Unbalanced parentheses: {value}")
    chunks.append("".join(current))
    codes = set()
    for chunk in chunks:
        match = re.match(r"^\s*([A-Za-z0-9]+)\s*(?:\(|$)", chunk)
        if not match:
            raise ValueError(f"Unparseable code: {value!r}: {chunk!r}")
        codes.add(match.group(1).upper())
    return codes

def safe_div(a, b):
    a, b = np.broadcast_arrays(np.asarray(a, dtype=float), np.asarray(b, dtype=float))
    out = np.full(a.shape, np.nan)
    np.divide(a, b, out=out, where=b != 0)
    return out

def metrics(counts):
    c = np.asarray(counts, dtype=float)
    tp, tn, fp, fn = [c[..., i] for i in range(4)]
    n = c.sum(axis=-1)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    po = safe_div(tp + tn, n)
    pe = safe_div((tp + fp) * (tp + fn) + (tn + fp) * (tn + fn), n * n)
    kappa = safe_div(po - pe, 1 - pe)
    ratings = 2 * n
    zeros = 2 * tn + fp + fn
    ones = 2 * tp + fp + fn
    de = safe_div(2 * zeros * ones, ratings * (ratings - 1))
    alpha = 1 - safe_div(safe_div(fp + fn, n), de)
    return np.stack([precision, safe_div(fp, tp + fp), safe_div(fn, tp + fn),
        safe_div(tp, tp + fp + fn), specificity, recall, safe_div(2 * tp, 2 * tp + fp + fn),
        po, (recall + specificity) / 2, kappa, 2 * po - 1, alpha], axis=-1)

def json_float(value):
    return float(value) if np.isfinite(value) else None

def row_result(label, article_ids, original_counts, replicate_counts, *, macro=False):
    original = metrics(original_counts)
    reps = metrics(replicate_counts)
    if macro:
        original = original.mean(axis=0)
        reps = reps.mean(axis=1)
    if not np.isfinite(original).all():
        raise ValueError(f"Undefined original statistic: {label}: {original}")
    ci, valid = {}, {}
    for name in ["Cohen's Kappa", "PABAK"]:
        j = METRIC_NAMES.index(name)
        finite = np.isfinite(reps[:, j])
        valid[name] = int(finite.sum())
        # Undefined bootstrap estimates are audited rather than silently set to zero.
        if not finite.all():
            raise ValueError(f"Undefined bootstrap estimates require review: {label} {name}: {finite.sum()}/{B}")
        ci[name] = np.quantile(reps[:, j], [0.025, 0.975], method="linear").tolist()
    counts = None if macro else dict(zip(COUNT_NAMES, map(int, original_counts)))
    return {"label": label, "counts": counts, "metrics": dict(zip(METRIC_NAMES, map(json_float, original))),
        "N_Articles": len(article_ids), "N_Comparisons": int(np.asarray(original_counts).sum()),
        "article_ids": list(map(int, article_ids)), "ci": ci, "finite_bootstrap_replicates": valid}
