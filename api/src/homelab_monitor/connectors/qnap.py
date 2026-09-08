import json
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

from homelab_monitor.connectors.base import BaseConnector, ConnectorSnapshot, utc_now
from homelab_monitor.connectors.http import as_float, as_int, as_str, get_json, http_get

STORAGE_WARNING_PERCENT = 80.0
STORAGE_CRITICAL_PERCENT = 90.0


def storage_health(percent: float) -> str:
    if percent >= STORAGE_CRITICAL_PERCENT:
        return "critical"
    if percent >= STORAGE_WARNING_PERCENT:
        return "warning"
    return "healthy"


class QnapConnector(BaseConnector):
    service = "qnap"

    def collect(self) -> ConnectorSnapshot:
        if self.mock:
            return self._snapshot(self._mock_summary(), version="5.2.1")
        if not self.base_url:
            return self._unconfigured()
        return self._live()

    def _unconfigured(self) -> ConnectorSnapshot:
        return ConnectorSnapshot(
            service=self.service,
            status="unknown",
            version="",
            updated_at=utc_now(),
            summary={},
        )

    def _mock_summary(self) -> dict:
        capacity = 12_000_000_000_000
        used = 4_980_000_000_000
        free = capacity - used
        percent = round(used / capacity * 100, 1)
        return {
            "hostname": "qnap-lab-01",
            "model": "TS-453Be",
            "firmware": "5.2.1",
            "firmware_version": "5.2.1",
            "uptime_seconds": 864000,
            "online": True,
            "storage_used_percent": percent,
            "storage_percent": percent,
            "capacity_bytes": capacity,
            "used_bytes": used,
            "free_bytes": free,
            "shared_folders": 4,
            "temperature_celsius": 42,
            "storage_health": storage_health(percent),
        }

    def _live(self) -> ConnectorSnapshot:
        sid = self.api_key
        if self.username and self.password and not sid:
            query = urlencode({"user": self.username, "pwd": self.password})
            login = http_get(
                f"{self.base_url}/cgi-bin/authLogin.cgi?{query}",
                timeout=self.timeout,
                client=self._client,
            )
            sid = _extract_sid(login.text)
        sysinfo = get_json(
            f"{self.base_url}/cgi-bin/management/manaRequest.cgi?subfunc=sysinfo&sid={sid}",
            timeout=self.timeout,
            client=self._client,
        )
        payload = sysinfo if isinstance(sysinfo, dict) else {}
        if "raw" in payload:
            payload = _parse_qnap_xml(str(payload["raw"]))
        share_count = as_int(payload.get("shared_folders"))
        try:
            shares = get_json(
                f"{self.base_url}/cgi-bin/filemanager/utilRequest.cgi?func=get_share_list&sid={sid}",
                timeout=self.timeout,
                client=self._client,
            )
            share_count = _share_count(shares) or share_count
        except httpx.HTTPError:
            pass
        capacity = as_int(payload.get("capacity_bytes") or payload.get("volume_size"))
        used = as_int(payload.get("used_bytes") or payload.get("volume_used"))
        free = as_int(payload.get("free_bytes") or payload.get("volume_free") or (capacity - used))
        percent = as_float(payload.get("storage_percent"))
        if percent == 0 and capacity:
            percent = round(used / capacity * 100, 1)
        firmware = as_str(payload.get("firmware") or payload.get("version"))
        online = payload.get("online", True)
        summary = {
            "hostname": as_str(payload.get("hostname") or payload.get("host"), "qnap"),
            "model": as_str(payload.get("model"), "TS-453Be"),
            "firmware": firmware,
            "firmware_version": firmware,
            "uptime_seconds": as_int(payload.get("uptime_seconds") or payload.get("uptime")),
            "online": bool(online),
            "storage_used_percent": percent,
            "storage_percent": percent,
            "capacity_bytes": capacity,
            "used_bytes": used,
            "free_bytes": free,
            "shared_folders": share_count,
            "temperature_celsius": as_int(
                payload.get("temperature_celsius") or payload.get("cpu_temp")
            ),
            "storage_health": storage_health(percent),
        }
        return self._snapshot(summary, version=firmware or "unknown")

    def _snapshot(self, summary: dict, *, version: str) -> ConnectorSnapshot:
        status = "healthy"
        if not summary.get("online") or summary.get("storage_health") == "critical":
            status = "unhealthy"
        elif summary.get("storage_health") == "warning":
            status = "degraded"
        return ConnectorSnapshot(
            service=self.service,
            status=status,
            version=version,
            updated_at=utc_now(),
            summary=summary,
        )


def _extract_sid(text: str) -> str:
    marker = "<authSid>"
    if marker in text:
        return text.split(marker, 1)[1].split("<", 1)[0].strip()
    if '"sid"' in text or '"authSid"' in text:
        try:
            body = json.loads(text)
            return str(body.get("sid") or body.get("authSid") or "")
        except json.JSONDecodeError:
            return ""
    return ""


def _parse_qnap_xml(text: str) -> dict:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return {}
    values = {child.tag: (child.text or "") for child in root.iter() if child is not root}
    return values


def _share_count(payload: object) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        datas = payload.get("datas") or payload.get("shares") or payload.get("items")
        if isinstance(datas, list):
            return len(datas)
        if "raw" in payload:
            return 0
        return as_int(payload.get("count") or payload.get("shared_folders"))
    return 0
