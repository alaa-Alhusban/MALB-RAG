#!/usr/bin/env python
"""Rebuild data/multi_university/pages.csv from the handbook PDFs.

    python download_university_sources.py     # saves the PDFs under data/original/universities/
    python extract_handbooks.py               # writes data/multi_university/pages.csv

The handbook text is not redistributed in this repository (copyright of the universities).
Check each PDF against the SHA-256 in data/multi_university/SOURCES.csv: universities update
their handbooks, and a different edition gives different pages and passages.
"""
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.full_extraction import extract_page_texts          # noqa: E402
from src.pdf_extraction import suspicious_tokens           # noqa: E402
from src.preprocessing import AR_TOKEN_RE                  # noqa: E402

PDF_DIR = ROOT / "data" / "original" / "universities"
OUT = ROOT / "data" / "multi_university" / "pages.csv"
LAT = re.compile(r"[A-Za-z]")
# per-file settings decided from the extraction audit (see the paper, Section IV-A)
METHOD = {("JU", "ar"): dict(method="ocr_hybrid"), ("CUA", "ar"): dict(x_tolerance=1.5), ("CUA", "en"): dict(x_tolerance=1.5)}

src = pd.read_csv(ROOT / "data" / "multi_university" / "SOURCES.csv", encoding="utf-8-sig")
rows = []
for _, s in src.iterrows():
    pdf = PDF_DIR / s.file_name
    if not pdf.exists():
        sys.exit(f"Missing {pdf}. Run download_university_sources.py or save the file from {s.source_url}")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if "sha256" in s and isinstance(s.sha256, str) and digest != s.sha256:
        print(f"WARNING: {s.file_name} differs from the edition used in the paper (sha256 mismatch)")
    kw = METHOD.get((s.university_id, s.language), {})
    for pg in extract_page_texts(pdf, **kw):
        t = pg["text"]
        ar = sum(len(x) for x in AR_TOKEN_RE.findall(t)); la = len(LAT.findall(t))
        rows.append(dict(university_id=s.university_id, doc_lang=s.language, file=s.file_name, page=pg["page"],
                         method=kw.get("method", "glyph") + (f"_xtol{kw['x_tolerance']}" if "x_tolerance" in kw else ""),
                         n_words=pg["n_words"], ar_share=round(ar / (ar + la), 3) if ar + la else 0,
                         long_tokens=sum(1 for w in t.split() if len(w) > 25), suspicious=len(suspicious_tokens(t)), text=t))
d = pd.DataFrame(rows)
d.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"Wrote {OUT} ({len(d)} pages)")
print(d.groupby(["university_id", "doc_lang"]).page.count().to_string())
