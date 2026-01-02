/**
 * ChangeDetailModal Component
 *
 * Modal dialog showing full details of a change entry.
 */

import {
  Bug,
  Calendar,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileCode,
  FileText,
  FolderOpen,
  GitCommit,
  Settings,
  Sparkles,
  TestTube,
  Wrench,
  X,
} from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Button, Card } from "../../ui/primitives";
import * as Dialog from "@radix-ui/react-dialog";
import { cn } from "../../ui/primitives/styles";
import type { Change, ChangeType } from "../types";
import { CHANGE_TYPE_CONFIG } from "../types";

export interface ChangeDetailModalProps {
  change: Change | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  githubRepo?: string; // Optional GitHub repo URL for commit links
}

// Icon mapping for change types
const CHANGE_TYPE_ICONS: Record<ChangeType, React.ReactNode> = {
  feature: <Sparkles className="w-5 h-5" />,
  bugfix: <Bug className="w-5 h-5" />,
  refactor: <Wrench className="w-5 h-5" />,
  docs: <FileText className="w-5 h-5" />,
  config: <Settings className="w-5 h-5" />,
  test: <TestTube className="w-5 h-5" />,
};

// Format date for display
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const ChangeDetailModal: React.FC<ChangeDetailModalProps> = ({
  change,
  open,
  onOpenChange,
  githubRepo,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);

  if (!change) return null;

  const typeConfig = CHANGE_TYPE_CONFIG[change.change_type];
  const icon = CHANGE_TYPE_ICONS[change.change_type];
  const hasDetails = change.details && Object.keys(change.details).length > 0;
  const filesAffected = change.files_affected || [];
  const hasFiles = filesAffected.length > 0;
  const displayFiles = showAllFiles ? filesAffected : filesAffected.slice(0, 10);

  const commitUrl = githubRepo && change.commit_sha ? `${githubRepo}/commit/${change.commit_sha}` : null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl max-h-[85vh] overflow-hidden">
          <Card
            blur="xl"
            transparency="frosted"
            className="flex flex-col max-h-[85vh] border border-gray-200/50 dark:border-gray-700/50"
          >
            {/* Header */}
            <div className="flex items-start gap-4 p-6 border-b border-gray-200/50 dark:border-gray-700/50">
              {/* Type icon */}
              <div
                className={cn(
                  "flex items-center justify-center w-12 h-12 rounded-xl backdrop-blur-md",
                  "border border-current/20",
                  typeConfig.color,
                )}
                style={{
                  backgroundColor: "currentColor",
                  opacity: 0.15,
                }}
              >
                <span className={typeConfig.color}>{icon}</span>
              </div>

              {/* Title and type badge */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={cn(
                      "px-2.5 py-1 rounded-full text-xs font-medium uppercase tracking-wide",
                      "backdrop-blur-md border border-current/20",
                      typeConfig.color,
                    )}
                  >
                    {typeConfig.label}
                  </span>
                </div>
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                  {change.summary}
                </Dialog.Title>
              </div>

              {/* Close button */}
              <Dialog.Close asChild>
                <Button variant="ghost" size="icon" className="shrink-0">
                  <X className="w-5 h-5" />
                </Button>
              </Dialog.Close>
            </div>

            {/* Content - scrollable */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Metadata row */}
              <div className="flex flex-wrap gap-4 text-sm">
                {/* Date */}
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  {formatDate(change.created_at)}
                </div>

                {/* Commit SHA */}
                {change.commit_sha && (
                  <div className="flex items-center gap-2">
                    <GitCommit className="w-4 h-4 text-gray-500" />
                    {commitUrl ? (
                      <a
                        href={commitUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        {change.commit_sha.slice(0, 7)}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <code className="font-mono text-gray-600 dark:text-gray-400">
                        {change.commit_sha.slice(0, 7)}
                      </code>
                    )}
                  </div>
                )}
              </div>

              {/* Files affected */}
              {hasFiles && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowAllFiles(!showAllFiles)}
                    className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
                  >
                    <FolderOpen className="w-4 h-4" />
                    Files Affected ({filesAffected.length})
                    {filesAffected.length > 10 && (
                      showAllFiles ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
                    )}
                  </button>

                  <div className="space-y-1 pl-6">
                    {displayFiles.map((file) => (
                      <div
                        key={file}
                        className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 font-mono"
                      >
                        <FileCode className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{file}</span>
                      </div>
                    ))}
                    {!showAllFiles && filesAffected.length > 10 && (
                      <button
                        type="button"
                        onClick={() => setShowAllFiles(true)}
                        className="text-sm text-cyan-600 dark:text-cyan-400 hover:underline"
                      >
                        Show {filesAffected.length - 10} more files...
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Details JSON */}
              {hasDetails && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowDetails(!showDetails)}
                    className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
                  >
                    {showDetails ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    Additional Details
                  </button>

                  {showDetails && (
                    <Card blur="sm" transparency="medium" className="p-4">
                      <pre className="text-xs text-gray-600 dark:text-gray-400 font-mono overflow-x-auto">
                        {JSON.stringify(change.details, null, 2)}
                      </pre>
                    </Card>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 p-6 border-t border-gray-200/50 dark:border-gray-700/50">
              <Dialog.Close asChild>
                <Button variant="outline">Close</Button>
              </Dialog.Close>
            </div>
          </Card>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
