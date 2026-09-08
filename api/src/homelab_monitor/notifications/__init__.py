CHANNELS = ("telegram", "discord", "slack", "email")
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.05
SETTINGS_ROW_ID = 1
SECRET_UNCHANGED = None


def channel_payload(payload: dict, channel: str) -> dict:
    raw = payload.get(channel)
    return raw if isinstance(raw, dict) else {}
