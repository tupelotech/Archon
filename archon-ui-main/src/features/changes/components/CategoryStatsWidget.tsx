/**
 * CategoryStatsWidget Component
 *
 * Displays statistics about changes by category with visual breakdown.
 * Supports both client-side calculation from changes array or API-fetched stats.
 */

import {
  Bug,
  FileText,
  GitBranch,
  Loader2,
  Package,
  Palette,
  Settings,
  Sparkles,
  TestTube,
  TrendingUp,
  Wrench,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo } from "react";
import { Card } from "../../ui/primitives";
import { cn } from "../../ui/primitives/styles";
import { useChangeStats } from "../hooks";
import type { Change, ChangeStats, ChangeType } from "../types";
import { CHANGE_TYPES, CHANGE_TYPE_CONFIG } from "../types";

export interface CategoryStatsWidgetProps {
  changes?: Change[]; // Optional - if provided, calculates stats client-side
  projectId?: string; // Optional - if provided without changes, fetches from API
  days?: number; // Number of days for API stats (default 30)
  className?: string;
  compact?: boolean;
  showTrendChart?: boolean;
}

// Icon mapping for change types
const STAT_ICONS: Record<ChangeType, React.ReactNode> = {
  feature: <Sparkles className="w-4 h-4" />,
  bugfix: <Bug className="w-4 h-4" />,
  refactor: <Wrench className="w-4 h-4" />,
  docs: <FileText className="w-4 h-4" />,
  config: <Settings className="w-4 h-4" />,
  test: <TestTube className="w-4 h-4" />,
  style: <Palette className="w-4 h-4" />,
  perf: <Zap className="w-4 h-4" />,
  deps: <Package className="w-4 h-4" />,
  ci: <GitBranch className="w-4 h-4" />,
};

// Color mapping for pie chart (using CSS color values)
const PIE_COLORS: Record<ChangeType, string> = {
  feature: "#34d399", // emerald-400
  bugfix: "#fb7185", // rose-400
  refactor: "#fbbf24", // amber-400
  docs: "#38bdf8", // sky-400
  config: "#a78bfa", // violet-400
  test: "#22d3ee", // cyan-400
  style: "#f472b6", // pink-400
  perf: "#fb923c", // orange-400
  deps: "#a3e635", // lime-400
  ci: "#818cf8", // indigo-400
};

// Calculate statistics from changes (client-side)
function calculateStatsFromChanges(changes: Change[]): ChangeStats {
  const by_type: Record<ChangeType, number> = {} as Record<ChangeType, number>;
  for (const type of CHANGE_TYPES) {
    by_type[type] = 0;
  }

  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);

  let currentWeek = 0;
  let previousWeek = 0;
  const weekCounts: Record<string, number> = {};

  for (const change of changes) {
    const ctype = change.change_type;
    if (ctype in by_type) {
      by_type[ctype]++;
    }

    const changeDate = new Date(change.created_at);

    // Track trend
    if (changeDate >= sevenDaysAgo) {
      currentWeek++;
    } else if (changeDate >= fourteenDaysAgo) {
      previousWeek++;
    }

    // Track by week
    const weekStart = new Date(changeDate);
    weekStart.setDate(weekStart.getDate() - weekStart.getDay());
    const weekKey = weekStart.toISOString().slice(0, 10);
    weekCounts[weekKey] = (weekCounts[weekKey] || 0) + 1;
  }

  const percentChange =
    previousWeek === 0
      ? currentWeek > 0
        ? 100
        : 0
      : Math.round(((currentWeek - previousWeek) / previousWeek) * 100);

  const by_week = Object.entries(weekCounts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([week, count]) => ({ week, count }));

  return {
    by_type,
    by_week,
    by_project: [],
    total: changes.length,
    trend: {
      current_week: currentWeek,
      previous_week: previousWeek,
      percent_change: percentChange,
    },
    days: 30,
  };
}

// Simple SVG Pie Chart component
function PieChart({ data, size = 120 }: { data: Array<{ type: ChangeType; count: number }>; size?: number }) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  if (total === 0) return null;

  const radius = size / 2 - 10;
  const centerX = size / 2;
  const centerY = size / 2;

  let currentAngle = -Math.PI / 2; // Start from top

  const segments = data
    .filter((item) => item.count > 0)
    .map((item) => {
      const percentage = item.count / total;
      const angle = percentage * 2 * Math.PI;

      const startX = centerX + radius * Math.cos(currentAngle);
      const startY = centerY + radius * Math.sin(currentAngle);

      currentAngle += angle;

      const endX = centerX + radius * Math.cos(currentAngle);
      const endY = centerY + radius * Math.sin(currentAngle);

      const largeArcFlag = angle > Math.PI ? 1 : 0;

      const pathData =
        percentage === 1
          ? // Full circle
            `M ${centerX},${centerY - radius}
             A ${radius},${radius} 0 1,1 ${centerX - 0.001},${centerY - radius}
             Z`
          : // Arc segment
            `M ${centerX},${centerY}
             L ${startX},${startY}
             A ${radius},${radius} 0 ${largeArcFlag},1 ${endX},${endY}
             Z`;

      return {
        type: item.type,
        count: item.count,
        percentage,
        pathData,
        color: PIE_COLORS[item.type],
      };
    });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      {segments.map((segment) => (
        <path
          key={segment.type}
          d={segment.pathData}
          fill={segment.color}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="1"
          className="transition-opacity hover:opacity-80"
        >
          <title>
            {CHANGE_TYPE_CONFIG[segment.type].label}: {segment.count} ({Math.round(segment.percentage * 100)}%)
          </title>
        </path>
      ))}
      {/* Center hole for donut effect */}
      <circle cx={centerX} cy={centerY} r={radius * 0.5} fill="rgba(0,0,0,0.3)" />
      {/* Total in center */}
      <text
        x={centerX}
        y={centerY - 5}
        textAnchor="middle"
        className="fill-gray-200 text-lg font-bold"
        style={{ fontSize: "18px" }}
      >
        {total}
      </text>
      <text
        x={centerX}
        y={centerY + 12}
        textAnchor="middle"
        className="fill-gray-400 text-xs"
        style={{ fontSize: "10px" }}
      >
        changes
      </text>
    </svg>
  );
}

// Simple bar chart for weekly trend
function TrendChart({
  data,
  height = 60,
}: {
  data: Array<{ week: string; count: number }>;
  height?: number;
}) {
  if (data.length === 0) return null;

  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const barWidth = 100 / Math.max(data.length, 1);

  // Take last 8 weeks
  const recentData = data.slice(-8);

  return (
    <div className="w-full" style={{ height }}>
      <div className="flex items-end justify-between h-full gap-1">
        {recentData.map((item, index) => {
          const barHeight = (item.count / maxCount) * 100;
          return (
            <div
              key={item.week}
              className="flex-1 flex flex-col items-center gap-1"
              style={{ maxWidth: `${barWidth}%` }}
            >
              <div
                className="w-full bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t transition-all duration-300 hover:from-cyan-500 hover:to-cyan-300"
                style={{ height: `${Math.max(barHeight, 5)}%` }}
                title={`Week of ${item.week}: ${item.count} changes`}
              />
              {index === recentData.length - 1 && (
                <span className="text-[9px] text-gray-500">now</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const CategoryStatsWidget: React.FC<CategoryStatsWidgetProps> = ({
  changes,
  projectId,
  days = 30,
  className,
  compact = false,
  showTrendChart = true,
}) => {
  // Fetch from API if no changes provided
  const { data: apiStats, isLoading, error } = useChangeStats(
    projectId,
    days,
    !changes // Only fetch if no changes provided
  );

  // Calculate stats from changes or use API data
  const stats: ChangeStats | null = useMemo(() => {
    if (changes) {
      return calculateStatsFromChanges(changes);
    }
    return apiStats || null;
  }, [changes, apiStats]);

  // Prepare pie chart data
  const pieData = useMemo(() => {
    if (!stats) return [];
    return CHANGE_TYPES.map((type) => ({
      type,
      count: stats.by_type[type] || 0,
    })).filter((item) => item.count > 0);
  }, [stats]);

  // Sort by count for the breakdown list
  const sortedStats = useMemo(() => {
    if (!stats) return [];
    return CHANGE_TYPES.map((type) => ({
      type,
      count: stats.by_type[type] || 0,
    }))
      .filter((item) => item.count > 0)
      .sort((a, b) => b.count - a.count);
  }, [stats]);

  if (isLoading) {
    return (
      <Card blur="md" transparency="light" className={cn("p-6 flex items-center justify-center", className)}>
        <Loader2 className="w-5 h-5 animate-spin text-cyan-500" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card blur="md" transparency="light" className={cn("p-4 text-center", className)}>
        <p className="text-sm text-rose-400">Failed to load statistics</p>
      </Card>
    );
  }

  if (!stats || stats.total === 0) {
    return (
      <Card blur="md" transparency="light" className={cn("p-4 text-center", className)}>
        <p className="text-sm text-gray-500 dark:text-gray-400">No changes to display</p>
      </Card>
    );
  }

  const maxCount = Math.max(...sortedStats.map((s) => s.count));

  return (
    <Card blur="md" transparency="light" className={cn("p-4", className)}>
      <div className={cn("flex gap-6", compact && "flex-col")}>
        {/* Left side: Pie chart */}
        <div className="shrink-0 flex flex-col items-center">
          <PieChart data={pieData} size={compact ? 100 : 120} />
          {/* Trend indicator below chart */}
          <div className="flex items-center gap-1.5 mt-3 text-xs">
            <TrendingUp
              className={cn(
                "w-3.5 h-3.5",
                stats.trend.percent_change >= 0 ? "text-emerald-500" : "text-rose-500",
              )}
            />
            <span
              className={cn(
                "font-medium",
                stats.trend.percent_change >= 0 ? "text-emerald-500" : "text-rose-500",
              )}
            >
              {stats.trend.percent_change >= 0 ? "+" : ""}
              {stats.trend.percent_change}%
            </span>
            <span className="text-gray-500 dark:text-gray-400">vs last week</span>
          </div>
        </div>

        {/* Right side: Breakdown and trend */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Change Distribution
          </h3>

          {/* Stats breakdown */}
          <div className={cn("space-y-2", compact && "space-y-1.5")}>
            {sortedStats.slice(0, compact ? 4 : 6).map(({ type, count }) => {
              const config = CHANGE_TYPE_CONFIG[type];
              const percentage = Math.round((count / stats.total) * 100);
              const barWidth = maxCount > 0 ? (count / maxCount) * 100 : 0;

              return (
                <div key={type} className="group">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={cn("shrink-0", config.color)}>{STAT_ICONS[type]}</span>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300 min-w-[55px]">
                      {config.label}
                    </span>
                    <div className="flex-1 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{ width: `${barWidth}%`, backgroundColor: PIE_COLORS[type] }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 min-w-[35px] text-right tabular-nums">
                      {count} <span className="text-gray-400">({percentage}%)</span>
                    </span>
                  </div>
                </div>
              );
            })}
            {sortedStats.length > (compact ? 4 : 6) && (
              <p className="text-xs text-gray-500 pl-6">
                +{sortedStats.length - (compact ? 4 : 6)} more categories
              </p>
            )}
          </div>

          {/* Weekly trend chart */}
          {showTrendChart && stats.by_week.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-200/50 dark:border-gray-700/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Weekly Activity</span>
                <span className="text-xs font-medium text-cyan-500">{stats.trend.current_week} this week</span>
              </div>
              <TrendChart data={stats.by_week} height={compact ? 40 : 50} />
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
