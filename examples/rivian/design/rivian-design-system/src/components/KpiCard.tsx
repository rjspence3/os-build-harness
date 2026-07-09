import React from "react";

/** Dashboard KPI card — icon + live COUNT value + label + optional trend. The value must be a real
 * aggregate `.Count` at runtime (never `.List.Length`, which renders a wrong "1"). */
export function KpiCard({ icon, value, label, trend }: {
  icon?: string; value: React.ReactNode; label: string; trend?: string;
}) {
  return (
    <div className="kpi-card">
      {icon && <div className={`kpi-icon glyph-${icon}`} />}
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      {trend && <div className="kpi-trend">{trend}</div>}
    </div>
  );
}

export function KpiRow({ children }: { children: React.ReactNode }) {
  return <div className="kpi-row">{children}</div>;
}
