"""Offline script: print candidate PubMed studies for two doctor profiles, for a human to pick.

Dr. Patel (endocrinology): per approved topic, a brand lane (topic MeSH AND semaglutide) and a
clinical lane (topic MeSH AND type 2 diabetes, NOT semaglutide; none for ozempic safety).
Dr. Evan (dermatology): clinical lane only, no drug term.
Every search: RCT / systematic review / meta-analysis, humans, no date limit, sorted by relevance.

Run from backend/:  python -m app.fetch_studies
Writes no files. Uses esearch + esummary only: titles, journals, and dates, never abstracts.
"""

import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "cation"
REQUEST_GAP_SECONDS = 0.4  # stays under NCBI's 3 requests/second
MAX_PER_SEARCH = 8
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "cache.json"

# blueprint §6: Dr. Patel's topic → MeSH query
PATEL_MESH = {
    "glycemic control": '"Glycemic Control"[MeSH]',
    "cardiovascular outcomes": '"Cardiovascular Diseases"[MeSH]',
    "kidney outcomes": '("Diabetic Nephropathies"[MeSH] OR "Renal Insufficiency, Chronic"[MeSH])',
    "ozempic safety": '"Gastrointestinal Diseases"[MeSH]',
    "cardio-kidney-metabolic care": '("Cardiovascular Diseases"[MeSH] AND "Kidney Diseases"[MeSH])',
}
BRAND_ONLY = {"ozempic safety"}
# Dr. Evan's topic → MeSH query
EVAN_MESH = {
    "psoriasis": '"Psoriasis"[MeSH]',
    "atopic dermatitis": '"Dermatitis, Atopic"[MeSH]',
    "hidradenitis suppurativa": '"Hidradenitis Suppurativa"[MeSH]',
    "psoriatic arthritis": '"Arthritis, Psoriatic"[MeSH]',
}
STUDY_FILTER = (
    "(randomized controlled trial[pt] OR systematic review[pt] OR meta-analysis[pt])"
    " AND humans[MeSH]"
)
STUDY_TYPES = ("Randomized Controlled Trial", "Systematic Review", "Meta-Analysis")


def searches():
    """(doctor, topic, lane, term) in run order. NOT comes last: PubMed reads operators left to right."""
    for topic, mesh in PATEL_MESH.items():
        yield "Dr. Patel", topic, "brand", f"({mesh}) AND semaglutide AND ({STUDY_FILTER})"
        if topic not in BRAND_ONLY:
            yield ("Dr. Patel", topic, "clinical",
                   f'({mesh}) AND "Diabetes Mellitus, Type 2"[MeSH] AND ({STUDY_FILTER}) NOT semaglutide')
    for topic, mesh in EVAN_MESH.items():
        yield "Dr. Evan", topic, "clinical", f"{mesh} AND ({STUDY_FILTER})"


def eutils(endpoint, email, **params):
    time.sleep(REQUEST_GAP_SECONDS)
    query = urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "tool": TOOL, "email": email, **params})
    with urllib.request.urlopen(f"{EUTILS}/{endpoint}.fcgi?{query}", timeout=30) as response:
        return json.loads(response.read())


def search(term, email):
    result = eutils("esearch", email, term=term, sort="relevance", retmax=MAX_PER_SEARCH)["esearchresult"]
    return int(result["count"]), result["idlist"]


def summaries(pmids, email):
    result = eutils("esummary", email, id=",".join(pmids))["result"]
    return [result[pmid] for pmid in pmids]


def candidate(summary):
    types = [t for t in STUDY_TYPES if t in summary.get("pubtype", [])]
    return {
        "pmid": summary["uid"],
        "year": summary.get("sortpubdate", "")[:4] or summary.get("pubdate", "")[:4],
        "title": html.unescape(summary["title"]),
        "journal": summary["fulljournalname"],
        "types": ", ".join(types) or "(other)",
    }


def cached_pmids():
    cards = json.loads(CACHE_FILE.read_text(encoding="utf-8"))["cards"]
    return {card["id"][3:] for card in cards if card["id"].startswith("pm-")}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    email = os.getenv("NCBI_EMAIL")
    if not email:
        raise SystemExit("NCBI_EMAIL is not set in backend/.env")

    in_cache = cached_pmids()
    first_seen = {}  # pmid → "doctor / topic / lane" where it first appeared
    counts = []
    doctor_shown = None
    for doctor, topic, lane, term in searches():
        if doctor != doctor_shown:
            print(f"\n################ {doctor} ################")
            doctor_shown = doctor
        where = f"{doctor} / {topic} / {lane}"
        count, pmids = search(term, email)
        print(f"\n== {doctor} → {topic} → {lane}  ({count} matches, top {len(pmids)} by relevance)")
        print(f"   query: {term}")
        if not pmids:
            print("   no results")
        fresh = 0
        for summary in summaries(pmids, email) if pmids else []:
            c = candidate(summary)
            line = f"{c['pmid']} · {c['year']} · {c['title']} · {c['journal']} · {c['types']}"
            if c["pmid"] in in_cache:
                print(f"   -  {line}\n      already in cache.json — skipped")
            elif c["pmid"] in first_seen:
                print(f"   -  {line}\n      duplicate — not a candidate (first under {first_seen[c['pmid']]})")
            else:
                first_seen[c["pmid"]] = where
                fresh += 1
                print(f"   {fresh}. {line}")
        counts.append((where, fresh))

    print("\n== Candidates per search")
    for where, fresh in counts:
        print(f"   {fresh}  {where}")
    print(f"   total: {sum(fresh for _, fresh in counts)}")


if __name__ == "__main__":
    main()
