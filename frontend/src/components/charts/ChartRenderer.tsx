/**
 * ChartRenderer — smart chart component that renders the appropriate
 * Recharts chart based on a ChartSpec from the visualization agent.
 *
 * Supports: bar, line, area, pie, scatter, radar
 * Features: theme-aware, responsive, animated, curated color palette
 */

import { memo, useState, useRef } from "react";
import { motion } from "framer-motion";
import { ChartToolbar } from "./ChartToolbar";
import { InlineDataCard } from "./InlineDataCard";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { ChartSpec } from "../../store/useStore";
import { ChartTooltip } from "./ChartTooltip";

const DEFAULT_COLORS = [
  "#6366F1", "#8B5CF6", "#EC4899", "#F59E0B",
  "#10B981", "#06B6D4", "#F97316", "#84CC16",
];

interface ChartRendererProps {
  spec: ChartSpec;
  height?: number;
  compact?: boolean;
  showDataCard?: boolean;
}

function ChartRendererInner({
  spec,
  height = 320,
  compact = false,
  showDataCard = false,
}: ChartRendererProps): React.ReactElement {
  const [hovered, setHovered] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  const colors = spec.colors?.length ? spec.colors : DEFAULT_COLORS;
  const { chart_type, data, x_key, y_keys, title } = spec;

  const chartMargin = compact
    ? { top: 8, right: 8, left: 0, bottom: 8 }
    : { top: 12, right: 24, left: 8, bottom: 8 };

  const renderChart = () => {
    switch (chart_type) {
      case "bar":
        return (
          <BarChart data={data} margin={chartMargin}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey={x_key}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip content={<ChartTooltip />} />
            {y_keys.length > 1 && (
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              />
            )}
            {y_keys.map((key, idx) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[idx % colors.length]}
                radius={[4, 4, 0, 0]}
                animationDuration={800}
                animationEasing="ease-out"
              />
            ))}
          </BarChart>
        );

      case "line":
        return (
          <LineChart data={data} margin={chartMargin}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey={x_key}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip content={<ChartTooltip />} />
            {y_keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />}
            {y_keys.map((key, idx) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[idx % colors.length]}
                strokeWidth={2.5}
                dot={{ r: 3, fill: colors[idx % colors.length] }}
                activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
                animationDuration={1200}
                animationEasing="ease-out"
              />
            ))}
          </LineChart>
        );

      case "area":
        return (
          <AreaChart data={data} margin={chartMargin}>
            <defs>
              {y_keys.map((key, idx) => (
                <linearGradient key={key} id={`gradient-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors[idx % colors.length]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={colors[idx % colors.length]} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey={x_key}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip content={<ChartTooltip />} />
            {y_keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />}
            {y_keys.map((key, idx) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[idx % colors.length]}
                strokeWidth={2}
                fill={`url(#gradient-${key})`}
                animationDuration={1200}
                animationEasing="ease-out"
              />
            ))}
          </AreaChart>
        );

      case "pie":
        return (
          <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
            <Pie
              data={data}
              dataKey={y_keys[0]}
              nameKey={x_key}
              cx="50%"
              cy="50%"
              outerRadius={height * 0.35}
              innerRadius={height * 0.18}
              paddingAngle={2}
              animationDuration={1000}
              animationEasing="ease-out"
              label={({ name, percent }: { name: string; percent: number }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={{ strokeWidth: 1 }}
            >
              {data.map((_, idx) => (
                <Cell
                  key={idx}
                  fill={colors[idx % colors.length]}
                  stroke="transparent"
                />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          </PieChart>
        );

      case "scatter":
        return (
          <ScatterChart margin={chartMargin}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey={x_key}
              type="number"
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              name={x_key}
            />
            <YAxis
              dataKey={y_keys[0]}
              type="number"
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={50}
              name={y_keys[0]}
            />
            <Tooltip content={<ChartTooltip />} />
            <Scatter
              data={data}
              fill={colors[0]}
              animationDuration={800}
            />
          </ScatterChart>
        );

      case "radar":
        return (
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
            <PolarGrid strokeOpacity={0.2} />
            <PolarAngleAxis
              dataKey={x_key}
              tick={{ fontSize: 11 }}
            />
            <PolarRadiusAxis
              tick={{ fontSize: 10 }}
              axisLine={false}
            />
            {y_keys.map((key, idx) => (
              <Radar
                key={key}
                dataKey={key}
                stroke={colors[idx % colors.length]}
                fill={colors[idx % colors.length]}
                fillOpacity={0.15}
                strokeWidth={2}
                animationDuration={800}
              />
            ))}
            <Tooltip content={<ChartTooltip />} />
            {y_keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />}
          </RadarChart>
        );

      default:
        return (
          <div className="flex items-center justify-center h-full text-text-muted text-sm">
            Unsupported chart type: {chart_type}
          </div>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="chart-container my-4 relative group/chart"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Hover toolbar */}
      {showDataCard && (
        <ChartToolbar spec={spec} visible={hovered} chartRef={chartRef} />
      )}

      {/* Wrapper for image export (needs solid background) */}
      <div ref={chartRef} className="bg-bg-surface rounded-xl pb-1" style={{ contain: "paint" }}>
        {/* Chart header */}
        {title && (
          <div className="px-4 pt-3 pb-1">
            <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
          </div>
        )}

        {/* Chart body */}
        <div className="px-2 pb-2" style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            {renderChart()}
          </ResponsiveContainer>
        </div>
      </div>

      {/* Inline data card */}
      {showDataCard && data && data.length > 0 && (
        <div className="px-3 pb-3">
          <InlineDataCard data={data} />
        </div>
      )}
    </motion.div>
  );
}

export const ChartRenderer = memo(ChartRendererInner);
