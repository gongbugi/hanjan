from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from hanjan.grind.analyze import GrindAnalysis
from hanjan.grind.calibration import Calibration, Point, build_calibration
from hanjan.models import GrindMeasurement


def calibration_for(session: Session, grinder_id: int) -> Calibration:
    rows = session.execute(
        select(GrindMeasurement.clicks, GrindMeasurement.d50_mm).where(GrindMeasurement.grinder_id == grinder_id)
    ).all()
    return build_calibration([Point(clicks, d50) for clicks, d50 in rows])


def save_measurement(
    session: Session, analysis: GrindAnalysis, *, grinder_id: int, clicks: int, brew_id: int | None
) -> GrindMeasurement:
    m = GrindMeasurement(
        brew_id=brew_id,
        grinder_id=grinder_id,
        clicks=clicks,
        mm_per_px=analysis.mm_per_px,
        particle_count=analysis.particle_count,
        d10_mm=analysis.d10_mm,
        d50_mm=analysis.d50_mm,
        d90_mm=analysis.d90_mm,
        count_d50_mm=analysis.count_d50_mm,
        min_detectable_mm=analysis.min_detectable_mm,
        clump_suspects=analysis.clump_suspects,
        histogram=[asdict(b) for b in analysis.histogram],
        warnings=list(analysis.warnings),
    )
    session.add(m)
    session.flush()
    return m
