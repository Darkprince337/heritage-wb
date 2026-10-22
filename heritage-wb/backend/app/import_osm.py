"""Import tourist spots from OpenStreetMap via the Overpass API.

    docker compose exec api python -m app.import_osm --dry-run
    docker compose exec api python -m app.import_osm --limit 300

Data (c) OpenStreetMap contributors, licensed under the ODbL. Already-known sites are skipped.
"""
import argparse
import json
import re
import urllib.parse
import urllib.request
from collections import Counter

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from .db import SessionLocal, init_db
from .models import Site

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = """[out:json][timeout:120];
area["ISO3166-2"="IN-WB"]->.a;
(
  nwr["tourism"~"^(attraction|viewpoint|museum|zoo|theme_park)$"]["name"](area.a);
  nwr["historic"~"^(monument|memorial|ruins|castle|fort|archaeological_site|palace)$"]["name"](area.a);
  nwr["amenity"="place_of_worship"]["name"]["wikidata"](area.a);
);
out center tags;"""


def category(tags: dict) -> str:
    if tags.get("amenity") == "place_of_worship":
        return "mon" if tags.get("religion") == "buddhist" else "tem"
    h, t = tags.get("historic"), tags.get("tourism")
    if h in ("castle", "fort", "palace"):
        return "pal"
    if h in ("ruins", "archaeological_site"):
        return "arc"
    if t in ("zoo", "viewpoint"):
        return "nat"
    return "cul"


def parse(elements: list[dict]) -> list[dict]:
    out = []
    for el in elements:
        tags = el.get("tags", {})
        pt = el if "lat" in el else el.get("center")
        if not pt:
            continue
        name = tags.get("name:en") or tags.get("name", "")
        if not name or not name.isascii():
            continue
        bn = tags.get("name:bn") or next((tags[k] for k in ("name",) if k in tags and not tags[k].isascii()), None)
        year = re.search(r"\b(\d{4})\b", tags.get("start_date", ""))
        kind = (tags.get("tourism") or tags.get("historic") or tags.get("religion", "") + " place of worship").replace("_", " ")
        out.append({
            "slug": f"osm-{el['type'][0]}{el['id']}",
            "name_en": name[:120], "name_bn": bn[:120] if bn else None,
            "category": category(tags), "year_founded": int(year.group(1)) if year else None,
            "region": (tags.get("addr:district") or tags.get("addr:city") or "")[:80] or None,
            "description_en": tags.get("description:en") or tags.get("description") or f"{kind.capitalize()}. Listed on OpenStreetMap.",
            "lat": pt["lat"], "lon": pt["lon"],
        })
    return out


def fetch() -> list[dict]:
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": QUERY}).encode(), headers={"User-Agent": "heritage-wb/0.1"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["elements"]


def run(limit: int | None, dry: bool):
    init_db()
    rows = parse(fetch())
    with SessionLocal() as db:
        known = [(s.name_en.lower(), s.lat, s.lon, s.slug) for s in db.scalars(select(Site))]
        added = Counter()
        for r in rows:
            if limit is not None and sum(added.values()) >= limit:
                break
            if any(r["slug"] == k[3] or r["name_en"].lower() == k[0] or (abs(r["lat"] - k[1]) < 0.002 and abs(r["lon"] - k[2]) < 0.002) for k in known):
                continue
            known.append((r["name_en"].lower(), r["lat"], r["lon"], r["slug"]))
            added[r["category"]] += 1
            if not dry:
                db.add(Site(**r, location=WKTElement(f"POINT({r['lon']} {r['lat']})", srid=4326)))
        if not dry:
            db.commit()
    print(("would add " if dry else "added "), dict(added), "of", len(rows), "found")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    run(a.limit, a.dry_run)
