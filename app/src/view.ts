// Written with Super Intelligence (SI) assistance.
// Shared helpers for framing the map.

export const WIDE = "(min-width: 700px)";

// Room the floating panels take on a wide screen, so views are framed in the free part of the map.
export function viewPadding(): { top: number; bottom: number; left: number; right: number } {
  const wide = window.matchMedia(WIDE).matches;
  return wide ? { top: 24, bottom: 130, left: 300, right: 24 } : { top: 16, bottom: 16, left: 16, right: 16 };
}

export function reducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
