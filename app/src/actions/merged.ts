// Written with Super Intelligence (SI) assistance.
// The outline of each level in the 3D at-a-glance view: the blocks of one level that touch are
// joined into one shape, and the corners of that shape are slightly rounded, so the view reads
// as areas and not as loose cubes. It is a drawing only. The 1 km block stays the unit: the
// shapes are built from the blocks' own corners, the radius is a small part of a block, and
// the block under the pointer or selected is still drawn as a block on top (layer.ts).

/** Corner radius in metres. A block is 1 km across, so this is well under half a block. */
export const CORNER_RADIUS_M = 160;
const ARC_STEPS = 5;
const METRES_PER_DEGREE = 111_320;

type Point = [number, number];

export interface LevelShape {
  type: "Feature";
  properties: { level: number };
  geometry: { type: "Polygon"; coordinates: Point[][] };
}

const key = (p: number[]): string => `${p[0].toFixed(5)},${p[1].toFixed(5)}`;

// Twice the signed area of a ring: positive when it runs counter-clockwise.
function area2(ring: number[][]): number {
  let sum = 0;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % ring.length];
    sum += a[0] * b[1] - b[0] * a[1];
  }
  return sum;
}

interface Edge {
  from: string;
  to: string;
  a: number[];
  b: number[];
  used: boolean;
}

// The rings around a set of blocks: every block edge that no neighbour shares, chained end to
// end. Outer rings come out counter-clockwise and holes clockwise. Where two blocks touch only
// at a corner, each keeps its own ring (the walk always takes the leftmost turn).
function boundaryRings(blocks: number[][][]): number[][][] {
  const edges = new Map<string, Edge>();
  for (const block of blocks) {
    const ring = key(block[0]) === key(block[block.length - 1]) ? block.slice(0, -1) : block.slice();
    if (ring.length < 3) continue;
    if (area2(ring) < 0) ring.reverse();
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % ring.length];
      const from = key(a);
      const to = key(b);
      if (from !== to) edges.set(`${from}>${to}`, { from, to, a, b, used: false });
    }
  }
  const leaving = new Map<string, Edge[]>();
  for (const edge of edges.values()) {
    if (edges.has(`${edge.to}>${edge.from}`)) continue; // shared with a neighbour: inside the shape
    const list = leaving.get(edge.from);
    if (list) list.push(edge);
    else leaving.set(edge.from, [edge]);
  }
  const rings: number[][][] = [];
  for (const list of leaving.values()) {
    for (const first of list) {
      if (first.used) continue;
      const ring: number[][] = [];
      let edge: Edge | undefined = first;
      while (edge && !edge.used) {
        edge.used = true;
        ring.push(edge.a);
        const current: Edge = edge;
        const heading = Math.atan2(current.b[1] - current.a[1], current.b[0] - current.a[0]);
        let best: Edge | undefined;
        let bestTurn = -Infinity;
        for (const next of leaving.get(current.to) ?? []) {
          if (next.used) continue;
          let turn = Math.atan2(next.b[1] - next.a[1], next.b[0] - next.a[0]) - heading;
          while (turn > Math.PI) turn -= 2 * Math.PI;
          while (turn <= -Math.PI) turn += 2 * Math.PI;
          if (turn > bestTurn) {
            bestTurn = turn;
            best = next;
          }
        }
        edge = best;
      }
      if (ring.length >= 3) rings.push(ring);
    }
  }
  return rings;
}

// A ring with its corners rounded, worked in metres about the ring's first point. Points along
// a straight side are dropped first, so only true corners are rounded.
function rounded(ring: number[][], radius: number): Point[] {
  const [lon0, lat0] = ring[0];
  const kx = METRES_PER_DEGREE * Math.cos((lat0 * Math.PI) / 180);
  const metres = ring.map((p): Point => [(p[0] - lon0) * kx, (p[1] - lat0) * METRES_PER_DEGREE]);
  const corners = metres.filter((p, i) => {
    const a = metres[(i + metres.length - 1) % metres.length];
    const b = metres[(i + 1) % metres.length];
    const ux = p[0] - a[0];
    const uy = p[1] - a[1];
    const vx = b[0] - p[0];
    const vy = b[1] - p[1];
    const size = Math.hypot(ux, uy) * Math.hypot(vx, vy);
    return size > 0 && Math.abs(ux * vy - uy * vx) / size > 0.05;
  });
  if (corners.length < 3) return [];
  const out: Point[] = [];
  for (let i = 0; i < corners.length; i++) {
    const p = corners[i];
    const a = corners[(i + corners.length - 1) % corners.length];
    const b = corners[(i + 1) % corners.length];
    const toA = Math.hypot(a[0] - p[0], a[1] - p[1]);
    const toB = Math.hypot(b[0] - p[0], b[1] - p[1]);
    const d = Math.min(radius, toA / 2, toB / 2);
    const start: Point = [p[0] + ((a[0] - p[0]) / toA) * d, p[1] + ((a[1] - p[1]) / toA) * d];
    const end: Point = [p[0] + ((b[0] - p[0]) / toB) * d, p[1] + ((b[1] - p[1]) / toB) * d];
    for (let step = 0; step <= ARC_STEPS; step++) {
      const t = step / ARC_STEPS;
      const s = 1 - t;
      out.push([s * s * start[0] + 2 * s * t * p[0] + t * t * end[0], s * s * start[1] + 2 * s * t * p[1] + t * t * end[1]]);
    }
  }
  const back = out.map((p): Point => [lon0 + p[0] / kx, lat0 + p[1] / METRES_PER_DEGREE]);
  back.push(back[0]);
  return back;
}

function inside(point: Point, ring: Point[]): boolean {
  let hit = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i];
    const b = ring[j];
    if (a[1] > point[1] !== b[1] > point[1] && point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0]) hit = !hit;
  }
  return hit;
}

/** One rounded shape for each group of touching blocks of one level. `ring` is a block's outline, lon and lat. */
export function levelShapes(blocks: { ring: number[][]; level: number }[], radius = CORNER_RADIUS_M): LevelShape[] {
  const byLevel = new Map<number, number[][][]>();
  for (const block of blocks) {
    const list = byLevel.get(block.level);
    if (list) list.push(block.ring);
    else byLevel.set(block.level, [block.ring]);
  }
  const shapes: LevelShape[] = [];
  for (const [level, rings] of byLevel) {
    const outers: { ring: Point[]; area: number; holes: Point[][] }[] = [];
    const holes: Point[][] = [];
    for (const raw of boundaryRings(rings)) {
      const ring = rounded(raw, radius);
      if (ring.length < 4) continue;
      const area = area2(ring);
      if (area > 0) outers.push({ ring, area, holes: [] });
      else holes.push(ring);
    }
    outers.sort((a, b) => a.area - b.area); // smallest first, so a hole goes to the innermost shape around it
    for (const hole of holes) outers.find((outer) => inside(hole[0], outer.ring))?.holes.push(hole);
    for (const outer of outers) shapes.push({ type: "Feature", properties: { level }, geometry: { type: "Polygon", coordinates: [outer.ring, ...outer.holes] } });
  }
  return shapes;
}
