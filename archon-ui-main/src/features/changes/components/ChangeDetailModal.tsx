/**
 * ChangeDetailModal Component
 *
 * Modal dialog showing full details of a change entry with inline editing.
 */

import {
  Bug,
  Calendar,
  Check,
  ChevronDown,
  ChevronRight,
  Edit2,
  ExternalLink,
  FileCode,
  FileText,
  FolderOpen,
  GitBranch,
  GitCommit,
  Loader2,
  Package,
  Palette,
  Settings,
  Sparkles,
  TestTube,
  Wand2,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { Button, Card } from "../../ui/primitives";
import * as Dialog from "@radix-ui/react-dialog";
import { cn } from "../../ui/primitives/styles";
import type { Change, ChangeType } from "../types";
import { CHANGE_TYPES, CHANGE_TYPE_CONFIG } from "../types";
import { changeService } from "../services";

export interface ChangeDetailModalProps {
  change: Change | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  githubRepo?: string; // Optional GitHub repo URL for commit links
  onUpdate?: (updatedChange: Change) => void; // Callback when change is updated
}

// Icon mapping for change types
const CHANGE_TYPE_ICONS: Record<ChangeType, React.ReactNode> = {
  feature: <Sparkles className="w-5 h-5" />,
  bugfix: <Bug className="w-5 h-5" />,
  refactor: <Wrench className="w-5 h-5" />,
  docs: <FileText className="w-5 h-5" />,
  config: <Settings className="w-5 h-5" />,
  test: <TestTube className="w-5 h-5" />,
  style: <Palette className="w-5 h-5" />,
  perf: <Zap className="w-5 h-5" />,
  deps: <Package className="w-5 h-5" />,
  ci: <GitBranch className="w-5 h-5" />,
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
  onUpdate,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [editedType, setEditedType] = useState<ChangeType | null>(null);
  const [editedSubCategory, setEditedSubCategory] = useState<string>("");
  const [suggestionConfidence, setSuggestionConfidence] = useState<number | null>(null);
  const [suggestionReasoning, setSuggestionReasoning] = useState<string | null>(null);

  // Reset edit state when change changes or modal closes
  const resetEditState = useCallback(() => {
    setIsEditing(false);
    setEditedType(null);
    setEditedSubCategory("");
    setSuggestionConfidence(null);
    setSuggestionReasoning(null);
  }, []);

  // Initialize edit state when entering edit mode
  const handleStartEdit = useCallback(() => {
    if (change) {
      setEditedType(change.change_type);
      setEditedSubCategory(change.sub_category || "");
      setIsEditing(true);
    }
  }, [change]);

  // Save changes
  const handleSave = useCallback(async () => {
    if (!change || !editedType) return;

    setIsSaving(true);
    try {
      const updatedChange = await changeService.updateChange(change.id, {
        change_type: editedType,
        sub_category: editedSubCategory.trim() || undefined,
      });
      onUpdate?.(updatedChange);
      resetEditState();
    } catch (error) {
      console.error("Failed to update change:", error);
    } finally {
      setIsSaving(false);
    }
  }, [change, editedType, editedSubCategory, onUpdate, resetEditState]);

  // Cancel editing
  const handleCancel = useCallback(() => {
    resetEditState();
  }, [resetEditState]);

  // Suggest category based on files and summary
  const handleSuggest = useCallback(async () => {
    if (!change) return;

    setIsSuggesting(true);
    setSuggestionConfidence(null);
    setSuggestionReasoning(null);

    try {
      const suggestion = await changeService.suggestCategory({
        file_paths: change.files_affected || [],
        commit_message: change.summary,
      });

      setEditedType(suggestion.category as ChangeType);
      if (suggestion.sub_category) {
        setEditedSubCategory(suggestion.sub_category);
      }
      setSuggestionConfidence(suggestion.confidence);
      setSuggestionReasoning(suggestion.reasoning);
    } catch (error) {
      console.error("Failed to get category suggestion:", error);
    } finally {
      setIsSuggesting(false);
    }
  }, [change]);

  if (!change) return null;

  const currentType = isEditing && editedType ? editedType : change.change_type;
  const typeConfig = CHANGE_TYPE_CONFIG[currentType];
  const icon = CHANGE_TYPE_ICONS[currentType];
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
                  "relative flex items-center justify-center w-12 h-12 rounded-xl backdrop-blur-md",
                  "border border-current/20",
                  typeConfig.color,
                )}
              >
                <div className="absolute inset-0 rounded-xl bg-current opacity-15" />
                <span className={cn("relative z-10", typeConfig.color)}>{icon}</span>
              </div>

              {/* Title and type badge */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  {isEditing ? (
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        {/* Category selector dropdown */}
                        <select
                          value={editedType || ""}
                          onChange={(e) => {
                            setEditedType(e.target.value as ChangeType);
                            setSuggestionConfidence(null);
                            setSuggestionReasoning(null);
                          }}
                          className={cn(
                            "px-2.5 py-1 rounded-lg text-xs font-medium uppercase tracking-wide",
                            "bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600",
                            "text-gray-900 dark:text-white",
                            "focus:outline-none focus:ring-2 focus:ring-cyan-500",
                          )}
                        >
                          {CHANGE_TYPES.map((type) => (
                            <option key={type} value={type}>
                              {CHANGE_TYPE_CONFIG[type].label}
                            </option>
                          ))}
                        </select>
                        {/* Sub-category input */}
                        <input
                          type="text"
                          value={editedSubCategory}
                          onChange={(e) => setEditedSubCategory(e.target.value)}
                          placeholder="Sub-category (optional)"
                          className={cn(
                            "px-2.5 py-1 rounded-lg text-xs",
                            "bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600",
                            "text-gray-900 dark:text-white placeholder-gray-500",
                            "focus:outline-none focus:ring-2 focus:ring-cyan-500",
                            "w-32",
                          )}
                        />
                        {/* Suggest button */}
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={handleSuggest}
                          disabled={isSuggesting}
                          className="gap-1 text-violet-500 hover:text-violet-600 hover:bg-violet-500/10"
                          title="Auto-detect category"
                        >
                          {isSuggesting ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Wand2 className="w-3.5 h-3.5" />
                          )}
                          Suggest
                        </Button>
                      </div>
                      {/* Confidence indicator */}
                      {suggestionConfidence !== null && (
                        <div className="flex items-center gap-2 text-xs">
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">Confidence:</span>
                            <span
                              className={cn(
                                "font-medium",
                                suggestionConfidence >= 0.8
                                  ? "text-emerald-500"
                                  : suggestionConfidence >= 0.5
                                    ? "text-amber-500"
                                    : "text-rose-500",
                              )}
                            >
                              {Math.round(suggestionConfidence * 100)}%
                            </span>
                          </div>
                          {suggestionReasoning && (
                            <span className="text-gray-400 truncate max-w-[200px]" title={suggestionReasoning}>
                              {suggestionReasoning}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <>
                      <span
                        className={cn(
                          "relative px-2.5 py-1 rounded-full text-xs font-medium uppercase tracking-wide",
                          "backdrop-blur-md border border-current/20",
                          typeConfig.color,
                        )}
                      >
                        <span className="absolute inset-0 rounded-full bg-current opacity-15" />
                        <span className={cn("relative z-10", typeConfig.color)}>{typeConfig.label}</span>
                      </span>
                      {change.sub_category && (
                        <span className="px-2 py-0.5 rounded-md text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                          {change.sub_category}
                        </span>
                      )}
                    </>
                  )}
                </div>
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                  {change.summary}
                </Dialog.Title>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-1 shrink-0">
                {isEditing ? (
                  <>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleCancel}
                      disabled={isSaving}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleSave}
                      disabled={isSaving}
                      className="text-cyan-500 hover:text-cyan-600"
                    >
                      {isSaving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleStartEdit}
                    className="text-gray-500 hover:text-cyan-500"
                    title="Edit category"
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                )}
                <Dialog.Close asChild>
                  <Button variant="ghost" size="icon" className="shrink-0">
                    <X className="w-5 h-5" />
                  </Button>
                </Dialog.Close>
              </div>
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
