// Written with Super Intelligence (SI) assistance.
// The view for a first look: every classed block in one of three levels, by how strong the
// signs of lasting change are. The levels group the classes and states that blocks.py has
// already decided (docs/FUSION.md); they add no threshold and no number of their own.
//
//   3  fire on several days, and HV still low after the rain   (fire_detected, agreement high)
//   2  the echo fell and stayed low after the rain, or fire with HV still low after the rain
//   1  any other classed block: fire or a fall with no lasting change seen after the rain
import { NO_ACTION } from "./colors";

export interface Level {
  id: number;
  title: string;
  text: string;
  color: string;
  /** Opacity of the flat fill: the lowest level is by far the largest, so it is kept faint and the other two come forward. */
  strength: number;
  /** The colour of a column, which cannot vary its opacity. */
  solid: string;
  /** Height of a column in metres. A drawing height only: taller is a higher level, nothing more. */
  height: number;
}

export const LEVELS: Level[] = [
  { id: 3, title: "Most affected", text: "Fire on several days, and the vegetation echo (HV) was still low after the rain.", color: "#ff3b30", strength: 0.95, solid: "#ff3b30", height: 2600 },
  { id: 2, title: "Affected", text: "The echo fell and was still low after the rain, or fire with the vegetation echo still low.", color: "#ff9f0a", strength: 0.92, solid: "#ff9f0a", height: 1500 },
  { id: 1, title: "Changed, then recovered", text: "Fire was detected or the echo fell, and the radar saw no lasting change after the rain.", color: "#f2d98a", strength: 0.16, solid: "#454031", height: 350 },
];

export const LEVELS_NOTE = "Ranked by signs of lasting change in the radar and fire data. Not checked on the ground.";
export const LEVELS_HEIGHT_NOTE = "Height shows the level: the taller a block, the stronger the signs of lasting change.";

export function levelOf(block: { action: string; confidence: string | null; states?: Record<string, boolean | null> }): number {
  if (block.action === NO_ACTION) return 0;
  if (block.action === "fire_detected" && block.confidence === "high") return 3;
  if (block.action === "fell_still_low" || (block.action === "fire_detected" && block.states?.canopy_low === true)) return 2;
  return 1;
}
