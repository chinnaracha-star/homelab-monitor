from pathlib import Path

DEFAULT_WATCH_FOLDERS = [
    "/mnt/picture-all",
    "/mnt/pictures-ss22",
    "/mnt/pictures-ae",
    "/mnt/picture-mae",
    "/mnt/picture-por",
    "/mnt/pictures-solarboy",
]

FOLDER_LABELS = {
    "/mnt/picture-all": "Pictures-All",
    "/mnt/pictures-ss22": "Pictures-SS22",
    "/mnt/pictures-ae": "Pictures-ae",
    "/mnt/picture-mae": "Pictures-แม่",
    "/mnt/picture-por": "Pictures-พ่อ",
    "/mnt/pictures-solarboy": "Pictures-SolarBoy",
}

_BASENAME_LABELS = {Path(path).name.lower(): label for path, label in FOLDER_LABELS.items()}


def display_folder_name(path: str) -> str:
    normalized = path.rstrip("/") or path
    if normalized in FOLDER_LABELS:
        return FOLDER_LABELS[normalized]
    base = Path(normalized).name
    if not base:
        return normalized
    return _BASENAME_LABELS.get(base.lower(), base)


def display_folder_names(paths: list[str]) -> list[str]:
    return [display_folder_name(path) for path in paths]


def matching_watch_root(folder: str, watch_roots: list[str]) -> str:
    normalized = folder.rstrip("/")
    for root in sorted(watch_roots, key=len, reverse=True):
        prefix = root.rstrip("/")
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return root
    return folder


def inspect_watch_folder(path: str) -> str | None:
    root = Path(path)
    try:
        if not root.exists():
            return "Not found"
        if not root.is_dir():
            return "Not a directory"
        next(root.iterdir(), None)
    except PermissionError:
        return "Permission denied"
    except OSError as exc:
        return exc.strerror or str(exc)
    return None
