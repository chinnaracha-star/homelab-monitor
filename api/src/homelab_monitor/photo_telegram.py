from datetime import UTC, datetime

from homelab_monitor.photo_folders import display_folder_name
from homelab_monitor.telegram import BANGKOK

_MONTHS = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_photo_size(size_bytes: int) -> str:
    megabytes = size_bytes / (1024 * 1024)
    return f"{megabytes:.2f} MB"


def format_photo_time(value: datetime) -> tuple[str, str]:
    stamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    local = stamp.astimezone(BANGKOK)
    date_line = f"{local.day} {_MONTHS[local.month]} {local.year}"
    time_line = local.strftime("%H:%M:%S")
    return date_line, time_line


def format_new_photo_message(
    *,
    filename: str,
    folder: str,
    size_bytes: int,
    created_at: datetime,
    source: str = "QNAP NAS",
) -> str:
    folder_name = display_folder_name(folder)
    date_line, time_line = format_photo_time(created_at)
    return "\n".join(
        (
            "━━━━━━━━━━━━━━",
            "📸 New Photo",
            "",
            "📁 Folder",
            folder_name,
            "",
            "📄 File",
            filename,
            "",
            "📏 Size",
            format_photo_size(size_bytes),
            "",
            "🕒 Time",
            date_line,
            time_line,
            "",
            "🏠 Source",
            source,
            "",
            "━━━━━━━━━━━━━━",
        )
    )
