import os

_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "/MSSV").strip()
_PREFIX = _PREFIX if _PREFIX.startswith("/") else "/" + _PREFIX
_PREFIX = _PREFIX.rstrip("/")

def topic(*parts: str) -> str:
    clean = [p.strip("/") for p in parts if p and str(p).strip("/")]
    return "/".join([_PREFIX] + clean)