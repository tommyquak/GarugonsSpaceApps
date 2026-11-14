// Written with Super Intelligence (SI) assistance.
// Data for the click-a-place chart: the radar time series of docs/DATA_CONTRACT.md section 4,
// the daily rain of section 2, and fire dates per cell when that file exists.

export interface Band {
  track: string;
  pol: "hh" | "hv";
  date: string; // YYYY-MM-DD
}

export interface SeriesMeta {
  site: string;
  bounds: [number, number, number, number]; // west, south, east, north in degrees
  cell_deg: number;
  rows: number;
  cols: number;
  scale: number;
  offset: number;
  nodata: number;
  bands: Band[];
}

export interface Line {
  track: string;
  pol: "hh" | "hv";
  points: { date: string; db: number }[];
}

export interface Place {
  site: string;
  lon: number;
  lat: number;
  lines: Line[]; // empty where the radar has no data
  season: [string, string]; // first and last radar date of the site
  rain: { date: string; mm: number }[];
  fires: string[]; // dates with a fire detection in this cell
}

/** Row and column of the cell that holds a point, or null outside the grid. */
export function cellAt(meta: SeriesMeta, lon: number, lat: number): { row: number; col: number } | null {
  const [west, , , north] = meta.bounds;
  const col = Math.floor((lon - west) / meta.cell_deg);
  const row = Math.floor((north - lat) / meta.cell_deg);
  if (col < 0 || row < 0 || col >= meta.cols || row >= meta.rows) return null;
  return { row, col };
}

/** One line per track and polarisation at a cell, in the order they first appear in `bands`. */
export function linesAt(meta: SeriesMeta, bin: Uint8Array, row: number, col: number): Line[] {
  const size = meta.rows * meta.cols;
  const lines = new Map<string, Line>();
  meta.bands.forEach((band, i) => {
    const byte = bin[i * size + row * meta.cols + col];
    if (byte === meta.nodata) return;
    const key = `${band.track}_${band.pol}`;
    if (!lines.has(key)) lines.set(key, { track: band.track, pol: band.pol, points: [] });
    lines.get(key)!.points.push({ date: band.date, db: byte * meta.scale + meta.offset });
  });
  for (const line of lines.values()) line.points.sort((a, b) => a.date.localeCompare(b.date));
  return [...lines.values()];
}

interface Site {
  meta: SeriesMeta;
  bin?: Promise<Uint8Array>;
  rain?: Promise<Record<string, number>>;
  fires?: Promise<Record<string, string[]>>;
}

// A missing file must not break the chart. A dev server may answer a missing file with
// its index page, so a body that is not JSON also counts as missing.
async function optionalJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(url);
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

/**
 * Loads `series_<site>.json` for every site up front (they are small) and the larger
 * `series_<site>.bin` on the first click inside that site.
 *
 * Files, all under `<base>series/`:
 *   series_<site>.json, series_<site>.bin   required, contract section 4
 *   rain_daily_<site>.json                  optional, contract section 2
 *   fire_dates_<site>.json                  optional, { "<row * cols + col>": ["YYYY-MM-DD", ...] }
 *                                           on the grid of series_<site>.json
 */
export class PlaceData {
  private sites: Promise<Site[]>;

  constructor(private base: string, siteNames: string[]) {
    this.sites = Promise.all(
      siteNames.map(async (name) => {
        const meta = await optionalJson<SeriesMeta | null>(`${base}series/series_${name}.json`, null);
        return meta && Array.isArray(meta.bands) ? { meta } : null;
      }),
    ).then((found) => found.filter((s): s is Site => s !== null));
  }

  /** True when at least one site has a time series file. */
  async available(): Promise<boolean> {
    return (await this.sites).length > 0;
  }

  /** Everything the chart shows for a point, or null when the point is outside every site. */
  async at(lon: number, lat: number): Promise<Place | null> {
    for (const site of await this.sites) {
      const cell = cellAt(site.meta, lon, lat);
      if (!cell) continue;
      const { meta } = site;
      const folder = `${this.base}series/`;
      site.bin ??= fetch(`${folder}series_${meta.site}.bin`).then(async (response) => {
        if (!response.ok) throw new Error(`series_${meta.site}.bin: HTTP ${response.status}`);
        const bytes = new Uint8Array(await response.arrayBuffer());
        const expected = meta.rows * meta.cols * meta.bands.length;
        if (bytes.length !== expected) {
          throw new Error(`series_${meta.site}.bin has ${bytes.length} bytes, expected ${expected}`);
        }
        return bytes;
      });
      site.rain ??= optionalJson<Record<string, number>>(`${folder}rain_daily_${meta.site}.json`, {});
      site.fires ??= optionalJson<Record<string, string[]>>(`${folder}fire_dates_${meta.site}.json`, {});
      let bin: Uint8Array;
      try {
        bin = await site.bin;
      } catch (error) {
        site.bin = undefined; // try again on the next click
        throw error;
      }
      const [rain, fires] = await Promise.all([site.rain, site.fires]);
      const dates = meta.bands.map((band) => band.date).sort();
      return {
        site: meta.site,
        lon,
        lat,
        lines: linesAt(meta, bin, cell.row, cell.col),
        season: [dates[0], dates[dates.length - 1]],
        rain: Object.entries(rain)
          .filter(([, mm]) => typeof mm === "number" && Number.isFinite(mm))
          .map(([date, mm]) => ({ date, mm }))
          .sort((a, b) => a.date.localeCompare(b.date)),
        fires: [...(fires[String(cell.row * meta.cols + cell.col)] ?? [])].sort(),
      };
    }
    return null;
  }
}
