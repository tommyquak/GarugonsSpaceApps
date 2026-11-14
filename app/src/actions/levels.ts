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
  /** Opacity of the flat fill: the lowest level is kept faint so the other two stand out. */
  strength: number;
  /** The colour of a column, which cannot vary its opacity. */
  solid: string;
}

export const LEVELS: Level[] = [
  { id: 3, title: "Most affected", text: "Fire on several days, and the vegetation echo (HV) was still low after the rain.", color: "#ff3b30", strength: 0.95, solid: "#ff3b30" },
  { id: 2, title: "Affected", text: "The echo fell and was still low after the rain, or fire with the vegetation echo still low.", color: "#ff9f0a", strength: 0.92, solid: "#ff9f0a" },
  { id: 1, title: "Changed, then recovered", text: "Fire was detected or the echo fell, and the radar saw no lasting change after the rain.", color: "#f2d98a", strength: 0.3, solid: "#5f573f" },
];

export const LEVELS_NOTE = "Ranked by signs of lasting change in the radar and fire data. Not checked on the ground.";

export function levelOf(block: { action: string; confidence: string | null; states?: Record<string, boolean | null> }): number {
  if (block.action === NO_ACTION) return 0;
  if (block.action === "fire_detected" && block.confidence === "high") return 3;
  if (block.action === "fell_still_low" || (block.action === "fire_detected" && block.states?.canopy_low === true)) return 2;
  return 1;
}
