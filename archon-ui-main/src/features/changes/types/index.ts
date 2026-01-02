/**
 * Change Tracking Types
 *
 * Types for tracking development changes made during AI-assisted sessions.
 */

// Change type enum - matches database
export type ChangeType = "feature" | "bugfix" | "refactor" | "docs" | "config" | "test";

// All valid change types for validation and UI
export const CHANGE_TYPES: ChangeType[] = ["feature", "bugfix", "refactor", "docs", "config", "test"];

// Change type display configuration
export const CHANGE_TYPE_CONFIG: Record<ChangeType, { label: string; color: string; icon: string }> = {
  feature: { label: "Feature", color: "text-emerald-400", icon: "sparkles" },
  bugfix: { label: "Bug Fix", color: "text-rose-400", icon: "bug" },
  refactor: { label: "Refactor", color: "text-amber-400", icon: "wrench" },
  docs: { label: "Docs", color: "text-sky-400", icon: "file-text" },
  config: { label: "Config", color: "text-violet-400", icon: "settings" },
  test: { label: "Test", color: "text-cyan-400", icon: "beaker" },
};

// Base Change interface (matches database schema)
export interface Change {
  id: string;
  project_id: string | null;
  session_id: string | null;
  change_type: ChangeType;
  summary: string;
  details: Record<string, unknown>;
  files_affected: string[];
  commit_sha: string | null;
  created_at: string;
}

// Request types
export interface CreateChangeRequest {
  change_type: ChangeType;
  summary: string;
  project_id?: string;
  session_id?: string;
  details?: Record<string, unknown>;
  files_affected?: string[];
  commit_sha?: string;
}

export interface UpdateChangeRequest {
  change_type?: ChangeType;
  summary?: string;
  details?: Record<string, unknown>;
  files_affected?: string[];
  commit_sha?: string;
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

export interface ChangelogResponse {
  project_id: string;
  format: "markdown" | "json";
  changelog: string;
  changes: Change[];
  count: number;
}

// Filter options for the timeline
export interface ChangeFilters {
  change_type?: ChangeType;
  project_id?: string;
  date_from?: string;
  date_to?: string;
  query?: string;
}
