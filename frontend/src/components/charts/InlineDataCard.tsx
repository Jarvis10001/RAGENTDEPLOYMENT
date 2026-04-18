/**
 * InlineDataCard — collapsible raw data table rendered below inline charts.
 *
 * Shows a compact header with row count, expands to a styled scrollable table.
 * Includes "Download CSV" action.
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { IconChevronDown, IconDownload, IconCheck, IconDatabase } from "../ui/icons";

interface InlineDataCardProps {
  data: Record<string, unknown>[];
}

export function InlineDataCard({ data }: InlineDataCardProps): React.ReactElement | null {
  const [expanded, setExpanded] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0]);

  const handleDownloadCSV = useCallback(() => {
    const header = keys.join(",");
    const rows = data.map((row) =>
      keys
        .map((k) => {
          const val = row[k];
          const str = String(val ?? "");
          return str.includes(",") || str.includes('"')
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        })
        .join(",")
    );
    const csv = [header, ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "data_export.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2000);
  }, [data, keys]);

  const formatValue = (val: unknown): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "number") {
      // Format numbers with commas for readability
      return val.toLocaleString();
    }
    return String(val);
  };

  return (
    <div className="mt-2 rounded-xl border border-[#333333] bg-[#212121] overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-left hover:bg-bg-elevated/50 transition-colors"
      >
        <div className="w-6 h-6 rounded-md bg-bg-elevated flex items-center justify-center flex-shrink-0">
          <IconDatabase size={12} className="text-text-muted" />
        </div>
        <span className="flex-1 text-xs font-medium text-text-secondary">
          View raw data
        </span>
        <span className="text-[10px] text-text-muted bg-bg-elevated rounded-full px-2 py-0.5 font-medium tabular-nums">
          {data.length} row{data.length !== 1 ? "s" : ""}
        </span>
        <IconChevronDown
          size={12}
          className={`text-text-muted transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      {/* Expandable table */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-[#333333]">
              {/* Download button */}
              <div className="flex justify-end px-3 py-1.5">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownloadCSV();
                  }}
                  className="inline-flex items-center gap-1 text-[10px] text-text-muted hover:text-text-secondary transition-colors px-2 py-1 rounded-md hover:bg-bg-elevated"
                >
                  {downloaded ? (
                    <>
                      <IconCheck size={10} className="text-status-success" />
                      Downloaded
                    </>
                  ) : (
                    <>
                      <IconDownload size={10} />
                      Download CSV
                    </>
                  )}
                </button>
              </div>

              {/* Table */}
              <div className="max-h-[280px] overflow-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-bg-elevated/60">
                      {keys.map((key) => (
                        <th
                          key={key}
                          className="text-left px-3 py-2 font-semibold text-text-muted text-[10px] uppercase tracking-wider border-b border-[#333333] whitespace-nowrap"
                        >
                          {key.replace(/_/g, " ")}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, rowIdx) => (
                      <tr
                        key={rowIdx}
                        className={`
                          border-b border-[#333333] last:border-b-0
                          ${rowIdx % 2 === 0 ? "bg-transparent" : "bg-bg-elevated/20"}
                          hover:bg-accent/5 transition-colors
                        `}
                      >
                        {keys.map((key) => (
                          <td
                            key={key}
                            className="px-3 py-2 text-text-secondary whitespace-nowrap tabular-nums"
                          >
                            {formatValue(row[key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
