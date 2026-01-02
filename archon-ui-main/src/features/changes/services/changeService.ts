/**
 * Change Tracking Service
 * Service for change CRUD operations and changelog generation
 */

import { callAPIWithETag } from "../../shared/api/apiClient";
import type {
  Change,
  ChangeFilters,
  ChangelogResponse,
  ChangesListResponse,
  CreateChangeRequest,
} from "../types";

export const changeService = {
  /**
   * Get all changes with optional filters
   */
  async getChanges(filters?: ChangeFilters, page = 1, perPage = 20): Promise<ChangesListResponse> {
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));

      if (filters?.change_type) params.set("change_type", filters.change_type);
      if (filters?.project_id) params.set("project_id", filters.project_id);
      if (filters?.date_from) params.set("date_from", filters.date_from);
      if (filters?.date_to) params.set("date_to", filters.date_to);
      if (filters?.query) params.set("q", filters.query);

      const response = await callAPIWithETag<ChangesListResponse>(`/api/changes?${params.toString()}`);
      return response;
    } catch (error) {
      console.error("Failed to get changes:", error);
      throw error;
    }
  },

  /**
   * Get changes for a specific project
   */
  async getChangesByProject(projectId: string, page = 1, perPage = 20): Promise<ChangesListResponse> {
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(perPage));

      const response = await callAPIWithETag<ChangesListResponse>(
        `/api/projects/${projectId}/changes?${params.toString()}`
      );
      return response;
    } catch (error) {
      console.error(`Failed to get changes for project ${projectId}:`, error);
      throw error;
    }
  },

  /**
   * Get a specific change by ID
   */
  async getChange(changeId: string): Promise<Change> {
    try {
      const change = await callAPIWithETag<Change>(`/api/changes/${changeId}`);
      return change;
    } catch (error) {
      console.error(`Failed to get change ${changeId}:`, error);
      throw error;
    }
  },

  /**
   * Create a new change entry
   */
  async createChange(changeData: CreateChangeRequest): Promise<Change> {
    try {
      const response = await callAPIWithETag<{ message: string; change: Change }>("/api/changes", {
        method: "POST",
        body: JSON.stringify(changeData),
      });
      return response.change;
    } catch (error) {
      console.error("Failed to create change:", error);
      throw error;
    }
  },

  /**
   * Delete a change entry
   */
  async deleteChange(changeId: string): Promise<void> {
    try {
      await callAPIWithETag<void>(`/api/changes/${changeId}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error(`Failed to delete change ${changeId}:`, error);
      throw error;
    }
  },

  /**
   * Get changelog for a project in markdown or JSON format
   */
  async getProjectChangelog(projectId: string, format: "markdown" | "json" = "markdown"): Promise<ChangelogResponse> {
    try {
      const response = await callAPIWithETag<ChangelogResponse>(
        `/api/projects/${projectId}/changelog?format=${format}`
      );
      return response;
    } catch (error) {
      console.error(`Failed to get changelog for project ${projectId}:`, error);
      throw error;
    }
  },
};
