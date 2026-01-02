/**
 * ChangeTimeline Component
 *
 * Displays a chronological timeline of changes with filtering.
 */

import { Bug, FileText, Filter, GitBranch, Loader2, Package, Palette, Settings, Sparkles, TestTube, Wrench, Zap } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, Card } from "../../ui/primitives";
import { cn } from "../../ui/primitives/styles";
import { useChanges, useProjectChanges } from "../hooks";
import type { Change, ChangeFilters, ChangeType } from "../types";
import { CHANGE_TYPES, CHANGE_TYPE_CONFIG } from "../types";
import { ChangeCard } from "./ChangeCard";

// Storage key for filter preferences
const FILTER_STORAGE_KEY = "archon-change-filters";

// Get stored filters for a project
function getStoredFilters(projectId?: string): ChangeType[] {
  try {
    const stored = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!stored) return [];
    const data = JSON.parse(stored);
    const key = projectId || "global";
    return Array.isArray(data[key]) ? data[key] : [];
  } catch {
    return [];
  }
}

// Store filters for a project
function storeFilters(filters: ChangeType[], projectId?: string): void {
  try {
    const stored = localStorage.getItem(FILTER_STORAGE_KEY);
    const data = stored ? JSON.parse(stored) : {};
    const key = projectId || "global";
    data[key] = filters;
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Ignore storage errors
  }
}

export interface ChangeTimelineProps {
  projectId?: string; // If provided, shows only project changes
  onChangeClick?: (change: Change) => void;
  compact?: boolean;
  maxItems?: number;
  showFilters?: boolean;
}

// Icon mapping for filter buttons
const FILTER_ICONS: Record<ChangeType, React.ReactNode> = {
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

// Group changes by date
function groupChangesByDate(changes: Change[]): Map<string, Change[]> {
  const groups = new Map<string, Change[]>();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  for (const change of changes) {
    const changeDate = new Date(change.created_at);
    changeDate.setHours(0, 0, 0, 0);

    let groupKey: string;
    if (changeDate.getTime() === today.getTime()) {
      groupKey = "Today";
    } else if (changeDate.getTime() === yesterday.getTime()) {
      groupKey = "Yesterday";
    } else if (changeDate > weekAgo) {
      groupKey = "This Week";
    } else {
      groupKey = changeDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    }

    const existing = groups.get(groupKey) || [];
    groups.set(groupKey, [...existing, change]);
  }

  return groups;
}

export const ChangeTimeline: React.FC<ChangeTimelineProps> = ({
  projectId,
  onChangeClick,
  compact = false,
  maxItems,
  showFilters = true,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedTypes, setSelectedTypes] = useState<Set<ChangeType>>(() => {
    // Initialize from URL params first, then localStorage
    const urlTypes = searchParams.get("types");
    if (urlTypes) {
      const types = urlTypes.split(",").filter((t): t is ChangeType => CHANGE_TYPES.includes(t as ChangeType));
      return new Set(types);
    }
    return new Set(getStoredFilters(projectId));
  });
  const [showFilterPanel, setShowFilterPanel] = useState(() => selectedTypes.size > 0);

  // Sync URL params when filters change
  useEffect(() => {
    const types = Array.from(selectedTypes);
    if (types.length > 0) {
      searchParams.set("types", types.join(","));
    } else {
      searchParams.delete("types");
    }
    setSearchParams(searchParams, { replace: true });
    // Persist to localStorage
    storeFilters(types, projectId);
  }, [selectedTypes, projectId, searchParams, setSearchParams]);

  // Create filters object for API (single type for now, multi-select is client-side)
  const apiFilters: ChangeFilters = {};

  // Use appropriate hook based on whether projectId is provided
  const {
    data: changesData,
    isLoading,
    error,
  } = projectId
    ? useProjectChanges(projectId, 1, maxItems || 50)
    : useChanges(apiFilters, 1, maxItems || 50);

  // Apply client-side multi-select filter
  const allChanges = changesData?.changes || [];
  const filteredChanges = selectedTypes.size === 0
    ? allChanges
    : allChanges.filter((change) => selectedTypes.has(change.change_type));
  const groupedChanges = groupChangesByDate(filteredChanges);

  // Toggle a category in multi-select mode
  const handleToggleType = useCallback((changeType: ChangeType) => {
    setSelectedTypes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(changeType)) {
        newSet.delete(changeType);
      } else {
        newSet.add(changeType);
      }
      return newSet;
    });
  }, []);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setSelectedTypes(new Set());
  }, []);

  const hasActiveFilters = selectedTypes.size > 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-500" />
      </div>
    );
  }

  if (error) {
    return (
      <Card blur="md" transparency="light" className="p-6 text-center">
        <p className="text-red-400">Failed to load changes</p>
        <p className="text-sm text-gray-500 mt-1">{error.message}</p>
      </Card>
    );
  }

  if (allChanges.length === 0) {
    return (
      <Card blur="md" transparency="light" className="p-8 text-center">
        <div className="text-gray-400 dark:text-gray-500 mb-2">
          <Sparkles className="w-8 h-8 mx-auto opacity-50" />
        </div>
        <p className="text-gray-600 dark:text-gray-400">No changes recorded yet</p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
          Changes will appear here as they are logged
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter controls */}
      {showFilters && !projectId && (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={cn(showFilterPanel && "bg-cyan-500/10")}
          >
            <Filter className="w-4 h-4 mr-1.5" />
            Filter
          </Button>

          {showFilterPanel && (
            <div className="flex items-center gap-1 flex-wrap">
              <Button
                variant={selectedTypes.size === 0 ? "cyan" : "ghost"}
                size="xs"
                onClick={handleClearFilters}
              >
                All
              </Button>
              {CHANGE_TYPES.map((type) => {
                const config = CHANGE_TYPE_CONFIG[type];
                const isSelected = selectedTypes.has(type);
                return (
                  <Button
                    key={type}
                    variant={isSelected ? "cyan" : "ghost"}
                    size="xs"
                    onClick={() => handleToggleType(type)}
                    className={cn("gap-1", isSelected && "ring-1 ring-cyan-400/50")}
                  >
                    {FILTER_ICONS[type]}
                    {config.label}
                  </Button>
                );
              })}
              {hasActiveFilters && (
                <span className="text-xs text-gray-500 ml-2">
                  {selectedTypes.size} selected
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timeline grouped by date */}
      <div className="space-y-6">
        {Array.from(groupedChanges.entries()).map(([dateGroup, groupChanges]) => (
          <div key={dateGroup}>
            {/* Date group header */}
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {dateGroup}
              </span>
              <div className="flex-1 h-px bg-gradient-to-r from-gray-200 dark:from-gray-700 to-transparent" />
            </div>

            {/* Changes in this group */}
            <div className="space-y-2 pl-2 border-l-2 border-gray-200 dark:border-gray-700">
              {groupChanges.map((change) => (
                <div key={change.id} className="relative">
                  {/* Timeline dot */}
                  <div className="absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-gray-100 dark:bg-gray-800 border-2 border-gray-300 dark:border-gray-600" />
                  <div className="ml-4">
                    <ChangeCard change={change} onClick={onChangeClick} compact={compact} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
