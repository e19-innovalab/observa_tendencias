type Props = {
  label: string;
  value: string;
  change: number | null; // variación porcentual; puede ser negativa
};

const pct = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 1,
  signDisplay: 'exceptZero',
});

export function KpiCard({ label, value, change }: Props) {
  const negative = change !== null && change < 0;
  return (
    <div className="border border-gray-300 bg-white p-4">
      <p className="text-sm text-gray-700">{label}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        {change !== null && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              negative ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-800'
            }`}
          >
            {pct.format(change)}%
          </span>
        )}
      </div>
    </div>
  );
}
