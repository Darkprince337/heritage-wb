from datetime import date
from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SiteOut(ORM):
    slug: str
    name_en: str
    name_bn: str | None
    category: str
    year_founded: int | None
    region: str | None
    description_en: str
    description_bn: str | None
    lat: float
    lon: float


class MediaOut(ORM):
    kind: str
    url: str
    caption: str | None


class ReportOut(ORM):
    noted_on: date
    status: str
    notes: str | None
    photo_url: str | None


class SiteDetail(SiteOut):
    media: list[MediaOut] = []
    reports: list[ReportOut] = []


class NearSite(SiteOut):
    distance_km: float


class TrailOut(ORM):
    slug: str
    name_en: str
    name_bn: str | None
    sites: list[SiteOut] = []


class ChatIn(BaseModel):
    question: str
    lang: str = "en"  # en | bn


class ChatOut(BaseModel):
    answer: str | None
    sources: list[str]
