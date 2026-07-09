// Rivian Supplier & Parts Onboarding — design tokens (mined from Supplier Onboarding.dc.html).
// Dark enterprise theme, near-black canvas, Rivian-yellow accent. Mirror of tokens.css for JS/TS consumers.

export const palette = {
  // surfaces
  bg: "#0c0e0c", panel: "#131612", panel2: "#191d17", panel3: "#1f241d",
  line: "#2a2f27", lineSoft: "#20241d",
  // text tiers
  ink: "#edefe8", ink2: "#a3a99c", ink3: "#6d7266", ink4: "#4a4e44",
  // brand accent + feedback
  yellow: "#ffd329", green: "#7fce8f", amber: "#f0b657", red: "#ef7d6b", blue: "#79b0e6",
} as const;

export const typography = {
  body: "'IBM Plex Sans', system-ui, sans-serif",
  heading: "'Space Grotesk', sans-serif",
  mono: "'JetBrains Mono', monospace",
  scale: { xs: 10, sm: 11, base: 13, md: 14, lg: 22, xl: 28 },
  weight: { regular: 400, medium: 500, semibold: 600, bold: 700 },
} as const;

export const spacing = { s1: 4, s2: 8, s3: 12, s4: 16, s5: 20, s6: 28 } as const;
export const radii = { r1: 3, r2: 5, r3: 10 } as const;
export const layout = { sidebarWidth: 248, contentMaxWidth: 1180 } as const;

// Status colors keyed to QualificationCase.Status / ScreeningResult / ReviewTask.State categories.
export const statusColor = {
  APPROVED: palette.green, ACTIVATED: palette.green, QUALIFIED: palette.green, CLEAR: palette.green,
  "IN REVIEW": palette.amber, PENDING: palette.amber,
  OVERDUE: palette.red, REJECTED: palette.red, BLOCKED: palette.red, BREACHED: palette.red,
  SCREENING: palette.blue,
} as const;

// Tier colors keyed to QualificationCase.Tier (T1 critical vs T2 standard).
export const tierColor = { "T1": palette.yellow, CRITICAL: palette.yellow, "T2": palette.ink2, STANDARD: palette.ink2 } as const;

export type StatusKey = keyof typeof statusColor;
export type TierKey = keyof typeof tierColor;
