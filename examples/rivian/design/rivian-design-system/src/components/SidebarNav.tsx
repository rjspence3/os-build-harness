import React from "react";

/** App-shell sidebar — RIVIAN brand + subtitle, sectioned nav with mono 3-letter tag chips + count
 * badges, yellow active left-border, user footer with online dot. The signature chrome on every screen. */
export type NavItem = { label: string; tag: string; badge?: string; section: string; active?: boolean };

export function SidebarNav({ items, user }: {
  items: NavItem[]; user: { name: string; role: string };
}) {
  const sections = [...new Set(items.map((i) => i.section))];
  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">RIVIAN<small>Supplier &amp; Parts Onboarding</small></div>
      {sections.map((section) => (
        <div key={section}>
          <div className="nav-section">{section}</div>
          {items.filter((i) => i.section === section).map((i) => (
            <a key={i.label} className={`nav-item${i.active ? " is-active" : ""}`} href="#">
              <span className="nav-tag">{i.tag}</span>
              {i.label}
              {i.badge && <span className="nav-badge">{i.badge}</span>}
            </a>
          ))}
        </div>
      ))}
      <div className="sidebar-user">
        <span className="avatar">{user.name.split(" ").map((n) => n[0]).join("")}</span>
        <div>{user.name}<br /><small>{user.role}</small></div>
        <span className="online-dot" />
      </div>
    </aside>
  );
}
