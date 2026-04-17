/**
 * DataPreview — shows SQL table data or vector search snippets
 * from the last tool response.
 */

import { useStore } from "../../store/useStore";
import { IconDatabase, IconLayers } from "../ui/icons";

function SqlTable({ data }: { data: string }): React.ReactElement {
  const lines = data.split("\n").filter((l) => l.trim());
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
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-bg-elevated">
                {headers.map((h, i) => (
                  <th
                    key={i}
                    className="text-left px-3 py-2 font-semibold text-text-secondary border-b border-border whitespace-nowrap text-[10px] uppercase tracking-wider"
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
                  className={`${ri % 2 === 0 ? "bg-bg-primary" : "bg-bg-surface"} hover:bg-accent/5 transition-colors`}
                >
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-3 py-1.5 text-text-primary border-b border-border-muted whitespace-nowrap text-[11px] tabular-nums"
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

  return (
    <pre className="p-3 text-[11px] font-mono bg-bg-elevated rounded-lg border border-border-muted text-text-secondary overflow-x-auto max-h-64 overflow-y-auto leading-relaxed">
      {data.slice(0, 2000)}
    </pre>
  );
}

function VectorSnippets({ data }: { data: string }): React.ReactElement {
  const snippets = data
    .split(/\n(?=\d+[\.)\]]\s)|\n\n/)
    .filter((s) => s.trim().length > 10)
    .slice(0, 8);

  if (snippets.length === 0) {
    return (
      <pre className="p-3 text-[11px] font-mono bg-bg-elevated rounded-lg border border-border-muted text-text-secondary overflow-x-auto max-h-64 overflow-y-auto leading-relaxed">
        {data.slice(0, 2000)}
      </pre>
    );
  }

  return (
    <div className="space-y-2">
      {snippets.map((snippet, idx) => (
        <blockquote
          key={idx}
          className="pl-3 border-l-2 border-accent/30 py-1.5 text-xs text-text-secondary leading-relaxed"
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
      <div className="flex flex-col items-center justify-center h-60 text-center px-4">
        <div className="w-12 h-12 rounded-xl bg-bg-elevated flex items-center justify-center mb-3">
          <IconDatabase size={20} className="text-text-muted" />
        </div>
        <p className="text-sm text-text-muted">No data preview</p>
        <p className="text-xs text-text-muted/60 mt-1.5 max-w-[220px]">
          SQL tables and vector search results will appear here
        </p>
      </div>
    );
  }

  return (
    <div className="p-3">
      <div className="flex items-center gap-2 mb-2.5">
        {dataPreview.type === "sql" ? (
          <IconDatabase size={14} className="text-accent" />
        ) : (
          <IconLayers size={14} className="text-accent" />
        )}
        <span className="text-xs font-semibold text-text-primary uppercase tracking-wider">
          {dataPreview.type === "sql" ? "SQL Results" : "Vector Search"}
        </span>
      </div>
      {dataPreview.type === "sql" ? (
        <SqlTable data={dataPreview.data} />
      ) : (
        <VectorSnippets data={dataPreview.data} />
      )}
    </div>
  );
}
