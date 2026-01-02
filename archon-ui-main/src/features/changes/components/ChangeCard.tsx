/**
 * ChangeCard Component
 *
 * Displays a single change entry in the timeline.
 */

import { Bug, CheckSquare, FileText, GitBranch, GitCommit, Package, Palette, Settings, Sparkles, TestTube, Wrench, Zap } from "lucide-react";
import type React from "react";
import { Card } from "../../ui/primitives";
import { cn } from "../../ui/primitives/styles";
import type { Change, ChangeType } from "../types";
import { CHANGE_TYPE_CONFIG } from "../types";

export interface ChangeCardProps {
  change: Change;
  onClick?: (change: Change) => void;
  onTaskClick?: (taskId: string) => void;
  compact?: boolean;
}

// Icon mapping for change types
const CHANGE_TYPE_ICONS: Record<ChangeType, React.ReactNode> = {
  feature: <Sparkles className="w-3.5 h-3.5" />,
  bugfix: <Bug className="w-3.5 h-3.5" />,
  refactor: <Wrench className="w-3.5 h-3.5" />,
  docs: <FileText className="w-3.5 h-3.5" />,
  config: <Settings className="w-3.5 h-3.5" />,
  test: <TestTube className="w-3.5 h-3.5" />,
  style: <Palette className="w-3.5 h-3.5" />,
  perf: <Zap className="w-3.5 h-3.5" />,
  deps: <Package className="w-3.5 h-3.5" />,
  ci: <GitBranch className="w-3.5 h-3.5" />,
};

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export const ChangeCard: React.FC<ChangeCardProps> = ({ change, onClick, onTaskClick, compact = false }) => {
  const typeConfig = CHANGE_TYPE_CONFIG[change.change_type];
  const icon = CHANGE_TYPE_ICONS[change.change_type];

  const handleClick = () => {
    onClick?.(change);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.(change);
    }
  };

  const handleTaskClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (change.task_id && onTaskClick) {
      onTaskClick(change.task_id);
    }
  };

  return (
    <Card
      blur="md"
      transparency="light"
      size="none"
      className={cn(
        "transition-all duration-200 ease-in-out cursor-pointer",
        "hover:border-cyan-400/50 hover:shadow-[0_0_15px_rgba(34,211,238,0.3)]",
        compact ? "p-3" : "p-4",
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start gap-3">
        {/* Change type indicator */}
        <div
          className={cn(
            "relative flex items-center justify-center rounded-lg backdrop-blur-md",
            "border border-current/20",
            compact ? "w-8 h-8" : "w-10 h-10",
            typeConfig.color,
          )}
        >
          <div className="absolute inset-0 rounded-lg bg-current opacity-15" />
          <span className={cn("relative z-10", typeConfig.color)}>{icon}</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 mb-1">
            <span
              className={cn(
                "relative px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide",
                "backdrop-blur-md border border-current/20",
                typeConfig.color,
              )}
            >
              <span className="absolute inset-0 rounded-full bg-current opacity-15" />
              <span className={cn("relative z-10", typeConfig.color)}>{typeConfig.label}</span>
            </span>

            <span className="text-xs text-gray-500 dark:text-gray-400">
              {formatRelativeTime(change.created_at)}
            </span>

            {change.task_id && onTaskClick && (
              <button
                type="button"
                onClick={handleTaskClick}
                className={cn(
                  "flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
                  "bg-violet-500/20 text-violet-400 border border-violet-400/30",
                  "hover:bg-violet-500/30 hover:border-violet-400/50 transition-colors",
                  "cursor-pointer"
                )}
                title="View linked task"
              >
                <CheckSquare className="w-3 h-3" />
                <span>Task</span>
              </button>
            )}

            {change.commit_sha && (
              <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 ml-auto">
                <GitCommit className="w-3 h-3" />
                <code className="font-mono">{change.commit_sha.slice(0, 7)}</code>
              </span>
            )}
          </div>

          {/* Summary */}
          <p
            className={cn(
              "text-gray-900 dark:text-white font-medium",
              compact ? "text-sm line-clamp-1" : "text-sm line-clamp-2",
            )}
          >
            {change.summary}
          </p>

          {/* Files affected (non-compact only) */}
          {!compact && change.files_affected && change.files_affected.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {change.files_affected.slice(0, 3).map((file) => (
                <code
                  key={file}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 font-mono"
                >
                  {file.split("/").pop()}
                </code>
              ))}
              {change.files_affected.length > 3 && (
                <span className="px-1.5 py-0.5 text-[10px] text-gray-500 dark:text-gray-400">
                  +{change.files_affected.length - 3} more
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
