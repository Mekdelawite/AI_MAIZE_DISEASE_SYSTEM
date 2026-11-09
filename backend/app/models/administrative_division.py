from __future__ import annotations

from backend.app.extensions import db


class GeographyRegion(db.Model):
    __tablename__ = "geography_regions"

    id = db.Column(db.String(32), primary_key=True)
    name_en = db.Column(db.String(120), nullable=False, unique=True)
    name_local = db.Column(db.String(120), nullable=True)

    zones = db.relationship("GeographyZone", back_populates="region")


class GeographyZone(db.Model):
    __tablename__ = "geography_zones"
    __table_args__ = (
        db.UniqueConstraint("region_id", "name_en", name="uq_geography_zone_region_name"),
        db.UniqueConstraint("id", "region_id", name="uq_geography_zone_id_region"),
    )

    id = db.Column(db.String(32), primary_key=True)
    region_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_regions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name_en = db.Column(db.String(120), nullable=False)
    name_local = db.Column(db.String(120), nullable=True)

    region = db.relationship("GeographyRegion", back_populates="zones")
    woredas = db.relationship("GeographyWoreda", back_populates="zone")


class GeographyWoreda(db.Model):
    __tablename__ = "geography_woredas"
    __table_args__ = (
        db.UniqueConstraint("zone_id", "name_en", name="uq_geography_woreda_zone_name"),
        db.UniqueConstraint("id", "zone_id", name="uq_geography_woreda_id_zone"),
    )

    id = db.Column(db.String(32), primary_key=True)
    zone_id = db.Column(
        db.String(32),
        db.ForeignKey("geography_zones.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name_en = db.Column(db.String(120), nullable=False)
    name_local = db.Column(db.String(120), nullable=True)

    zone = db.relationship("GeographyZone", back_populates="woredas")
