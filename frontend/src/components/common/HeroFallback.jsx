export function HeroFallback() {
  return (
    <div
      role="img"
      aria-label="RAGFUSION knowledge core"
      className="absolute inset-0 overflow-hidden rounded-3xl bg-linear-to-br from-primary/20 via-background to-primary/5"
    >
      <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
        <div className="size-56 rounded-full border border-primary/30 bg-primary/10 shadow-[0_0_100px_var(--color-primary)]" />
        <div className="absolute size-36 rounded-full border border-primary/40 bg-linear-to-br from-primary/30 to-transparent" />
      </div>
    </div>
  )
}
