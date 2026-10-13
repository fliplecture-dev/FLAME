/** The product logo and its quieter parent-brand endorsement. */
export function FlameBrand({ logoSrc, compact = false }: { logoSrc?: string; compact?: boolean }) {
  return (
    <a className={`brand ${logoSrc ? "brand-with-logo" : ""} ${compact ? "brand-compact" : ""}`} href="/" aria-label="FLAME home — by FlipLecture">
      {logoSrc ? <img className="brand-logo" src={logoSrc} alt="FLAME" width={174} height={58} /> : <span className="brand-wordmark">FLAME</span>}
      {!compact && <span className="brand-parent">by FlipLecture</span>}
    </a>
  );
}
