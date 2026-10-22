from datetime import date
from geoalchemy2 import Geometry
from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, Float, func, literal_column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

CATEGORIES = ("mon", "tem", "pal", "col", "arc", "nat", "cul")  # monastery, temple, palace/mosque, colonial, ancient, nature, culture


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_bn: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(3), index=True)
    year_founded: Mapped[int | None] = mapped_column(Integer, index=True)  # negative = BCE
    region: Mapped[str | None] = mapped_column(String(80), index=True)
    description_en: Mapped[str] = mapped_column(Text)
    description_bn: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=True))

    media: Mapped[list["Media"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    reports: Mapped[list["ConditionReport"]] = relationship(
        back_populates="site", cascade="all, delete-orphan", order_by="ConditionReport.noted_on.desc()"
    )



def fts_doc():
    """Full-text document for a site. Shared by the GIN index and rag.retrieve so the index is used."""
    t = Site.__table__
    return func.to_tsvector(
        literal_column("'english'"),
        func.coalesce(t.c.name_en, literal_column("''", String))
        + literal_column("' '", String)
        + func.coalesce(t.c.region, literal_column("''", String))
        + literal_column("' '", String)
        + t.c.description_en,
    )


Index("ix_sites_fts", fts_doc(), postgresql_using="gin", _table=Site.__table__)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(12))  # photo | panorama | model3d | audio
    url: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(200))
    site: Mapped[Site] = relationship(back_populates="media")


class ConditionReport(Base):
    __tablename__ = "condition_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    noted_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))  # good | fair | poor | critical
    notes: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    site: Mapped[Site] = relationship(back_populates="reports")


class Trail(Base):
    __tablename__ = "trails"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_bn: Mapped[str | None] = mapped_column(String(120))
    stops: Mapped[list["TrailStop"]] = relationship(
        back_populates="trail", cascade="all, delete-orphan", order_by="TrailStop.position"
    )


class TrailStop(Base):
    __tablename__ = "trail_stops"
    trail_id: Mapped[int] = mapped_column(ForeignKey("trails.id", ondelete="CASCADE"), primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    trail: Mapped[Trail] = relationship(back_populates="stops")
    site: Mapped[Site] = relationship()
