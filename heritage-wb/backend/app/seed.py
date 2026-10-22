"""Idempotent seed: python -m app.seed"""
import json
from pathlib import Path
from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from .db import SessionLocal, init_db
from .models import Site, Trail, TrailStop

DATA = json.loads((Path(__file__).parent / "data" / "sites.json").read_text(encoding="utf-8"))


def run():
    init_db()
    with SessionLocal() as db:
        by_slug = {s.slug: s for s in db.scalars(select(Site))}
        for d in DATA["sites"]:
            lat, lon = d["lat"], d["lon"]
            site = by_slug.get(d["slug"]) or Site(slug=d["slug"])
            for k, v in d.items():
                setattr(site, k, v)
            site.location = WKTElement(f"POINT({lon} {lat})", srid=4326)
            db.add(site)
            by_slug[d["slug"]] = site
        db.flush()
        for t in DATA["trails"]:
            trail = db.scalar(select(Trail).where(Trail.slug == t["slug"])) or Trail(slug=t["slug"])
            trail.name_en, trail.name_bn = t["name_en"], t["name_bn"]
            trail.stops = [TrailStop(site_id=by_slug[s].id, position=i) for i, s in enumerate(t["stops"])]
            db.add(trail)
        db.commit()
    print(f"seeded {len(DATA['sites'])} sites, {len(DATA['trails'])} trails")


if __name__ == "__main__":
    run()
