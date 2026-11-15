#!/usr/bin/env python
"""Download candidate UAE university handbooks for the multi-university dataset.

    python download_university_sources.py

Saves PDFs to data/original/universities/<university_id>/ and writes
data/original/universities/SOURCES.csv (URL, language, edition, status).
Every source is a public document. If a download fails, open the URL in a browser
and save the file under the listed name. Links were found on 2026-11-09 and may change.
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "original" / "universities"

# university_id, university, language, edition, file_name, url, role
SOURCES = [
    ("AAU", "Al Ain University", "ar", "2025-2026", "aau_student_handbook_2025_2026_ar.pdf",
     "https://aau.ac.ae/publications/handbooks/al_ain_university_student_handbook__2025_2026_ar.pdf", "bilingual pair"),
    ("AAU", "Al Ain University", "en", "2025-2026", "aau_student_handbook_2025_2026_en.pdf",
     "https://aau.ac.ae/publications/handbooks/al_ain_university_student_handbook__2025_2026_en.pdf", "bilingual pair"),
    ("JU", "Jumeira University (Dubai)", "ar", "2024-2025", "ju_ug_student_handbook_2024_2025_ar.pdf",
     "https://ju.ac.ae/wp-content/uploads/2024/10/Undergraduate-Student-Handbook-2024-25-Arabic.pdf", "bilingual pair"),
    ("JU", "Jumeira University (Dubai)", "en", "2024-2025", "ju_ug_student_handbook_2024_2025_en.pdf",
     "https://ju.ac.ae/wp-content/uploads/2024/10/Undergraduate-Student-Handbook-2024-2025-English.pdf", "bilingual pair"),
    ("CUA", "City University Ajman", "ar", "Sep 2024", "cua_ug_student_handbook_sep2024_ar.pdf",
     "https://cu.ac.ae/wp-content/uploads/2024/12/UG-Student-Handbook-Arabic_Sep-24.docx.pdf", "bilingual pair"),
    ("CUA", "City University Ajman", "en", "Sep 2024", "cua_ug_student_handbook_sep2024_en.pdf",
     "https://cu.ac.ae/public-resources/UG-Student-Handbook_English-Sep-24.pdf", "bilingual pair"),
    ("UAEU", "United Arab Emirates University", "ar", "2023-2024", "uaeu_ug_student_handbook_2023_ar.pdf",
     "https://www.uaeu.ac.ae/ar/experience/uaeu-undergraduate-student-handbook-2023-ar.pdf", "bilingual pair (short guide)"),
    ("UAEU", "United Arab Emirates University", "en", "2023-2024", "uaeu_ug_student_handbook_2023_en.pdf",
     "https://www.uaeu.ac.ae/en/docs/uaeu-undergraduate-student-handbook2023-english.pdf", "bilingual pair (short guide)"),
    ("AQU", "Al Qasimia University", "ar", "2024-2025", "aqu_student_guide_2024_2025_ar.pdf",
     "https://www.alqasimia.ac.ae/ar/MediaCenter/Publications/Documents/UniversityGuides/Student-Guide.pdf", "Arabic only"),
    ("AJU", "Ajman University", "en", "2026-2027", "aju_student_handbook_2026_2027_en.pdf",
     "https://www.ajman.ac.ae/upload/docs/Student_Handbook_2026-2027.pdf", "English only"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, failed = [], []
    for uid, uni, lang, ed, fname, url, role in SOURCES:
        d = OUT / uid
        d.mkdir(exist_ok=True)
        f = d / fname
        status = "present"
        if not (f.exists() and f.stat().st_size > 10_000):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research download)"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                if not data.startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                f.write_bytes(data)
                status = "downloaded"
            except Exception as e:
                status = f"FAILED: {type(e).__name__}"
                failed.append((uid, fname, url))
        print(f"[{status:>10}] {uid:5} {lang}  {fname}")
        rows.append({"university_id": uid, "university": uni, "language": lang, "edition": ed,
                     "file_name": f"{uid}/{fname}", "source_url": url, "role": role, "status": status})
    with open(OUT / "SOURCES.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows) - len(failed)}/{len(rows)} files present in {OUT}")
    if failed:
        print("Download these manually and save them with exactly these names:")
        for uid, fname, url in failed:
            print(f"  {OUT / uid / fname}\n      {url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
