# MALB-RAG: Arabic–English RAG over Multi-Institution Regulations

Code, benchmark and results for the paper

> **Morphological and Cross-Lingual Asymmetry in Arabic–English Retrieval-Augmented Generation: Controlled Evaluation and a Prospectively Confirmed Multi-Institution Pipeline**
> Alaa Alhusban, Brahim Ahmed, Remonda Marid — Al Ain University, UAE.

Students in the UAE ask about academic regulations in Arabic, in English, or in both at once, and many universities publish near-identical rules with different thresholds. This repository studies three failure modes of RAG in that setting — Arabic morphology, query/evidence language mismatch, and confusion between institutions — and provides **MALB-RAG**, a pipeline whose configuration was frozen before its test questions were written and then confirmed once on unseen questions.

## Main results

| | Development (62 needs, held-out CV) | Confirm-20 (16 unseen needs) | AAU-60 (external, 60 needs) |
|---|---|---|---|
| BGE-M3 + reranker (strongest baseline) | 0.571 | 0.594 | 0.866 |
| MALB v4 | 0.613 | 0.657 | **0.875** |
| MALB v4 + institution filter | **0.686** | **0.778** | n/a |

nDCG@10, need-level means. Confirm-20 primary contrast: +0.184 [0.103, 0.274], p<sub>Holm</sub> < 0.001.
With the institution filter, answers never cited another university, and all unanswerable Confirm-20 questions were declined.

Key findings:
* Arabic light stemming helps **BM25 only when applied to both queries and passages**, and harms dense retrieval (BGE-M3, mE5).
* Query translation is partly undone when the cross-encoder scores passages against a query in another language; **language-matched reranking** fixes English→Arabic retrieval (0.302 → 0.481).
* Better retrieval alone does **not** stop answers drawn from the wrong institution; an institution filter does.

## Repository layout

```
src/                      pipeline: preprocessing, BM25 / mE5 / BGE-M3 / hybrid, MALB-RAG, reranking,
                          generation, statistics, confirmatory test (confirmatory.py), robustness.py
run_all.py                single entry point (stages: qc gold matrix retrieval stats figures report
                          malb translate malb_cv generation faithfulness confirm robustness)
config_multi.yaml         six-university experiment;   config.yaml: original AAU experiment
data/multi_university/    72 needs, 216 queries, SOURCES.csv (URL, edition, SHA-256 of every handbook)
data/confirmatory/        frozen configuration, Confirm-20 needs/queries, AAU-60 corrections
data/original/AAU_RAG_Project/   original AAU benchmark (AAU-60)
annotation/               anonymised reviewer agreement and blind answer ratings
results/                  final results (development, confirmatory, robustness)
paper/figures/            figures of the paper
tests/                    unit tests (pytest)
```

## Data notice

The university handbooks are **not redistributed**. `data/multi_university/SOURCES.csv` lists the public URL, edition, page count and SHA-256 of every file used. Universities update their handbooks; a different edition gives different pages, so check the checksum after downloading.

## Reproducing the experiments

Requirements: Python 3.10–3.12; an NVIDIA GPU with ≥ 20 GB is recommended (all results in the paper were produced on one RTX 4000 Ada, about 2.5 h for everything). Models are downloaded from Hugging Face on first use: BAAI/bge-m3, BAAI/bge-reranker-v2-m3, intfloat/multilingual-e5-large, Qwen/Qwen2.5-7B-Instruct.

```bash
python3 -m venv .venv && bash setup_mac_linux.sh          # installs requirements, runs the tests

python download_university_sources.py                      # handbooks -> data/original/universities/
python extract_handbooks.py                                # -> data/multi_university/pages.csv

bash run_mac_linux.sh multi-smoke                          # 1-minute plumbing check (test doubles)
bash run_mac_linux.sh multi-final                          # full re-run on the GPU + confirmatory test
```

Individual parts: `multi-full` (baselines and H1–H4), `multi-malb` (MALB v1), `multi-malb-cv` / `multi-v3` (MALB v2–v4), `multi-malb-generation` (answers), `multi-confirm` (confirmatory test), `multi-robustness` (latency and comparator rankings). See `HOW_TO_RUN_EN.md`.

## Confirmatory protocol

The MALB v4 configuration (`data/confirmatory/FROZEN_MALB_v4_config.json`) was selected by nested cross-validation on the development needs and frozen on 2026-11-13, before the Confirm-20 questions were written. Before any confirmatory metric is computed, `src/confirmatory.py` writes `registration.json` with SHA-256 hashes of the frozen configuration and the test data; a later run stops if either has changed. The registration records of the reported run are in `results/confirmatory/*/registration.json`.

## Citation

See `CITATION.cff`. The paper reference will be added on publication.

## License

Code and annotation files: MIT (see `LICENSE`). Handbooks: property of the respective universities.
