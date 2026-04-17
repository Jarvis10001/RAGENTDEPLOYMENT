/**
 * ChartTooltip — custom Recharts tooltip with glassmorphism styling.
 * Theme-aware, formats numbers and percentages.
 */

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

function formatValue(val: number): string {
  if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
  if (Number.isInteger(val)) return val.toLocaleString();
  return val.toFixed(2);
}

export function ChartTooltip({
  active,
  payload,
  label,
}: ChartTooltipProps): React.ReactElement | null {
  if (!active || !payload?.length) return null;

  return (
    <div className="glass rounded-lg px-3 py-2.5 shadow-lg border border-border/50 min-w-[140px]">
      {label && (
        <p className="text-xs font-medium text-text-primary mb-1.5 border-b border-border-muted pb-1.5">
          {label}
        </p>
      )}
      <div className="space-y-1">
        {payload.map((entry, idx) => (
          <div key={idx} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-xs text-text-secondary truncate max-w-[100px]">
                {entry.name}
              </span>
            </div>
            <span className="text-xs font-semibold text-text-primary tabular-nums">
              {formatValue(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
