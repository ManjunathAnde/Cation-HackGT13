"""Offline script: print the Ozempic label's Indications and Usage sentences from DailyMed.

Run from backend/:  python -m app.fetch_label
Writes no files. Copy the chosen sentence(s) into data/label.json and the label card.
"""

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
HEADERS = {"User-Agent": "cation-hackgt13"}
NS = {"v": "urn:hl7-org:v3"}
INDICATIONS_CODE = "34067-9"  # LOINC code for "Indications and Usage"

# Novo Nordisk's Ozempic injection label; excludes the oral tablet and repackager copies.
TITLE_MUST_CONTAIN = ["(SEMAGLUTIDE) INJECTION", "NOVO NORDISK"]


def get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def search_spls(drug_name):
    query = urllib.parse.urlencode({"drug_name": drug_name})
    return json.loads(get(f"{DAILYMED}/spls.json?{query}"))["data"]


def choose_spl(spls):
    matches = [spl for spl in spls if all(text in spl["title"] for text in TITLE_MUST_CONTAIN)]
    return max(matches, key=lambda spl: datetime.strptime(spl["published_date"], "%b %d, %Y"))


def local_name(element):
    return element.tag.split("}")[-1]


def text_without_captions(element):
    """Element text, skipping <caption> children (they hold list bullets)."""
    parts = [element.text or ""]
    for child in element:
        if local_name(child) != "caption":
            parts.append(text_without_captions(child))
        parts.append(child.tail or "")
    return "".join(parts)


def clean(text):
    return " ".join(text.split()).lstrip("•· ").strip()


def split_sentences(text):
    return [part for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if part]


def indications_sentences(section):
    """Paragraphs split into sentences; each list item is one sentence. Skips Highlights."""
    sentences = []
    for child in section:
        name = local_name(child)
        if name in ("excerpt", "title", "code", "id", "effectiveTime"):
            continue
        if name == "paragraph":
            sentences += split_sentences(clean(text_without_captions(child)))
        elif name == "item":
            sentences.append(clean(text_without_captions(child)))
        else:
            sentences += indications_sentences(child)
    return [sentence for sentence in sentences if sentence]


def find_indications(root):
    for section in root.iter("{urn:hl7-org:v3}section"):
        code = section.find("v:code", NS)
        if code is not None and code.get("code") == INDICATIONS_CODE:
            return section
    raise SystemExit("No Indications and Usage section found")


def main():
    spls = search_spls("ozempic")
    print(f"DailyMed results for 'ozempic': {len(spls)}")
    for spl in spls:
        print(f"  {spl['setid']}  v{spl['spl_version']}  {spl['published_date']}  {spl['title']}")

    chosen = choose_spl(spls)
    root = ET.fromstring(get(f"{DAILYMED}/spls/{chosen['setid']}.xml"))
    set_id = root.find("v:setId", NS).get("root")
    version = root.find("v:versionNumber", NS).get("value")
    effective = root.find("v:effectiveTime", NS).get("value")

    print("\nChosen label")
    print(f"  title:          {chosen['title']}")
    print(f"  set ID:         {set_id}")
    print(f"  version:        {version}")
    print(f"  effective date: {effective[:4]}-{effective[4:6]}-{effective[6:8]}")
    print(f"  link:           https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}")

    print("\nIndications and Usage sentences")
    for number, sentence in enumerate(indications_sentences(find_indications(root)), start=1):
        print(f"  {number}. {sentence}")
        print(f"     exact: {json.dumps(sentence)}")


if __name__ == "__main__":
    main()
