// Written with Super Intelligence (SI) assistance.
// One colour per action, used by the map, the legend, the list and the evidence graph.
// "No class" has no colour of its own: it is not drawn, or drawn as a faint grey outline.

const ACTION_COLORS: Record<string, string> = {
  fire_detected: "#ff5a36", // red-orange: fire was detected on this peat
  fell_still_low: "#3b82f6", // blue: the echo fell and was still low after the first rain
  fell_came_back: "#f5c431", // amber: the echo fell and came back with the rain
};

export const NONE_COLOR = "#8b949e";
export const NO_ACTION = "none";
const DARK = "#12161a";

// Agreement (a count of conditions that hold, stored as "confidence") is shown as strength of colour: the share of the action colour that is kept.
const STRENGTH: Record<string, number> = { high: 0.92, medium: 0.64, low: 0.4 };

export function actionColor(action: string): string {
  return ACTION_COLORS[action] ?? NONE_COLOR;
}

export function confidenceStrength(confidence: string | null): number {
  return STRENGTH[confidence ?? ""] ?? STRENGTH.low;
}

export const CONFIDENCE_LEVELS = Object.keys(STRENGTH);

function rgb(hex: string): number[] {
  return [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16));
}

/** The action colour mixed towards the dark map by confidence, for layers that cannot vary opacity. */
export function solidColor(action: string, confidence: string | null): string {
  const t = confidenceStrength(confidence);
  const a = rgb(actionColor(action));
  const b = rgb(DARK);
  const mix = a.map((v, k) => Math.round(v * t + b[k] * (1 - t)));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}
