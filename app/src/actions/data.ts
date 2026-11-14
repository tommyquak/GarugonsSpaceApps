// Written with Super Intelligence (SI) assistance.
// Loads the fused blocks that scripts/copy_blocks.py puts in public/blocks (docs/DATA_CONTRACT.md
// section 6). The index and the ontology are small and read at the start; the blocks of a site
// are read only when the Actions view needs that site.
import { fetchJson } from "../data";
import { isOntology, type BlockProps, type Ontology } from "../ontology/model";

export interface BlockFeature {
  type: "Feature";
  properties: BlockProps;
  geometry: { type: "Polygon"; coordinates: number[][][] };
}

// One entry of blocks/index.json.
export interface SiteEntry {
  id: string;
  geojson: string;
  csv: string | null;
  compact: string | null;
  bounds: [number, number, number, number]; // west, south, east, north
  blocks: number;
  actions: Record<string, number>;
}

interface IndexFile {
  ontology?: string;
  sites?: SiteEntry[];
}

// The compact file of copy_blocks.py: the same blocks as rows of values, without the key names.
interface CompactFile {
  format: string;
  props: string[];
  obs: string[];
  states: string[];
  rows: unknown[][];
}

function expand(file: CompactFile): BlockFeature[] {
  const n = file.props.length;
  return file.rows.map((row) => {
    const props: Record<string, unknown> = {};
    file.props.forEach((key, i) => {
      props[key] = row[i];
    });
    const obs = row[n] as (number | null)[];
    const flags = row[n + 1] as (number | null)[];
    const flat = row[n + 3] as number[];
    props.obs = Object.fromEntries(file.obs.map((key, i) => [key, obs[i] ?? null]));
    props.states = Object.fromEntries(file.states.map((key, i) => [key, flags[i] === null || flags[i] === undefined ? null : flags[i] === 1]));
    props.reasons = row[n + 2];
    const ring: number[][] = [];
    for (let i = 0; i + 1 < flat.length; i += 2) ring.push([flat[i], flat[i + 1]]);
    ring.push(ring[0]);
    return { type: "Feature", properties: props as unknown as BlockProps, geometry: { type: "Polygon", coordinates: [ring] } };
  });
}

function usable(f: BlockFeature | null | undefined): f is BlockFeature {
  const p = f?.properties;
  return Boolean(p && typeof p.id === "string" && typeof p.action === "string" && p.obs && p.states && f?.geometry?.type === "Polygon");
}

export class BlockStore {
  private jobs = new Map<string, Promise<BlockFeature[]>>();
  private bySite = new Map<string, BlockFeature[]>();
  private byId = new Map<string, BlockFeature>();
  private listeners: ((site: string) => void)[] = [];

  constructor(
    readonly sites: SiteEntry[],
    readonly ontology: Ontology,
  ) {}

  /** Calls `fn` each time the blocks of a site have arrived. */
  onLoad(fn: (site: string) => void): void {
    this.listeners.push(fn);
  }

  /** The blocks of a site, fetched once. An unknown site or a failed download gives an empty list. */
  load(site: string): Promise<BlockFeature[]> {
    let job = this.jobs.get(site);
    if (!job) {
      job = this.fetchSite(site).then((features) => {
        this.bySite.set(site, features);
        for (const f of features) this.byId.set(f.properties.id, f);
        for (const fn of this.listeners) fn(site);
        return features;
      });
      this.jobs.set(site, job);
    }
    return job;
  }

  private async fetchSite(site: string): Promise<BlockFeature[]> {
    const entry = this.sites.find((s) => s.id === site);
    if (!entry) return [];
    if (entry.compact) {
      const file = await fetchJson<CompactFile>(entry.compact);
      if (file?.format === "blocks-compact" && Array.isArray(file.rows)) return expand(file).filter(usable);
    }
    const file = await fetchJson<{ features?: BlockFeature[] }>(entry.geojson);
    return Array.isArray(file?.features) ? file.features.filter(usable) : [];
  }

  loadAll(): Promise<BlockFeature[][]> {
    return Promise.all(this.sites.map((s) => this.load(s.id)));
  }

  isLoaded(site: string): boolean {
    return this.bySite.has(site);
  }

  /** The blocks of a site that has arrived, else an empty list. */
  features(site: string): BlockFeature[] {
    return this.bySite.get(site) ?? [];
  }

  get(id: string): BlockFeature | undefined {
    return this.byId.get(id);
  }

  /** The site a block id belongs to: ids start with the site, as in "west-042-017". */
  siteOf(id: string): string | null {
    return this.sites.find((s) => id.startsWith(`${s.id}-`))?.id ?? null;
  }

  /** How many blocks of a site got an action, from the index. Ranks count inside this number. */
  count(action: string, site?: string): number {
    return this.sites.filter((s) => !site || s.id === site).reduce((n, s) => n + (s.actions[action] ?? 0), 0);
  }
}

/** The store, or null when public/blocks is absent, in which case the Actions view stays hidden. */
export async function openStore(): Promise<BlockStore | null> {
  const index = await fetchJson<IndexFile>("blocks/index.json");
  const sites = (index?.sites ?? []).filter((s) => s && typeof s.id === "string" && typeof s.geojson === "string" && Array.isArray(s.bounds) && s.actions);
  if (!sites.length) return null;
  const ontology = await fetchJson<unknown>(index?.ontology ?? "blocks/ontology.json");
  return isOntology(ontology) ? new BlockStore(sites, ontology) : null;
}
