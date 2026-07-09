import React from "react";

/** Case-detail horizontal stage stepper — the onboarding workflow made visual. Each stage is
 * done / active / pending; the theme colors is-done (green), is-active (yellow ring), is-pending (muted). */
export type Stage = { label: string; state: "done" | "active" | "pending" };

export function StageStepper({ stages }: { stages: Stage[] }) {
  return (
    <div className="stepper">
      {stages.map((s) => (
        <div key={s.label} className={`step is-${s.state}`}>{s.label}</div>
      ))}
    </div>
  );
}

/** Parallel functional-review grid — one card per team with its state chip. */
export function ReviewGrid({ reviews }: { reviews: { team: string; state: string }[] }) {
  return (
    <div className="review-grid">
      {reviews.map((r) => (
        <div key={r.team} className="review-card">
          <h5>{r.team}</h5>
          <span className={`chip chip-${r.state.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>{r.state}</span>
        </div>
      ))}
    </div>
  );
}
