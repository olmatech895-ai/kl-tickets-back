"""
Отчёт посещений с устройства Hikvision.
ТЗ: face-control/TZ_ATTENDANCE_FROM_DEVICE.md
Эндпоинт: GET /report/attendance-from-device и GET /api-attendance/report/attendance-from-device.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.infrastructure.hikvision.attendance_client import get_attendance_from_device

router = APIRouter(tags=["report"])


def _attendance_response(
    date_from: Optional[date],
    date_to: Optional[date],
    max_records: int,
) -> dict:
    """Всегда возвращает { records, error }; при исключении — 200 с error в теле, без 500."""
    try:
        return get_attendance_from_device(
            date_from=date_from,
            date_to=date_to,
            max_records=max_records,
        )
    except Exception as e:
        return {"records": [], "error": str(e)}


@router.get(
    "/attendance-from-device",
    response_model=dict,
    summary="Отчёт посещений с устройства Hikvision",
    description="Запрашивает у камеры/NVR Hikvision историю посещений по ISAPI AccessControl (AcsEvent). "
    "Параметры: date_from, date_to (YYYY-MM-DD), max_records. Ответ: { records: [...], error: null | string }.",
)
def attendance_from_device(
    date_from: Optional[date] = Query(None, description="Начало периода (YYYY-MM-DD), по умолчанию сегодня"),
    date_to: Optional[date] = Query(None, description="Конец периода (YYYY-MM-DD), по умолчанию = date_from"),
    max_records: int = Query(2000, ge=1, le=10000, description="Лимит записей за ответ"),
) -> dict:
    return _attendance_response(date_from, date_to, max_records)
