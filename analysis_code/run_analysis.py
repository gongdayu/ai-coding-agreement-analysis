"""Reproduce the fixed-data analyses. No API or unpublished inputs are used."""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
import agreement_metrics as am
from agreement_metrics import CODEBOOK, METRIC_NAMES, COUNT_NAMES, STRATA, parse, metrics, row_result

PROJECT = Path(__file__).resolve().parents[1]
KEYS = ['m1_gpt41','m2_gpt41','m2_gpt54']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_source(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f)
        required={'Article Number'} | {f'{q}_{c}' for q in CODEBOOK for c in ['Human','GPT']}
        if set(reader.fieldnames or []) != required:
            raise ValueError(f'Unexpected columns in {path.name}')
        result={}
        for row in reader:
            i=int(row['Article Number'])
            if i in result:raise ValueError(f'Duplicate Article Number {i}')
            result[i]=row
    if set(result)!=set(range(1,101)):raise ValueError('Expected exactly the public IDs 1 to 100')
    return result

def run(args):
    global B, SEED, ROOT, SOURCES
    B=args.replicates;SEED=args.seed;ROOT=args.out.resolve()
    if B < 2:raise ValueError('At least 2 bootstrap replicates are required')
    if ROOT==PROJECT or PROJECT in ROOT.parents and ROOT.parts[len(PROJECT.parts)] in {'analysis_code','data','validation','gpt_codings'}:
        raise ValueError('Output must not overwrite release sources')
    ROOT.mkdir(parents=True,exist_ok=True);am.B=B
    SOURCES={k:(args.data_dir / (k+'.csv'),'GPT') for k in KEYS}
    data={k:read_source(p) for k,(p,s) in SOURCES.items()}
    manifest={k:{'source':'data/coding_workbooks/'+p.name,'sha256':sha(p),'ai_suffix':s} for k,(p,s) in SOURCES.items()}
    ids = np.array(sorted(data["m2_gpt41"]), dtype=int)
    assert all(set(rows) == set(ids) for rows in data.values())
    human = {int(i): {q: data["m2_gpt41"][int(i)][f"{q}_Human"] for q in CODEBOOK} for i in ids}
    human_changes = []
    for number in ids:
        for q, labels in CODEBOOK.items():
            answer = human[int(number)][q]
            assert answer == data["m2_gpt54"][int(number)][f"{q}_Human"], (number, q, "Human mismatch")
            assert parse(answer) <= set(labels), (number, q, "Human out of pool")
            if q in ["Q5", "Q6", "Q7", "Q8"]:
                assert len(parse(answer)) == 1
            old = data["m1_gpt41"][int(number)][f"{q}_Human"]
            if old != answer:
                human_changes.append({"Article Number": int(number), "Question": q, "Old Human": old, "Analysis Human": answer})
    assert not human_changes, "Human reference must be identical across all public inputs"
    hq5 = np.array([str(human[int(i)]["Q5"]).strip().upper() for i in ids])
    strata = {s: np.flatnonzero(hq5 == s) for s in STRATA}
    assert all(len(x) == 25 for x in strata.values())
    rng = np.random.default_rng(SEED)
    indices = np.concatenate([rng.choice(strata[s], size=(B, len(strata[s])), replace=True) for s in STRATA], axis=1)
    np.save(ROOT / "bootstrap_indices.npy", indices)
    weights = np.zeros((B, len(ids)), dtype=np.int64)
    np.add.at(weights, (np.repeat(np.arange(B), len(ids)), indices.ravel()), 1)
    assert np.all(weights.sum(axis=1) == 100)
    assert all(np.all(weights[:, ix].sum(axis=1) == 25) for ix in strata.values())
    output = {"version": "RR2 fixed-data analysis", "sources": manifest, "codebook": CODEBOOK,
        "human_reference": "Author-confirmed common reference in all three public coding tables", "method1_human_changes": human_changes,
        "bootstrap": {"replicates": B, "seed": SEED, "strata": "Human Q5", "stratum_sizes": {s: len(ix) for s, ix in strata.items()},
            "unit": "article", "paired_all_questions_and_datasets": True, "interval": "95% percentile", "quantile_method": "linear",
            "conditional_subsets_reselected_each_replicate": True, "indices_sha256": sha(ROOT / "bootstrap_indices.npy")}, "datasets": {}}
    audit, analysis_rows, binary_rows = [], [], []
    for key, (_, suffix) in SOURCES.items():
        rows = data[key]
        per_article = np.zeros((100, 8, 4), dtype=np.int64)
        out_of_pool = {q: [] for q in CODEBOOK}
        for a, number in enumerate(ids):
            entry = {"Dataset": key, "Article Number": int(number)}
            for j, (q, labels) in enumerate(CODEBOOK.items()):
                raw_ai = rows[int(number)][f"{q}_{suffix}"]
                h = parse(human[int(number)][q])
                pred = parse(raw_ai)
                if j >= 4:
                    assert len(pred) == 1, (key, number, q, "Multiple single-label codes")
                bad = pred - set(labels)
                if bad:
                    out_of_pool[q].append(int(number))
                    audit.append({"Dataset": key, "Article Number": int(number), "Question": q, "GPT answer": raw_ai, "OOC codes": ";".join(sorted(bad))})
                entry[f"{q}_Human"] = human[int(number)][q]
                entry[f"{q}_GPT"] = raw_ai
                for label in labels:
                    hv, av = label in h, label in pred
                    bucket = 0 if hv and av else 1 if not hv and not av else 2 if av else 3
                    per_article[a, j, bucket] += 1
                    if j < 4 or key != "m1_gpt41":
                        binary_rows.append({"Dataset": key, "Article Number": int(number), "Question": q, "Label": label, "Human": int(hv), "GPT": int(av)})
            analysis_rows.append(entry)
        q5ai = np.array([str(rows[int(i)][f"Q5_{suffix}"]).strip().upper() for i in ids])
        eligible = {"Q5": np.ones(100, dtype=bool),
            "Q6": np.isin(hq5, ["MA", "SRQUAN"]) & np.isin(q5ai, ["MA", "SRQUAN"]),
            "Q7": np.isin(hq5, ["MA", "SRQUAN"]) & np.isin(q5ai, ["MA", "SRQUAN"]),
            "Q8": np.isin(hq5, ["QA", "SRQUAL"]) & np.isin(q5ai, ["QA", "SRQUAL"])}
        tables = {"table1": [], "table2": [], "table3": []}
        qcounts = per_article[:, :4, :].sum(axis=0)
        qreps = np.einsum("ba,aqc->bqc", weights, per_article[:, :4, :])
        for j in range(4):
            tables["table1"].append(row_result(f"Q{j+1}", ids, qcounts[j], qreps[:, j]))
        tables["table1"].append(row_result("Macro-level average", ids, qcounts, qreps, macro=True))
        tables["table1"].append(row_result("Micro-level average", ids, qcounts.sum(axis=0), qreps.sum(axis=1)))
        for s, ix in strata.items():
            counts = per_article[ix, :4].sum(axis=0)
            reps = np.einsum("ba,aqc->bqc", weights[:, ix], per_article[ix, :4])
            label = {"SRQUAL": "SRQual", "SRQUAN": "SRQuan"}.get(s, s)
            tables["table2"].append(row_result(label, ids[ix], counts, reps, macro=True))
            tables["table3"].append(row_result(label, ids[ix], counts.sum(axis=0), reps.sum(axis=1)))
        subgroup_ooc = {}
        if key != "m1_gpt41":
            tables["table4"], tables["table5"] = [], []
            for j in range(4, 8):
                q = f"Q{j+1}"
                mask = eligible[q]
                counts = per_article[mask, j].sum(axis=0)
                reps = weights[:, mask] @ per_article[mask, j]
                tables["table4"].append(row_result(q, ids[mask], counts, reps))
                subgroup_ooc[q] = sorted(set(map(int, ids[mask])) & set(out_of_pool[q]))
            f1 = tables["table4"][0]["metrics"]["F-1 Score"]
            q5reps = metrics(weights @ per_article[:, 4])[:, METRIC_NAMES.index("F-1 Score")]
            for j in range(5, 8):
                q = f"Q{j+1}"
                conditional = tables["table4"][j-4]["metrics"]["F-1 Score"]
                rep_score = q5reps * metrics(weights[:, eligible[q]] @ per_article[eligible[q], j])[:, METRIC_NAMES.index("F-1 Score")]
                assert np.isfinite(rep_score).all()
                tables["table5"].append({"label": q, "metrics": {"Composite F1 score": f1 * conditional},
                    "component_Q5_F1": f1, "component_conditional_F1": conditional,
                    "bootstrap_ci_audit_only": np.quantile(rep_score, [0.025, 0.975], method="linear").tolist()})
        output["datasets"][key] = {"tables": tables, "out_of_pool_responses_all_questions": out_of_pool,
            "out_of_pool_responses_in_table4_subsets": subgroup_ooc,
            "article_question_counts": per_article.tolist(), "article_ids": ids.tolist()}
    for name, records in [("out_of_codebook_audit.csv", audit), ("analysis_input.csv", analysis_rows), ("binary_matrix.csv", binary_rows), ("method1_human_reference_changes.csv", human_changes)]:
        with (ROOT / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]) if records else ["Article Number", "Question", "Old Human", "Analysis Human"])
            writer.writeheader(); writer.writerows(records)
    (ROOT / "statistics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    export_details(output, data, ROOT)
    for key,(path,_) in SOURCES.items():
        if sha(path)!=manifest[key]['sha256']:raise RuntimeError('Input changed during analysis')
    print(json.dumps({'datasets':len(data),'articles_per_dataset':len(ids),'replicates':B,'seed':SEED,'output':str(ROOT)},indent=2))

def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def export_details(output,data,out):
    flat=[];perlabel=[];ooc=[];binary=[]
    for key,d in output['datasets'].items():
        for table,rows in d['tables'].items():
            for r in rows:
                for m,v in r['metrics'].items():
                    ci=r.get('ci',{}).get(m,[None,None])
                    flat.append({'dataset':key,'table':table,'row':r['label'],'metric':m,'value':v,'ci_low':ci[0],'ci_high':ci[1],'N_articles':r.get('N_Articles','')})
        table4={r['label']:r for r in d['tables'].get('table4',[])}
        for q,labels in CODEBOOK.items():
            eligible=list(range(1,101)) if int(q[1:])<=5 else table4.get(q,{}).get('article_ids',[])
            hsets={i:parse(data[key][i][q+'_Human']) for i in eligible}
            gsets={i:parse(data[key][i][q+'_GPT']) for i in eligible}
            n_ooc=sum(bool(gsets[i]-set(labels)) for i in eligible)
            ooc.append({'dataset':key,'question':q,'OOC_responses':n_ooc if eligible else '/','N_responses':len(eligible) if eligible else '/','percent':100*n_ooc/len(eligible) if eligible else '/','OOC_assignments':sum(len(gsets[i]-set(labels)) for i in eligible) if eligible else '/','N_assignments':sum(len(gsets[i]) for i in eligible) if eligible else '/'})
            for label in labels:
                tp=sum(label in hsets[i] and label in gsets[i] for i in eligible)
                tn=sum(label not in hsets[i] and label not in gsets[i] for i in eligible)
                fp=sum(label not in hsets[i] and label in gsets[i] for i in eligible)
                fn=sum(label in hsets[i] and label not in gsets[i] for i in eligible)
                if not eligible:continue
                v=metrics([tp,tn,fp,fn])
                perlabel.append({'dataset':key,'question':q,'label':label,'N':len(eligible),'TP':tp,'TN':tn,'FP':fp,'FN':fn,'Precision':am.json_float(v[0]),'Recall':am.json_float(v[5]),'F1':am.json_float(v[6]),'estimable':bool(2*tp+fp+fn)})
        subset=[r for r in ooc if r['dataset']==key and r['N_responses']!='/']
        ooc.append({'dataset':key,'question':'Overall','OOC_responses':sum(r['OOC_responses'] for r in subset),'N_responses':sum(r['N_responses'] for r in subset),'percent':100*sum(r['OOC_responses'] for r in subset)/sum(r['N_responses'] for r in subset),'OOC_assignments':sum(r['OOC_assignments'] for r in subset),'N_assignments':sum(r['N_assignments'] for r in subset)})
    write_csv(out/'metrics.csv',flat);write_csv(out/'per_label_metrics.csv',perlabel);write_csv(out/'ooc_summary.csv',ooc)
    with (out/'binary_matrix.csv').open(encoding='utf-8-sig',newline='') as f:binary=list(csv.DictReader(f))
    for key in ['m1_gpt41','m2_gpt41']:
        write_csv(out/(key+'_q1q4_binary.csv'),[{k:v for k,v in r.items() if k!='Dataset'} for r in binary if r['Dataset']==key and r['Question'] in ['Q1','Q2','Q3','Q4']])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=PROJECT/'data/coding_workbooks')
    p.add_argument('--out',type=Path,default=Path('rr2_results'))
    p.add_argument('--replicates',type=int,default=10000)
    p.add_argument('--seed',type=int,default=20261013)
    args=p.parse_args();run(args)

if __name__=='__main__':main()
