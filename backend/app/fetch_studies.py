"""Offline script: print proposed PubMed study cards for each approved topic.

Run from backend/:  python -m app.fetch_studies
Writes no files. Uses esearch + esummary only: titles, journals, and dates, never abstracts.
"""

import html
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "cation"
REQUEST_GAP_SECONDS = 0.4  # stays under NCBI's 3 requests/second
MAX_PER_TOPIC = 3

# blueprint §6: topic → MeSH query
TOPIC_MESH = {
    "glycemic control": '"Glycemic Control"[MeSH]',
    "cardiovascular outcomes": '"Cardiovascular Diseases"[MeSH]',
    "kidney outcomes": '("Diabetic Nephropathies"[MeSH] OR "Renal Insufficiency, Chronic"[MeSH])',
    "ozempic safety": '"Gastrointestinal Diseases"[MeSH]',
    "cardio-kidney-metabolic care": '("Cardiovascular Diseases"[MeSH] AND "Kidney Diseases"[MeSH])',
}
# blueprint §9 filters
STUDY_FILTER = (
    "(randomized controlled trial[pt] OR systematic review[pt] OR meta-analysis[pt])"
    " AND humans[MeSH]"
)


def eutils(endpoint, email, **params):
    time.sleep(REQUEST_GAP_SECONDS)
    query = urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "tool": TOOL, "email": email, **params})
    with urllib.request.urlopen(f"{EUTILS}/{endpoint}.fcgi?{query}", timeout=30) as response:
        return json.loads(response.read())


def search(topic, email):
    term = f"({TOPIC_MESH[topic]}) AND semaglutide AND {STUDY_FILTER}"
    result = eutils(
        "esearch", email, term=term, sort="pub_date", retmax=MAX_PER_TOPIC,
        datetype="pdat", reldate=730,
    )["esearchresult"]
    return term, int(result["count"]), result["idlist"]


def summaries(pmids, email):
    result = eutils("esummary", email, id=",".join(pmids))["result"]
    return [result[pmid] for pmid in pmids]


def study_card(summary, topic):
    pmid = summary["uid"]
    return {
        "id": f"pm-{pmid}",
        "title": html.unescape(summary["title"]),
        "summary": f"{summary['fulljournalname']}, {summary['pubdate']}",
        "source": "PubMed",
        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "topics": [topic],
        "claims": [],
        "kind": "study",
    }


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    email = os.getenv("NCBI_EMAIL")
    if not email:
        raise SystemExit("NCBI_EMAIL is not set in backend/.env")

    first_topic = {}  # pmid → the topic it was first found under
    for topic in TOPIC_MESH:
        term, count, pmids = search(topic, email)
        print(f"\n== {topic}  ({count} matches, showing newest {len(pmids)})")
        print(f"   query: {term}")
        for summary in summaries(pmids, email) if pmids else []:
            card = study_card(summary, topic)
            pmid = summary["uid"]
            if pmid in first_topic:
                print(f"\n   {card['id']}  duplicate — not a candidate (first under {first_topic[pmid]})")
                print(f"   title: {card['title']}")
                continue
            first_topic[pmid] = topic
            print()
            print("   " + json.dumps(card, indent=2, ensure_ascii=False).replace("\n", "\n   "))


if __name__ == "__main__":
    main()
