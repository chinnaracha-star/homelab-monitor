const FOLDER_LABELS: Record<string, string> = {
  '/mnt/picture-all': 'Pictures-All',
  '/mnt/pictures-ss22': 'Pictures-SS22',
  '/mnt/pictures-ae': 'Pictures-ae',
  '/mnt/picture-mae': 'Pictures-แม่',
  '/mnt/picture-por': 'Pictures-พ่อ',
  '/mnt/pictures-solarboy': 'Pictures-SolarBoy',
}

const BASENAME_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(FOLDER_LABELS).map(([path, label]) => [path.split('/').pop()?.toLowerCase() ?? '', label]),
)

export function displayFolderName(path: string): string {
  const normalized = path.replace(/\/+$/, '') || path
  if (FOLDER_LABELS[normalized]) {
    return FOLDER_LABELS[normalized]
  }
  const base = normalized.split('/').filter(Boolean).pop() ?? normalized
  return BASENAME_LABELS[base.toLowerCase()] ?? base
}

export function watchFolderList(stats: {
  watch_folders?: string[]
  watch_folder?: string
}): string[] {
  if (stats.watch_folders?.length) {
    return stats.watch_folders
  }
  return stats.watch_folder ? [stats.watch_folder] : []
}
