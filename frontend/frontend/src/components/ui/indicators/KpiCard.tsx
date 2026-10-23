type Props = {
  label: string;
  value: string;
  caption?: string; // por ejemplo el período del dato
  changeText: string | null;
  negative?: boolean;
};

export function KpiCard({ label, value, caption, changeText, negative = false }: Props) {
  return (
    <div className="border border-gray-300 bg-white p-4">
      <p className="text-sm text-gray-700">{label}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        {changeText && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              negative ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-800'
            }`}
          >
            {changeText}
          </span>
        )}
      </div>
      {caption && <p className="mt-1 text-xs text-gray-500">{caption}</p>}
    </div>
  );
}
