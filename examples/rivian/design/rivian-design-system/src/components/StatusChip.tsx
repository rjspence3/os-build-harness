import React from "react";

/** Value-tinted status chip — the queue's STATUS/SLA cells. The tint class is derived from the value
 * (`chip chip-<lowercased-value>`), matching the ODC list-screen recipe's data-driven class contract. */
export type ChipKind = "chip" | "tag" | "badge";

export function StatusChip({ value, kind = "chip" }: { value: string; kind?: ChipKind }) {
  const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  return <span className={`${kind} ${kind}-${slug}`}>{value}</span>;
}

/** Tier tag — `T1 · CRITICAL` (yellow) vs `T2 · STANDARD` (muted). */
export function TierTag({ tier }: { tier: string }) {
  const critical = /t1|critical/i.test(tier);
  return <span className={`tag ${critical ? "tag-t1" : "tag-t2"}`}>{tier}</span>;
}
