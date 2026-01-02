/**
 * Change Tracking Types
 *
 * Types for tracking development changes made during AI-assisted sessions.
 */

// Change type enum - matches database
export type ChangeType =
  | "feature"
  | "bugfix"
  | "refactor"
  | "docs"
  | "config"
  | "test"
  | "style"
  | "perf"
  | "deps"
  | "ci";

// All valid change types for validation and UI
export const CHANGE_TYPES: ChangeType[] = [
  "feature",
  "bugfix",
  "refactor",
  "docs",
  "config",
  "test",
  "style",
  "perf",
  "deps",
  "ci",
];

// Change type display configuration
export const CHANGE_TYPE_CONFIG: Record<ChangeType, { label: string; color: string; icon: string }> = {
  feature: { label: "Feature", color: "text-emerald-400", icon: "sparkles" },
  bugfix: { label: "Bug Fix", color: "text-rose-400", icon: "bug" },
  refactor: { label: "Refactor", color: "text-amber-400", icon: "wrench" },
  docs: { label: "Docs", color: "text-sky-400", icon: "file-text" },
  config: { label: "Config", color: "text-violet-400", icon: "settings" },
  test: { label: "Test", color: "text-cyan-400", icon: "beaker" },
  style: { label: "Style", color: "text-pink-400", icon: "palette" },
  perf: { label: "Perf", color: "text-orange-400", icon: "zap" },
  deps: { label: "Deps", color: "text-lime-400", icon: "package" },
  ci: { label: "CI/CD", color: "text-indigo-400", icon: "git-branch" },
};

// Base Change interface (matches database schema)
export interface Change {
  id: string;
  project_id: string | null;
  task_id: string | null;
  session_id: string | null;
  change_type: ChangeType;
  summary: string;
  details: Record<string, unknown>;
  files_affected: string[];
  commit_sha: string | null;
  sub_category: string | null;
  created_at: string;
}

// Request types
export interface CreateChangeRequest {
  summary: string;
  change_type?: ChangeType; // Optional - auto-detected if not provided
  project_id?: string;
  task_id?: string; // Optional - links change to a task for changelog grouping
  session_id?: string;
  details?: Record<string, unknown>;
  files_affected?: string[];
  commit_sha?: string;
  sub_category?: string;
}

export interface UpdateChangeRequest {
  change_type?: ChangeType;
  summary?: string;
  project_id?: string;
  task_id?: string; // Optional - links change to a task for changelog grouping
  details?: Record<string, unknown>;
  files_affected?: string[];
  commit_sha?: string;
  sub_category?: string;
}

// Category suggestion types
export interface SuggestCategoryRequest {
  file_paths?: string[];
  commit_message?: string;
  tool_context?: Record<string, unknown>;
}

export interface CategorySuggestion {
  category: ChangeType;
  sub_category: string | null;
  confidence: number;
  reasoning: string;
  signals: Array<{
    signal_type: string;
    pattern: string;
    confidence: number;
    category: string;
  }>;
}

// API response types
export interface ChangesListResponse {
  changes: Change[];
  total_count: number;
  page: number;
  per_page: number;
  total_pages: number;
  filters_applied: string;
}

// Task-grouped changelog structure
export interface TaskGroupedChange {
  task: {
    id: string;
    title: string;
    status?: string;
    feature?: string;
  };
  changes: Change[];
  files_affected: string[];
  change_count: number;
}

export interface GroupedChangelog {
  tasks: TaskGroupedChange[];
  unlinked: Change[];
}

export interface ChangelogResponse {
  project_id: string;
  format: "markdown" | "json";
  group_by: "date" | "task";
  changelog?: string; // Present for markdown format
  changes?: Change[]; // Present for json format with date grouping
  grouped?: GroupedChangelog; // Present for json format with task grouping
  count: number;
}

// Filter options for the timeline
export interface ChangeFilters {
  change_type?: ChangeType;
  change_types?: ChangeType[]; // Multi-select filter support
  project_id?: string;
  date_from?: string;
  date_to?: string;
  query?: string;
}

// Statistics types
export interface ChangeStats {
  by_type: Record<ChangeType, number>;
  by_week: Array<{ week: string; count: number }>;
  by_project: Array<{ project_id: string | null; count: number }>;
  total: number;
  trend: {
    current_week: number;
    previous_week: number;
    percent_change: number;
  };
  days: number;
}
