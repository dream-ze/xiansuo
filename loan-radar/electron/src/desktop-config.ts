import * as path from 'path';

export const DEFAULT_APP_PORT = 8001;
export const DEFAULT_MEDIA_CRAWLER_PORT = 8080;
export const DEFAULT_POSTGRES_PORT = 55432;

export function buildDatabaseUrl(pgPort: number): string {
  return `postgresql+psycopg2://loan_radar:loan_radar_password@127.0.0.1:${pgPort}/loan_radar`;
}

export function buildPythonImportPath(paths: string[]): string {
  return [...new Set(paths.filter(Boolean))].join(path.delimiter);
}

export function getEmbeddedPlaywrightNodeDir(pythonDir: string): string {
  return path.join(pythonDir, 'Lib', 'site-packages', 'playwright', 'driver');
}

export function prependPathEntries(currentPath: string | undefined, entries: string[]): string {
  const seen = new Set<string>();
  const nextEntries = [...entries, ...(currentPath || '').split(path.delimiter)]
    .filter(Boolean)
    .filter((entry) => {
      const key = process.platform === 'win32' ? entry.toLowerCase() : entry;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  return nextEntries.join(path.delimiter);
}
