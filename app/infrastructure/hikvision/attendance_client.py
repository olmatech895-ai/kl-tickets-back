"""
Клиент Hikvision ISAPI AccessControl AcsEvent для отчёта посещений.
ТЗ: face-control/TZ_ATTENDANCE_FROM_DEVICE.md
"""
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, Optional

import httpx

from app.infrastructure.config.settings import settings


def _norm(s: Any, default: str = "-") -> str:
    if s is None or (isinstance(s, str) and not s.strip()):
        return default
    return str(s).strip()


def _norm_int(n: Any):
    if n is None:
        return None
    try:
        return int(n)
    except (TypeError, ValueError):
        return None


def _parse_record_from_info(info: dict) -> dict:
    """Маппинг одной записи из InfoList (JSON) в контракт API."""
    person_id = _norm(info.get("employeeNoString") or info.get("employeeNo") or info.get("cardNo"), "-")
    name = _norm(info.get("name"))
    department = _norm(info.get("department"))
    time_val = _norm(info.get("time") or info.get("dateTime"), "")
    door_no = _norm_int(info.get("doorNo"))
    door_name = _norm(info.get("doorName"))
    checkpoint = door_name if door_name != "-" else (f"Door{door_no}" if door_no is not None else "Door")
    attendance_status = _norm(info.get("attendanceStatus"))
    label = _norm(info.get("label"), "")
    return {
        "person_id": person_id,
        "name": name,
        "department": department,
        "time": time_val or None,
        "checkpoint": checkpoint,
        "attendance_status": attendance_status,
        "door_no": door_no,
        "label": label,
    }


def _parse_json_response(body: dict) -> tuple[list[dict], int, int, str]:
    """Парсит JSON-ответ AcsEvent. Возвращает (records, totalMatches, numOfMatches, responseStatusStrg)."""
    acs = body.get("AcsEvent") or {}
    total = int(acs.get("totalMatches", 0) or 0)
    num = int(acs.get("numOfMatches", 0) or 0)
    status_str = _norm(acs.get("responseStatusStrg", ""), "")
    info_list = acs.get("InfoList") or []
    if isinstance(info_list, dict):
        info_list = info_list.get("InfoListItem") or info_list.get("info") or []
        if not isinstance(info_list, list):
            info_list = [info_list] if info_list else []
    records = []
    for item in info_list:
        if isinstance(item, dict):
            records.append(_parse_record_from_info(item))
    return records, total, num, status_str


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_by_local_name(parent: ET.Element, name: str):
    for el in parent.iter():
        if _local_name(el.tag) == name:
            return el
    return None


def _parse_xml_response(text: str) -> tuple[list[dict], int, int, str]:
    """Парсит XML-ответ AcsEvent. Возвращает (records, totalMatches, numOfMatches, responseStatusStrg)."""
    root = ET.fromstring(text)
    acs = root if _local_name(root.tag) == "AcsEvent" else _find_by_local_name(root, "AcsEvent") or root
    total_el = _find_by_local_name(acs, "totalMatches")
    num_el = _find_by_local_name(acs, "numOfMatches")
    status_el = _find_by_local_name(acs, "responseStatusStrg")
    total = int(total_el.text or 0) if total_el is not None else 0
    num = int(num_el.text or 0) if num_el is not None else 0
    status_str = (status_el.text or "").strip() if status_el is not None else ""
    info_list_el = _find_by_local_name(acs, "InfoList")
    records = []
    if info_list_el is not None:
        for item in info_list_el:
            ln = _local_name(item.tag)
            if ln in ("InfoListItem", "info"):
                info = {}
                for child in item:
                    info[_local_name(child.tag)] = child.text
                records.append(_parse_record_from_info(info))
    return records, total, num, status_str


def get_attendance_from_device(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    max_records: int = 2000,
) -> dict:
    """
    Запрашивает у устройства Hikvision историю посещений (AcsEvent).
    Возвращает { "records": [...], "error": None | "строка" }.
    """
    if not settings.HIKVISION_DEVICE_IP or not settings.HIKVISION_DEVICE_USER:
        return {"records": [], "error": "Устройство не настроено (HIKVISION_DEVICE_IP, HIKVISION_DEVICE_USER)"}

    today = date.today()
    date_from = date_from or today
    date_to = date_to or date_from
    max_records = max(1, min(10000, max_records))

    start_time = f"{date_from.isoformat()}T00:00:00+00:00"
    end_time = f"{date_to.isoformat()}T23:59:59+00:00"

    base_url = f"http://{settings.HIKVISION_DEVICE_IP}:{settings.HIKVISION_DEVICE_PORT}"
    path = "/ISAPI/AccessControl/AcsEvent"
    auth = httpx.DigestAuth(
        settings.HIKVISION_DEVICE_USER,
        settings.HIKVISION_DEVICE_PASSWORD or "",
    )
    all_records: list[dict] = []
    use_json = True
    position = 0
    timeout = settings.HIKVISION_REQUEST_TIMEOUT

    with httpx.Client(timeout=timeout, auth=auth) as client:
        while len(all_records) < max_records:
            page_size = min(10, max_records - len(all_records))
            body_json = {
                "AcsEventCond": {
                    "searchID": "1",
                    "searchResultPosition": position,
                    "maxResults": page_size,
                    "major": 5,
                    "minor": 0,
                    "startTime": start_time,
                    "endTime": end_time,
                }
            }
            body_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<AcsEventCond version="1.0" xmlns="http://www.hikvision.com/ver10/XMLSchema">
  <searchID>1</searchID>
  <searchResultPosition>{position}</searchResultPosition>
  <maxResults>{page_size}</maxResults>
  <major>5</major>
  <minor>0</minor>
  <startTime>{start_time}</startTime>
  <endTime>{end_time}</endTime>
</AcsEventCond>"""

            try:
                if use_json:
                    url = f"{base_url}{path}?format=json"
                    resp = client.post(
                        url,
                        json=body_json,
                        headers={"Accept": "application/json"},
                    )
                else:
                    url = f"{base_url}{path}?format=xml"
                    resp = client.post(
                        url,
                        content=body_xml,
                        headers={"Content-Type": "application/xml; charset=utf-8", "Accept": "application/xml"},
                    )
            except Exception as e:
                err_msg = str(e).strip().lower()
                if "timed out" in err_msg or "timeout" in err_msg:
                    return {
                        "records": all_records,
                        "error": "Таймаут подключения к устройству. Проверьте: устройство доступно с сервера (сеть/VPN), HIKVISION_DEVICE_IP в .env, при необходимости увеличьте HIKVISION_REQUEST_TIMEOUT.",
                    }
                return {"records": all_records, "error": f"Ошибка подключения: {e}"}

            if resp.status_code != 200:
                if use_json and resp.status_code == 400 and "badJsonFormat" in (resp.text or ""):
                    use_json = False
                    continue
                return {
                    "records": all_records,
                    "error": f"HTTP {resp.status_code}: {(resp.text or '')[:200]}",
                }

            try:
                if use_json:
                    data = resp.json()
                    records, total, num, status_str = _parse_json_response(data)
                else:
                    records, total, num, status_str = _parse_xml_response(resp.text)
            except Exception as e:
                return {"records": all_records, "error": f"Ошибка разбора ответа: {e}"}

            all_records.extend(records)
            if status_str != "MORE" or num == 0:
                break
            position += num
            if position >= total:
                break

    return {"records": all_records, "error": None}
