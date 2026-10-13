"use client";

export function RowActionsMenu({ label, disabled, onInsert, onDuplicate, onDelete }: {
  label: string; disabled: boolean; onInsert: (placement: "above" | "below") => void;
  onDuplicate: () => void; onDelete: () => void;
}) {
  return <details className="admin-overflow admin-row-overflow" onToggle={event => {
    if (!event.currentTarget.open) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const panel = event.currentTarget.querySelector<HTMLElement>(".admin-overflow-menu");
    const height = panel?.getBoundingClientRect().height ?? 160;
    const width = panel?.getBoundingClientRect().width ?? 180;
    event.currentTarget.style.setProperty("--menu-top", (window.innerHeight - rect.bottom >= height + 8 ? rect.bottom + 4 : Math.max(8, rect.top - height - 4)) + "px");
    event.currentTarget.style.setProperty("--menu-left", Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)) + "px");
  }}><summary aria-label={label} onClick={event => { event.stopPropagation(); if (disabled) event.preventDefault(); }}>•••</summary>
    <div className="admin-overflow-menu" onClick={event => { event.stopPropagation(); const menu = event.currentTarget.closest("details"); if (menu) menu.open = false; }}>
      <button disabled={disabled} onClick={() => onInsert("above")}>Insert row above</button>
      <button disabled={disabled} onClick={() => onInsert("below")}>Insert row below</button>
      <button disabled={disabled} onClick={onDuplicate}>Duplicate row</button>
      <button disabled={disabled} className="admin-danger" onClick={onDelete}>Delete row</button>
    </div>
  </details>;
}
