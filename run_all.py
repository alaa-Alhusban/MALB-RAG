#!/usr/bin/env python
"""End-to-end driver.

  python run_all.py                       # all stages, models from config
  python run_all.py --models bm25         # lexical only (CPU)
  python run_all.py --smoke               # quick plumbing test on a 5-need subset
  python run_all.py --stages audit qc gold
Stages: audit qc gold matrix retrieval stats figures generation faithfulness report export
(+ optional stages "malb" (MALB-RAG v1 + ablations), "translate" (query translation, Qwen),
 "malb_cv" (MALB v2/v3/v4, nested cross-validation + frozen config) and "confirm" (one run of the
 FROZEN MALB v4 on the validated confirmatory sets, see src/confirmatory.py); not in the default list)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import annotation, audit, experiment, faithfulness, interaction_analysis, quality_control  # noqa: E402
from src import rag_generation, reporting, visualization  # noqa: E402
from src.preprocessing import Preprocessor  # noqa: E402
from src.utils import ensure_dirs, get_logger, load_config, p, save_json, set_seed  # noqa: E402

ALL = ["audit", "qc", "gold", "matrix", "retrieval", "stats", "figures", "generation", "faithfulness", "report", "export"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--stages", nargs="*", default=ALL)
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-unrepaired-sensitivity", action="store_true")
    ap.add_argument("--enable-generation", action="store_true", help="override generation.enabled = true")
    ap.add_argument("--set", nargs="*", default=[], metavar="KEY=VALUE",
                    help="override a config value for this run, e.g. malb_cv.use_query_translation=false")
    ap.add_argument("--confirm-sets", nargs="*", default=["confirm20", "aau60"],
                    help="test sets for the 'confirm' stage (confirm20, aau60)")
    a = ap.parse_args(argv)

    cfg = load_config(a.config)
    for kv in a.set:                       # e.g. --set malb_cv.rerank_query_language=[orig]
        import yaml
        key, _, val = kv.partition("=")
        node = cfg
        *parents, leaf = key.split(".")
        for k in parents:
            node = node[k]
        if leaf not in node:
            raise SystemExit(f"--set: unknown config key {key}")
        node[leaf] = yaml.safe_load(val)
    if a.enable_generation:
        cfg["generation"]["enabled"] = True
    ensure_dirs(cfg)
    import atexit, os
    lock = p(cfg, "results_dir") / ".run.lock"
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            os.kill(pid, 0)
            raise SystemExit(f"Another run (pid {pid}) is still active for {p(cfg, 'results_dir')}. "
                             "Wait for it to finish (ps aux | grep run_all) before starting a new one.")
        except (ValueError, ProcessLookupError, PermissionError):
            pass   # stale lock from a finished/crashed run
    lock.write_text(str(os.getpid()))
    atexit.register(lambda: lock.exists() and lock.read_text().strip() == str(os.getpid()) and lock.unlink())
    log = get_logger(log_dir=p(cfg, "log_dir"))
    set_seed(cfg["seed"])
    models = a.models or cfg["retrieval"]["models"]
    t0 = time.time()
    log.info("=== run start: stages=%s models=%s smoke=%s overrides=%s", a.stages, models, a.smoke, a.set)

    # --- data stages (always cheap; recomputed so downstream stages are consistent)
    multi = cfg.get("dataset", {}).get("mode") == "multi_university"
    if multi:
        from src import multi_university as mu
        corpus = mu.build_corpus(cfg, log) if "qc" in a.stages else quality_control.load_corpus(cfg)
        queries, needs, auto_qrels = mu.align_gold(cfg, corpus, log)
        splits = mu.make_splits(needs, cfg)
    else:
        corpus = quality_control.build_qc_corpus(cfg, log) if "qc" in a.stages else quality_control.load_corpus(cfg)
        queries, needs, auto_qrels = annotation.align_gold(cfg, corpus, log)
        splits = annotation.make_splits(needs, cfg)
    pdir = p(cfg, "processed_dir")
    if "gold" in a.stages:
        needs.to_csv(pdir / "information_needs.csv", index=False, encoding="utf-8-sig")
        auto_qrels.to_csv(pdir / "qrels_auto_unverified.csv", index=False, encoding="utf-8-sig")
        splits.to_csv(pdir / "splits_need_level.csv", index=False)
        queries.drop(columns=["evidence"], errors="ignore").to_csv(pdir / "queries.csv", index=False, encoding="utf-8-sig")
        if not multi:
            sheet = annotation.write_validation_sheet(cfg, queries, needs, auto_qrels, corpus, splits)
            log.info("Validation sheet: %s", sheet)
    if multi:   # evidence spans were validated by two reviewers; passage alignment is automatic
        qrels = queries[["query_id", "need_id"]].merge(auto_qrels, on="need_id")
        gold_status = "validated"
    else:
        qrels, gold_status = annotation.load_qrels(cfg, auto_qrels, queries)
    log.info("Gold status for this run: %s", gold_status)
    if "audit" in a.stages and not multi:
        audit.run_audit(cfg, log, corpus, queries, needs, auto_qrels, splits)

    pre = Preprocessor(cfg)
    matrix = experiment.build_matrix(cfg, pre)
    if "matrix" in a.stages:
        matrix.to_csv(p(cfg, "results_dir") / "tables" / "experiment_matrix.csv", index=False)
        log.info("Experiment matrix: %d configs (%d available); primary design = 1 + 3x3 = 10",
                 len(matrix), int(matrix.available.sum()))

    out_root = p(cfg, "results_dir")
    if a.smoke:
        keep = sorted(queries.need_id.unique())[:5]
        queries = queries[queries.need_id.isin(keep)].reset_index(drop=True)
        matrix = matrix[matrix.config_id.isin(["P0", "P1-Q", "P1-D", "P1-QD"])]
        out_root = p(cfg, "results_dir") / "smoke"
        models = [m for m in models if m == "bm25"] + ["dense_testdouble"]

    per_q_path = out_root / "metrics"
    if "retrieval" in a.stages:
        per_q = experiment.run_retrieval(cfg, corpus, queries, qrels, splits, matrix, models, log,
                                         "text_display", "smoke" if a.smoke else "main", out_root)
        if cfg["corpus"].get("repair_lam_alef", True) and not a.no_unrepaired_sensitivity and not a.smoke and not multi:
            log.info("Sensitivity run: BM25 on the unrepaired extraction")
            experiment.run_retrieval(cfg, corpus, queries, qrels, splits, matrix, ["bm25"], log,
                                     "text_extracted", "unrepaired", out_root)
    if "malb" in a.stages:
        from src import malb
        malb.run_malb(cfg, corpus, queries, qrels, splits, log, smoke=a.smoke, out_root=out_root)
    if "translate" in a.stages:
        from src import translation
        translation.run_translation(cfg, queries, log, smoke=a.smoke)
    if "malb_cv" in a.stages:
        from src import malb_cv
        malb_cv.run_malb_cv(cfg, corpus, queries, needs, auto_qrels, log, smoke=a.smoke, out_root=out_root)
    if "robustness" in a.stages:
        from src import robustness
        robustness.run_robustness(cfg, corpus, queries, auto_qrels, log, smoke=a.smoke)
        if a.stages == ["robustness"]:
            log.info("=== run finished in %.1fs", time.time() - t0)
            return
    if "confirm" in a.stages:
        from src import confirmatory
        for name in a.confirm_sets:
            confirmatory.run_confirmatory(cfg, name, log, generate=bool(cfg["generation"].get("enabled")), smoke=a.smoke)
        if a.stages == ["confirm"]:
            log.info("=== run finished in %.1fs", time.time() - t0)
            return
    if a.smoke:
        per_q = pd.read_csv(per_q_path / "per_query_metrics_smoke.csv")
        log.info("SMOKE TEST OK: %d per-query rows; mean ndcg@10 by model: %s", len(per_q),
                 per_q[per_q.eligible].groupby("model")["ndcg@10"].mean().round(3).to_dict())
        return

    per_q = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in sorted(per_q_path.glob("per_query_metrics_*.csv"))],
                      ignore_index=True) if list(per_q_path.glob("per_query_metrics_*.csv")) else pd.DataFrame()
    tdir = p(cfg, "results_dir") / "tables"
    sdir = p(cfg, "results_dir") / "statistical_analysis"
    contrasts = inter = gen = None
    if "stats" in a.stages and len(per_q):
        for cols, name in [(["corpus_variant", "model", "index", "config_id", "qlang"], "retrieval_by_config_qlang"),
                           (["corpus_variant", "model", "index", "config_id", "direction"], "retrieval_by_language_direction"),
                           (["corpus_variant", "model", "index", "config_id"], "retrieval_by_config_all_queries"),
                           (["corpus_variant", "model", "index", "config_id", "partition", "qlang"], "retrieval_by_partition")]:
            s = experiment.summarize(per_q, cols)
            s.to_csv(tdir / f"{name}.csv", index=False)
        contrasts = interaction_analysis.all_contrasts(per_q, matrix, cfg, log)
        contrasts.to_csv(sdir / "contrasts_vs_raw_all.csv", index=False)
        inter = interaction_analysis.interaction_table(per_q, matrix, cfg)
        inter.to_csv(sdir / "interaction_IQD_all.csv", index=False)
    else:
        if (sdir / "contrasts_vs_raw_all.csv").exists():
            contrasts = pd.read_csv(sdir / "contrasts_vs_raw_all.csv", keep_default_na=False, na_values=[""])
            inter = pd.read_csv(sdir / "interaction_IQD_all.csv", keep_default_na=False, na_values=[""])

    if "generation" in a.stages:
        rag_generation.run_generation(cfg, corpus, queries, qrels, log)
    if "faithfulness" in a.stages:
        gen = faithfulness.evaluate_answers(cfg, corpus, queries, qrels, log)
    gen_ok = gen is not None and not gen.empty
    summary = None
    if "stats" in a.stages and contrasts is not None:
        summary = interaction_analysis.run_hypotheses(per_q, contrasts, inter, matrix, cfg, gold_status, gen_ok, log)
        if gen_ok:
            summary["hypotheses"]["H5"] = faithfulness.h5_analysis(cfg, gen)
            save_json(summary, sdir / "hypothesis_summary.json")
    if "figures" in a.stages and contrasts is not None:
        visualization.make_all(cfg, per_q, contrasts, inter, gen, log)
    if "report" in a.stages:
        reporting.write_tables_xlsx(cfg)
        reporting.write_experiment_report(cfg, matrix, gold_status, log)
        reporting.write_reproducibility(cfg, matrix, log)
    if "export" in a.stages:
        export_zip(cfg, log)
    log.info("=== run finished in %.1fs", time.time() - t0)


def export_zip(cfg, log):
    out = ROOT.parent / f"{ROOT.name}.zip"
    skip_dirs = {"__pycache__", ".pytest_cache", "cache", "smoke", ".venv", "venv", ".git"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(ROOT.rglob("*")):
            rel = f.relative_to(ROOT.parent)
            if f.is_file() and not (set(f.relative_to(ROOT).parts) & skip_dirs):
                z.write(f, rel)
    log.info("Exported %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


if __name__ == "__main__":
    main()
