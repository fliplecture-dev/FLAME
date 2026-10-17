import { FliplectureLogo } from "./fliplecture-logo";

/** Fliplecture product identity; FLAME is its learning engine. */
export function FlameBrand({ compact = false }: { compact?: boolean }) {
  return (
    <a className={`brand ${compact ? "brand-compact" : ""}`} href="/" aria-label="Fliplecture home">
      <FliplectureLogo />
      {!compact && <span className="brand-parent">Learning with FLAME</span>}
    </a>
  );
}
