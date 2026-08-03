// Single source of truth for tyre compound presentation (colors, labels, order).
// All components must use these helpers so compounds render identically everywhere.

export const TYRE_COLORS = {
  soft: "#e10600",
  medium: "#ffd500",
  hard: "#ffffff",
  intermediate: "#39d353",
  wet: "#0096ff",
};

export const TYRE_LABELS = {
  soft: "Soft",
  medium: "Medium",
  hard: "Hard",
  intermediate: "Intermediate",
  wet: "Wet",
};

// Maps any spelling (EN / PT-BR) to a canonical key.
const TYRE_ALIASES = {
  soft: "soft", macio: "soft",
  medium: "medium", medio: "medium", "médio": "medium",
  hard: "hard", duro: "hard",
  intermediate: "intermediate", intermediario: "intermediate", "intermediário": "intermediate",
  wet: "wet", chuva: "wet",
};

export const TYRE_ORDER = {
  soft: 1,
  medium: 2,
  hard: 3,
  intermediate: 4,
  wet: 5,
};

export function canonicalTyre(tyre) {
  if (tyre == null) return null;
  return TYRE_ALIASES[String(tyre).toLowerCase()] || null;
}

export function tyreColor(tyre) {
  const key = canonicalTyre(tyre);
  return key ? TYRE_COLORS[key] : "#888";
}

export function formatTyre(tyre) {
  if (tyre == null) return "-";
  const key = canonicalTyre(tyre);
  return key ? TYRE_LABELS[key] : String(tyre);
}

export function tyreOrder(tyre) {
  const key = canonicalTyre(tyre);
  return key ? TYRE_ORDER[key] : null;
}

export const PACE_DELTAS = [
  { compound: "Soft", color: TYRE_COLORS.soft, delta: 0 },
  { compound: "Medium", color: TYRE_COLORS.medium, delta: 0.45 },
  { compound: "Hard", color: TYRE_COLORS.hard, delta: 0.85 },
];
