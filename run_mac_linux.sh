#!/usr/bin/env bash
# bash run_mac_linux.sh [smoke|download|bm25|full|stats|generation|export]          -> Al Ain University experiment
# bash run_mac_linux.sh [multi-smoke|multi-bm25|multi-full|multi-stats|multi-generation] -> six-university experiment
# bash run_mac_linux.sh [multi-malb|multi-malb-cv|multi-v3|multi-malb-generation|multi-all] -> proposed MALB-RAG method   (see run_windows.ps1 for what each mode does)
# bash run_mac_linux.sh [multi-confirm-smoke|multi-confirm|multi-final]   -> confirmatory test of the FROZEN MALB v4 / full final re-run
set -e
MODE=${1:-smoke}
PY=.venv/bin/python
[ -x "$PY" ] || { echo ".venv not found - run: bash setup_mac_linux.sh"; exit 1; }
case "$MODE" in
  smoke)      $PY run_all.py --smoke ;;
  download)   $PY download_full_documents.py ;;
  bm25)       $PY run_all.py --stages audit qc gold matrix retrieval stats figures report --models bm25 ;;
  full)       $PY run_all.py --stages audit qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid ;;
  stats)      $PY run_all.py --stages stats figures report ;;
  generation) $PY run_all.py --stages qc gold matrix generation faithfulness stats figures report ;;
  export)     $PY run_all.py --stages export ;;
  multi-smoke)      $PY run_all.py --config config_multi.yaml --stages qc gold matrix retrieval --smoke ;;
  multi-bm25)       $PY run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 ;;
  multi-full)       $PY run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid ;;
  multi-stats)      $PY run_all.py --config config_multi.yaml --stages stats figures report ;;
  multi-malb)       $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb ;;
  multi-malb-generation) $PY run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report --enable-generation ;;
  multi-malb-cv)    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb_cv ;;
  multi-v3)         $PY run_all.py --config config_multi.yaml --stages qc gold matrix translate malb_cv ;;
  multi-all)        $PY run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report --enable-generation ;;
  multi-generation) $PY run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report ;;
  multi-confirm-smoke) $PY run_all.py --config config_multi.yaml --stages confirm --smoke ;;
  multi-robustness-smoke) $PY run_all.py --config config_multi.yaml --stages robustness --smoke ;;
  multi-robustness) $PY run_all.py --config config_multi.yaml --stages robustness ;;
  multi-confirm)    $PY run_all.py --config config_multi.yaml --stages confirm --enable-generation ;;
  multi-final)      # ONE clean re-run of everything on the GPU (fresh reranker cache), then the confirmatory test.
                    # Earlier outputs are kept, renamed with a time stamp; cached query translations are reused.
                    TS=$(date +%Y%m%d_%H%M)
                    [ -d results_multi ]   && mv results_multi   "results_multi_before_final_$TS"
                    [ -d reports_multi ]   && mv reports_multi   "reports_multi_before_final_$TS"
                    [ -d results_confirm ] && mv results_confirm "results_confirm_before_final_$TS"
                    $PY -c "import torch,sys; ok=torch.cuda.is_available(); print('CUDA available:', ok); sys.exit(0 if ok else 3)" \
                      || { echo "STOP: no GPU visible. multi-final must run on the GPU."; exit 3; }
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix translate
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb_cv --set malb_cv.use_query_translation=false
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb_cv --set "malb_cv.rerank_query_language=[orig]"
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix malb_cv
                    $PY run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report --enable-generation
                    $PY run_all.py --config config_multi.yaml --stages confirm --enable-generation
                    echo "FINAL RUN COMPLETE" ;;
  *) echo "unknown mode: $MODE"; exit 1 ;;
esac
case "$MODE" in multi-robustness*) echo "Done. Results in results_multi/robustness/";;
  multi-confirm*|multi-final) echo "Done. Open results_confirm/confirm20/CONFIRMATORY_REPORT.md and results_confirm/aau60/CONFIRMATORY_REPORT.md";;
  multi-*) echo "Done. Open reports_multi/experiment_report.md and results_multi/tables/AAU_RAG_results.xlsx";;
  *) echo "Done. Open reports/experiment_report.md and results/tables/AAU_RAG_results.xlsx";; esac
