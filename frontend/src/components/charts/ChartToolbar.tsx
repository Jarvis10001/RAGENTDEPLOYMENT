/**
 * ChartToolbar — floating action bar that appears on hover over inline charts.
 *
 * Actions: Expand to panel, Download data as CSV, Download as Image
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toPng } from "html-to-image";
import { IconExpand, IconDownload, IconCheck, IconImage } from "../ui/icons";
import { useStore, type ChartSpec } from "../../store/useStore";

interface ChartToolbarProps {
  spec: ChartSpec;
  visible: boolean;
  chartRef?: React.RefObject<HTMLDivElement>;
}

export function ChartToolbar({ spec, visible, chartRef }: ChartToolbarProps): React.ReactElement {
  const [downloadedCsv, setDownloadedCsv] = useState(false);
  const [downloadedImg, setDownloadedImg] = useState(false);

  const handleExpand = () => {
    useStore.getState().setChartSpec(spec);
    useStore.getState().setRightPanelTab("chart");
    useStore.getState().setRightPanelOpen(true);
  };

  const handleDownloadCSV = () => {
    if (!spec.data || spec.data.length === 0) return;

    const keys = Object.keys(spec.data[0]);
    const header = keys.join(",");
    const rows = spec.data.map((row) =>
      keys.map((k) => {
        const val = row[k];
        const str = String(val ?? "");
        // Escape commas and quotes in CSV
        return str.includes(",") || str.includes('"')
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      }).join(",")
    );
    const csv = [header, ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const filename = spec.title ? spec.title.replace(/[^a-z0-9]/gi, '_').toLowerCase() : 'chart_data';
    link.setAttribute("download", `${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloadedCsv(true);
    setTimeout(() => setDownloadedCsv(false), 2000);
  };

  const handleDownloadImage = async () => {
    if (!chartRef?.current) return;

    try {
      const dataUrl = await toPng(chartRef.current, { cacheBust: true, pixelRatio: 2 });
      const link = document.createElement("a");
      link.download = `${spec.title ? spec.title.replace(/[^a-z0-9]/gi, '_').toLowerCase() : 'chart_image'}.png`;
      link.href = dataUrl;
      link.click();

      setDownloadedImg(true);
      setTimeout(() => setDownloadedImg(false), 2000);
    } catch (err) {
      console.error("Failed to generate image", err);
    }
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.15 }}
          className="absolute top-3 right-3 z-10 flex items-center gap-1 p-1 rounded-lg bg-bg-surface/90 border border-border/60 backdrop-blur-sm shadow-lg"
        >
          <button
            onClick={handleExpand}
            className="w-7 h-7 rounded-md flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
            title="Expand in panel"
          >
            <IconExpand size={13} />
          </button>

          {chartRef && (
            <button
              onClick={handleDownloadImage}
              className="w-7 h-7 rounded-md flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
              title={downloadedImg ? "Downloaded!" : "Download as Image"}
            >
              {downloadedImg ? (
                <IconCheck size={13} className="text-status-success" />
              ) : (
                <IconImage size={13} />
              )}
            </button>
          )}

          <button
            onClick={handleDownloadCSV}
            className="w-7 h-7 rounded-md flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-elevated transition-colors"
            title={downloadedCsv ? "Downloaded!" : "Download CSV"}
          >
            {downloadedCsv ? (
              <IconCheck size={13} className="text-status-success" />
            ) : (
              <IconDownload size={13} />
            )}
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
