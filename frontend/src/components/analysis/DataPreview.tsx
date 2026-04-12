/**
 * DataPreview — shows SQL table data or vector search snippets
 * from the last tool response.
 */

import { useStore } from "../../store/useStore";

function SqlTable({ data }: { data: string }): React.ReactElement {
  // Try to parse tabular data from the tool output
  // Common formats: pipe-delimited tables, or raw rows
  const lines = data.split("\n").filter((l) => l.trim());

  // Attempt to detect a markdown-style table
  const pipeLines = lines.filter((l) => l.includes("|"));

  if (pipeLines.length >= 2) {
    const headerLine = pipeLines[0];
    const dataLines = pipeLines.filter((l) => !l.match(/^[\s|:-]+$/));
    const headers = headerLine
      .split("|")
      .map((h) => h.trim())
      .filter(Boolean);
    const rows = dataLines.slice(1).map((line) =>
      line
        .split("|")
        .map((cell) => cell.trim())
        .filter(Boolean)
    );

    if (headers.length > 0 && rows.length > 0) {
      return (
        <div className="overflow-x-auto rounded-input border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-bg-elevated">
                {headers.map((h, i) => (
                  <th
                    key={i}
                    className="text-left px-3 py-2 font-semibold text-text-secondary border-b border-border whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr
                  key={ri}
                  className={ri % 2 === 0 ? "bg-bg-primary" : "bg-bg-surface"}
                >
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-3 py-1.5 text-text-primary border-b border-border-muted whitespace-nowrap"
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  }

  // Fallback: plain text
  return (
    <pre className="p-3 text-xs font-mono bg-bg-elevated rounded-input border border-border-muted text-text-secondary overflow-x-auto max-h-64 overflow-y-auto">
      {data.slice(0, 2000)}
    </pre>
  );
}

function VectorSnippets({ data }: { data: string }): React.ReactElement {
  // Split on numbered items or double newlines
  const snippets = data
    .split(/\n(?=\d+[\.\)]\s)|\n\n/)
    .filter((s) => s.trim().length > 10)
    .slice(0, 8);

  if (snippets.length === 0) {
    return (
      <pre className="p-3 text-xs font-mono bg-bg-elevated rounded-input border border-border-muted text-text-secondary overflow-x-auto max-h-64 overflow-y-auto">
        {data.slice(0, 2000)}
      </pre>
    );
  }

  return (
    <div className="space-y-2">
      {snippets.map((snippet, idx) => (
        <blockquote
          key={idx}
          className="pl-3 border-l-2 border-accent/40 py-1.5 text-xs text-text-secondary leading-relaxed"
        >
          {snippet.trim().slice(0, 300)}
        </blockquote>
      ))}
    </div>
  );
}

export function DataPreview(): React.ReactElement {
  const dataPreview = useStore((s) => s.dataPreview);

  if (!dataPreview) {
    return (
      <div className="py-4 text-center text-sm text-text-muted">
        No data available
      </div>
    );
  }

  return (
    <div>
      {dataPreview.type === "sql" ? (
        <SqlTable data={dataPreview.data} />
      ) : (
        <VectorSnippets data={dataPreview.data} />
      )}
    </div>
  );
}
