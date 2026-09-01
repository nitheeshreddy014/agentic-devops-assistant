interface Props { missingInfo: string[] }
export default function MissingInfoPanel({ missingInfo }: Props) {
  if (!missingInfo.length) return null;
  return (
    <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-yellow-300 mb-2">⚠ Missing Information</h3>
      <ul className="space-y-1">
        {missingInfo.map((item, i) => (
          <li key={i} className="text-xs text-yellow-200 flex gap-2">
            <span className="text-yellow-500 shrink-0">•</span>{item}
          </li>
        ))}
      </ul>
      <p className="text-xs text-yellow-500 mt-2">
        Provide this information in the diagnostic output or start a new investigation with more context.
      </p>
    </div>
  );
}
