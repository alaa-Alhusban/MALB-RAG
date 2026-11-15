# How to run (English quick guide)

The full step-by-step guide is in **HOW_TO_RUN_AR.md**, which is in Arabic. This page is the short English version.

## Requirements
- **Python 3.12.** Python 3.15 fails to build `pyyaml` and `lz4` on Windows.
- About 15 GB free disk space and preferably 16 GB RAM.
- Internet access for installation and for the first download of the models.

## 1. Unzip
Unzip the archive. Work inside the folder that **directly contains `run_all.py`**. Windows often creates a nested folder with the same name.

## 2. Setup (once)
Windows PowerShell:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\setup_windows.ps1
```
macOS / Linux:
```bash
bash setup_mac_linux.sh
```
Expected result: `29 passed, 4 skipped`, then `Setup finished`. Four data tests wait for the first run; after it the result is `33 passed`.

## 2b. Corpus expansion (recommended for publication)
Without this step the collection has only 60 passages, which makes retrieval unrealistically easy.
```powershell
.\run_windows.ps1 download          # or: python download_full_documents.py
```
This downloads the 7 full public handbooks into `data/original/full_documents/`. If a download fails, save the file manually under the exact name listed in `SOURCES_TO_DOWNLOAD.csv`.

Every non-gold page is then added as a distractor passage. Gold passages, their IDs and the annotations stay unchanged. Distractors that contain a gold evidence span are labelled relevant automatically and flagged for review.

Dense encoding of the larger collection takes several hours on a CPU, so use a GPU if you can. Scores will be lower than in `reference_results_4models/`. That is expected.

## 3. Run
| Command (Windows) | macOS / Linux | What it does | CPU time |
|---|---|---|---|
| `.\run_windows.ps1 smoke` | `bash run_mac_linux.sh smoke` | Plumbing test | 1–2 min |
| `.\run_windows.ps1 bm25` | `bash run_mac_linux.sh bm25` | Full design, BM25 only | ~1 min |
| `.\run_windows.ps1 full` | `bash run_mac_linux.sh full` | BM25 + mE5-large + BGE-M3 + Hybrid | ~1–1.5 h on first run |
| `.\run_windows.ps1 stats` | `bash run_mac_linux.sh stats` | Recompute statistics, figures and reports | 3–10 min |
| `.\run_windows.ps1 generation` | `bash run_mac_linux.sh generation` | RAG answers + faithfulness (H5) | needs an API key |

Check which models ran:
```powershell
type results\metrics\model_status_main.json
```
Each model should show `"status": "RUN"`.

## 4. Results
- `reports/experiment_report.md`
- `results/tables/AAU_RAG_results.xlsx`
- `results/figures/`
- `results/statistical_analysis/`

Compare your results with `reference_results_4models/`. BM25 must match exactly. Dense models can differ slightly, at about the third decimal, between GPU (fp16) and CPU (fp32).

## Optional steps
- **CAMeL Tools segmentation (P2):**
  ```
  pip install camel-tools --no-deps
  pip install docopt cachetools editdistance emoji pyrsistent muddler dill
  camel_data -i light
  ```
  Then run `full` again.
- **Answer generation:** in `config.yaml` set `generation.enabled: true` and `backend: openai` (or `anthropic`). Put the API key in an environment variable such as `OPENAI_API_KEY`. Never put a key in a file.
- **Gold validation:** fill in `data/annotations/gold_validation_sheet_TEMPLATE.xlsx` and save it as `gold_validation_sheet.xlsx`. Then run `stats` again.
- **Google Colab:** use `notebooks/AAU_RAG_Colab.ipynb` with a T4 GPU.

Every result is **preliminary** until the machine-generated gold annotations have been validated by a person.

---

# Six-university experiment

- **What it is:** the same pipeline on 6 UAE universities (11 handbooks, 1,634 passages) and 216 validated queries (72 needs × 3 variants: 62 answerable, 10 unanswerable).
- **Configuration:** `config_multi.yaml`. Outputs go to `results_multi/` and `reports_multi/`.
- **How to run:**
  - Linux: `bash run_mac_linux.sh multi-smoke | multi-bm25 | multi-full | multi-stats | multi-generation`
  - Windows: `.\run_windows.ps1 multi-...` with the same modes.
- **Relevance:**
  - Only passages from the question's own university can be relevant.
  - Grade 2 passages count anywhere in that university's handbook.
  - Grade 1 passages count only within ±1 page of the cited page.
- **Split:** need-level dev/test split (24/48), stratified by university × evidence language.
- **Reference results:** `reference_results_multi_bm25/` holds the BM25 results from our run; `multi-bm25` should reproduce them exactly.

---

# Proposed method: MALB-RAG (`src/malb.py`)

**Pipeline:**
1. Adaptive morphological preprocessing on the BM25 channel. One method per query language, chosen from P0, P1, P2 (or P2H) and P3 and applied to both sides.
2. BM25 and BGE-M3 search the Arabic and English indexes separately.
3. Language-balanced weighted RRF (c = 60). The BM25 weight is chosen per query language from {0, .25, .5, .75, 1}.
4. bge-reranker-v2-m3 re-scores the top 50.
5. Qwen2.5-7B-Instruct generates the answer from the top 5 passages, or abstains.

**Tuning:** only the method (1) and the weight (3) are tuned, and only on DEV needs. The final comparisons use TEST needs, with need-level bootstrap CIs, sign-flip tests and Holm correction.

**Ablations:** no reranker, no language balance, fixed w = 0.5, P0 only, BM25 only, dense only.

**Run modes:** `multi-malb`, `multi-malb-generation`, and `multi-all`, which runs everything in sequence. Outputs are in `results_multi/malb/`.

# MALB v2–v4 and the confirmatory test

* **v2** (`multi-malb-cv`): nested 5-fold cross-validation by need over a pre-specified grid (chunking, BM25 preprocessing, dense document preprocessing, fusion weight, language-balanced lists, rerank depth).
* **v3/v4** (`multi-v3`): adds query translation (Qwen2.5-7B, cached) and the reranker query language (`orig` / `matched`). The configuration selected on all 72 needs is frozen in `results_multi/malb_cv_v4/FROZEN_MALB_v4_config.json`.
* **Confirmatory test** (`src/confirmatory.py`): the frozen configuration (registered copy: `data/confirmatory/FROZEN_MALB_v4_config.json`, 2026-11-13) is run once, unchanged, on
  * `confirm20` — 20 new needs × 3 variants on the six-university corpus, written after freezing (two reviewers, 90 % agreement, AC1 0.885);
  * `aau60` — the original AAU 60 needs × 3 variants on the original 60-passage corpus, with the adjudicated corrections in `data/confirmatory/aau60_corrections.json` (90 %, AC1 0.895).

  `registration.json` stores hashes of the frozen configuration and the test data before any metric is computed; a later run stops if either changed. Primary hypotheses (need-level paired tests, Holm): MALB_v4_unifilter > BGE-M3+reranker and MALB_v4 > BGE-M3+reranker on nDCG@10.

```bash
bash run_mac_linux.sh multi-confirm-smoke                        # plumbing check, test doubles
nohup bash run_mac_linux.sh multi-confirm > confirm.log 2>&1 &   # real run (GPU), retrieval + generation
nohup bash run_mac_linux.sh multi-final > final.log 2>&1 &       # clean GPU re-run of everything, then the confirmatory test
```
Reports: `results_confirm/<set>/CONFIRMATORY_REPORT.md`.
