import React from "react";
import { StatusChip, TierTag } from "./StatusChip";

/** Case Queue row — the signature styled list unit: mono case id, owner avatar, tier tag, stage,
 * status chip, SLA-state badge. Anchors the queue's data-driven cell rendering. */
export type CaseRowData = {
  caseNo: string; owner: string; tier: string; stage: string; status: string; slaState: string;
};

export function CaseRow({ c }: { c: CaseRowData }) {
  const initials = c.owner.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
  return (
    <tr>
      <td><span className="cell-id">{c.caseNo}</span></td>
      <td><span className="avatar">{initials}</span></td>
      <td><TierTag tier={c.tier} /></td>
      <td>{c.stage}</td>
      <td><StatusChip value={c.status} kind="chip" /></td>
      <td><StatusChip value={c.slaState} kind="badge" /></td>
    </tr>
  );
}
