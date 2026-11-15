# Run the experiment on Windows (PowerShell), from the folder that contains run_all.py.
#   .\run_windows.ps1 smoke        quick plumbing test (1-2 minutes)
#   .\run_windows.ps1 bm25         full experiment, BM25 only (about 1 minute + statistics)
#   .\run_windows.ps1 full         all four retrievers: BM25, mE5, BGE-M3, Hybrid (CPU: about 1-1.5 hours first time)
#   .\run_windows.ps1 stats        recompute statistics, figures and reports from existing runs
#   .\run_windows.ps1 generation   RAG answer generation + faithfulness (needs config.yaml generation.enabled: true and an API key)
#   .\run_windows.ps1 download     download the 7 full handbooks (corpus expansion with distractor passages)
#   .\run_windows.ps1 export       write a clean ZIP of the project next to this folder
#   Six-university experiment (config_multi.yaml, results in results_multi/):
#   .\run_windows.ps1 multi-smoke | multi-bm25 | multi-full | multi-stats | multi-generation
param(
    [ValidateSet("smoke", "download", "bm25", "full", "stats", "generation", "export", "multi-smoke", "multi-bm25", "multi-full", "multi-stats", "multi-generation", "multi-malb", "multi-malb-cv", "multi-v3", "multi-malb-generation", "multi-confirm-smoke", "multi-confirm")]
    [string]$Mode = "smoke"
)

$vpy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $vpy)) {
    Write-Host ".venv not found. Run .\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

switch ($Mode) {
    "smoke"      { & $vpy run_all.py --smoke }
    "multi-smoke"      { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix retrieval --smoke }
    "multi-bm25"       { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 }
    "multi-full"       { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid }
    "multi-confirm-smoke" { & $vpy run_all.py --config config_multi.yaml --stages confirm --smoke }
    "multi-confirm"    { & $vpy run_all.py --config config_multi.yaml --stages confirm --enable-generation }
    "multi-v3"         { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix translate malb_cv }
    "multi-malb-cv"    { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix malb_cv }
    "multi-malb"       { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix malb }
    "multi-malb-generation" { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report --enable-generation }
    "multi-stats"      { & $vpy run_all.py --config config_multi.yaml --stages stats figures report }
    "multi-generation" { & $vpy run_all.py --config config_multi.yaml --stages qc gold matrix generation faithfulness stats figures report }
    "download"   { & $vpy download_full_documents.py }
    "bm25"       { & $vpy run_all.py --stages audit qc gold matrix retrieval stats figures report --models bm25 }
    "full"       { & $vpy run_all.py --stages audit qc gold matrix retrieval stats figures report --models bm25 e5 bge_m3 hybrid }
    "stats"      { & $vpy run_all.py --stages stats figures report }
    "generation" { & $vpy run_all.py --stages qc gold matrix generation faithfulness stats figures report }
    "export"     { & $vpy run_all.py --stages export }
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run failed - copy the last 20 lines of the error. See HOW_TO_RUN_AR.md, 'Common problems'." -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "Done. Open reports\experiment_report.md and results\tables\AAU_RAG_results.xlsx" -ForegroundColor Green
