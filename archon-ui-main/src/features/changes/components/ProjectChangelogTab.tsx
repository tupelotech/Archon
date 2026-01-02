/**
 * ProjectChangelogTab Component
 *
 * Tab content for viewing and exporting a project's changelog.
 */

import { Download, FileText, Loader2 } from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Card } from "../../ui/primitives";
import { useProjectChangelog, useProjectChanges, changeKeys } from "../hooks";
import type { Change } from "../types";
import { CategoryStatsWidget } from "./CategoryStatsWidget";
import { ChangeCard } from "./ChangeCard";
import { ChangeDetailModal } from "./ChangeDetailModal";

export interface ProjectChangelogTabProps {
  projectId: string;
  githubRepo?: string;
  onTaskClick?: (taskId: string) => void;
}

export const ProjectChangelogTab: React.FC<ProjectChangelogTabProps> = ({ projectId, githubRepo, onTaskClick }) => {
  const queryClient = useQueryClient();
  const [selectedChange, setSelectedChange] = useState<Change | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch changes for timeline
  const { data: changesData, isLoading, error } = useProjectChanges(projectId);

  // Fetch changelog for export
  const { data: changelogData, isLoading: isLoadingChangelog } = useProjectChangelog(projectId, "markdown");

  const changes = changesData?.changes || [];

  const handleChangeClick = useCallback((change: Change) => {
    setSelectedChange(change);
    setIsModalOpen(true);
  }, []);

  const handleChangeUpdate = useCallback(
    (updatedChange: Change) => {
      // Update selected change in local state
      setSelectedChange(updatedChange);
      // Invalidate changes queries to refetch
      queryClient.invalidateQueries({ queryKey: changeKeys.byProject(projectId) });
      queryClient.invalidateQueries({ queryKey: changeKeys.changelog(projectId, "markdown") });
    },
    [queryClient, projectId],
  );

  const handleExport = useCallback(() => {
    if (!changelogData?.changelog) return;

    // Create blob and download
    const blob = new Blob([changelogData.changelog], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `changelog-${projectId.slice(0, 8)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [changelogData, projectId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-500" />
      </div>
    );
  }

  if (error) {
    return (
      <Card blur="md" transparency="light" className="p-6 text-center">
        <p className="text-red-400">Failed to load changelog</p>
        <p className="text-sm text-gray-500 mt-1">{error.message}</p>
      </Card>
    );
  }

  if (changes.length === 0) {
    return (
      <Card blur="md" transparency="light" className="p-12 text-center">
        <div className="text-gray-400 dark:text-gray-500 mb-4">
          <FileText className="w-12 h-12 mx-auto opacity-50" />
        </div>
        <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No Changes Yet</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
          Changes made during development will appear here. Use the MCP tools or API to log changes as you work.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with export button */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {changes.length} {changes.length === 1 ? "change" : "changes"} recorded
          </h3>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={isLoadingChangelog || !changelogData?.changelog}
          className="gap-2"
        >
          {isLoadingChangelog ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Export Markdown
        </Button>
      </div>

      {/* Category statistics */}
      <CategoryStatsWidget changes={changes} />

      {/* Changes list */}
      <div className="space-y-3">
        {changes.map((change) => (
          <ChangeCard key={change.id} change={change} onClick={handleChangeClick} onTaskClick={onTaskClick} />
        ))}
      </div>

      {/* Detail modal */}
      <ChangeDetailModal
        change={selectedChange}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        githubRepo={githubRepo}
        onUpdate={handleChangeUpdate}
      />
    </div>
  );
};
