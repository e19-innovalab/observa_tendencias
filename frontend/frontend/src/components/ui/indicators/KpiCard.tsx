type Props = {
  label: string;
  value: string;
  caption?: string; // por ejemplo país y período del dato
  changeText: string | null;
  negative?: boolean;
};

export function KpiCard({ label, value, caption, changeText, negative = false }: Props) {
  return (
    <article className="flex min-h-36 flex-col justify-between gap-3 rounded-lg border border-line bg-canvas p-5 shadow-[0_1px_2px_var(--shadow-color)]">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold tracking-wide text-muted-text uppercase">{label}</p>
        {changeText && (
          <span
            className={
              negative
                ? 'rounded-full bg-heading px-3 py-1 text-xs font-semibold text-white'
                : 'rounded-full bg-surface-2 px-3 py-1 text-xs font-semibold text-body'
            }
          >
            {changeText}
          </span>
        )}
      </div>

      <div>
        <p className="text-2xl font-semibold text-heading">{value}</p>
        {caption && <p className="mt-1 text-xs text-muted-text">{caption}</p>}
      </div>
    </article>
  );
}
