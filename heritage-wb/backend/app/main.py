from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from . import rag, schemas
from .db import get_db, init_db
from .models import CATEGORIES, Site, Trail, TrailStop


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Heritage of West Bengal API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/sites", response_model=list[schemas.SiteOut])
def list_sites(
    category: str | None = Query(None, description="mon | tem | pal | col | arc"),
    region: str | None = None,
    q: str | None = Query(None, description="text search in name, region, description"),
    year_max: int | None = Query(None, description="only sites founded up to this year"),
    db: Session = Depends(get_db),
):
    if category and category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {CATEGORIES}")
    stmt = select(Site).order_by(Site.year_founded)
    if category:
        stmt = stmt.where(Site.category == category)
    if region:
        stmt = stmt.where(Site.region.ilike(f"%{region}%"))
    if year_max is not None:
        stmt = stmt.where(Site.year_founded <= year_max)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Site.name_en.ilike(like) | Site.name_bn.ilike(like) | Site.description_en.ilike(like) | Site.region.ilike(like))
    return list(db.scalars(stmt))


@app.get("/sites/near", response_model=list[schemas.NearSite])
def sites_near(lat: float, lon: float, km: float = 50, db: Session = Depends(get_db)):
    pt = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    dist = (func.ST_DistanceSphere(Site.location, pt) / 1000).label("distance_km")
    rows = db.execute(select(Site, dist).where(dist <= km).order_by(dist)).all()
    return [schemas.NearSite(**schemas.SiteOut.model_validate(s).model_dump(), distance_km=round(d, 1)) for s, d in rows]


@app.get("/sites/{slug}", response_model=schemas.SiteDetail)
def get_site(slug: str, db: Session = Depends(get_db)):
    site = db.scalar(select(Site).where(Site.slug == slug).options(selectinload(Site.media), selectinload(Site.reports)))
    if not site:
        raise HTTPException(404, "site not found")
    return site


def _trail_out(t: Trail) -> schemas.TrailOut:
    return schemas.TrailOut(slug=t.slug, name_en=t.name_en, name_bn=t.name_bn, sites=[schemas.SiteOut.model_validate(s.site) for s in t.stops])


@app.get("/trails", response_model=list[schemas.TrailOut])
def list_trails(db: Session = Depends(get_db)):
    trails = db.scalars(select(Trail).options(selectinload(Trail.stops).selectinload(TrailStop.site)))
    return [_trail_out(t) for t in trails]


@app.post("/chat", response_model=schemas.ChatOut)
def chat(body: schemas.ChatIn, db: Session = Depends(get_db)):
    text, sources = rag.answer(db, body.question, body.lang)
    return schemas.ChatOut(answer=text, sources=sources)


# The web app. Mounted last so the API routes above take priority.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="web")
