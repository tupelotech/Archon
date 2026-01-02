/**
 * Change Tracking Query Hooks
 * TanStack Query hooks for change management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DISABLED_QUERY_KEY, STALE_TIMES } from "../../shared/config/queryPatterns";
import { useSmartPolling } from "../../shared/hooks";
import { useToast } from "../../shared/hooks/useToast";
import { changeService } from "../services/changeService";
import type { Change, ChangeFilters, ChangesListResponse, CreateChangeRequest } from "../types";

// Query keys factory for changes
export const changeKeys = {
  all: ["changes"] as const,
  lists: () => [...changeKeys.all, "list"] as const,
  list: (filters?: ChangeFilters, page?: number) => [...changeKeys.lists(), { filters, page }] as const,
  detail: (id: string) => [...changeKeys.all, "detail", id] as const,
  byProject: (projectId: string) => ["projects", projectId, "changes"] as const,
  changelog: (projectId: string, format: string) => ["projects", projectId, "changelog", format] as const,
};

/**
 * Fetch changes with optional filters and pagination
 */
export function useChanges(filters?: ChangeFilters, page = 1, perPage = 20, enabled = true) {
  const { refetchInterval } = useSmartPolling(30_000); // 30s polling for changes

  return useQuery<ChangesListResponse>({
    queryKey: changeKeys.list(filters, page),
    queryFn: () => changeService.getChanges(filters, page, perPage),
    enabled,
    refetchInterval,
    staleTime: STALE_TIMES.normal,
  });
}

/**
 * Fetch changes for a specific project
 */
export function useProjectChanges(projectId: string | undefined, page = 1, perPage = 20, enabled = true) {
  const { refetchInterval } = useSmartPolling(30_000);

  return useQuery<ChangesListResponse>({
    queryKey: projectId ? changeKeys.byProject(projectId) : DISABLED_QUERY_KEY,
    queryFn: () => {
      if (!projectId) throw new Error("No project ID");
      return changeService.getChangesByProject(projectId, page, perPage);
    },
    enabled: !!projectId && enabled,
    refetchInterval,
    staleTime: STALE_TIMES.normal,
  });
}

/**
 * Fetch a single change by ID
 */
export function useChange(changeId: string | undefined, enabled = true) {
  return useQuery<Change>({
    queryKey: changeId ? changeKeys.detail(changeId) : DISABLED_QUERY_KEY,
    queryFn: () => {
      if (!changeId) throw new Error("No change ID");
      return changeService.getChange(changeId);
    },
    enabled: !!changeId && enabled,
    staleTime: STALE_TIMES.normal,
  });
}

/**
 * Fetch project changelog
 */
export function useProjectChangelog(
  projectId: string | undefined,
  format: "markdown" | "json" = "markdown",
  enabled = true
) {
  return useQuery({
    queryKey: projectId ? changeKeys.changelog(projectId, format) : DISABLED_QUERY_KEY,
    queryFn: () => {
      if (!projectId) throw new Error("No project ID");
      return changeService.getProjectChangelog(projectId, format);
    },
    enabled: !!projectId && enabled,
    staleTime: STALE_TIMES.normal,
  });
}

/**
 * Create a new change entry
 */
export function useCreateChange() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation<Change, Error, CreateChangeRequest>({
    mutationFn: (changeData: CreateChangeRequest) => changeService.createChange(changeData),
    onSuccess: (data) => {
      // Invalidate all change lists
      queryClient.invalidateQueries({ queryKey: changeKeys.lists() });

      // If change is associated with a project, invalidate that project's changes
      if (data.project_id) {
        queryClient.invalidateQueries({ queryKey: changeKeys.byProject(data.project_id) });
        queryClient.invalidateQueries({ queryKey: changeKeys.changelog(data.project_id, "markdown") });
        queryClient.invalidateQueries({ queryKey: changeKeys.changelog(data.project_id, "json") });
      }

      showToast("Change logged successfully", "success");
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Failed to create change:", error);
      showToast(`Failed to log change: ${errorMessage}`, "error");
    },
  });
}

/**
 * Delete a change entry
 */
export function useDeleteChange() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation<void, Error, { changeId: string; projectId?: string | null }>({
    mutationFn: ({ changeId }) => changeService.deleteChange(changeId),
    onSuccess: (_data, variables) => {
      // Invalidate all change lists
      queryClient.invalidateQueries({ queryKey: changeKeys.lists() });

      // If change was associated with a project, invalidate that project's changes
      if (variables.projectId) {
        queryClient.invalidateQueries({ queryKey: changeKeys.byProject(variables.projectId) });
        queryClient.invalidateQueries({ queryKey: changeKeys.changelog(variables.projectId, "markdown") });
        queryClient.invalidateQueries({ queryKey: changeKeys.changelog(variables.projectId, "json") });
      }

      showToast("Change deleted", "success");
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Failed to delete change:", error);
      showToast(`Failed to delete change: ${errorMessage}`, "error");
    },
  });
}
