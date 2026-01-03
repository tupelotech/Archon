/**
 * Inspector Pagination Hook
 * Handles pagination for the Knowledge Inspector with "Load More" functionality
 */

import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { STALE_TIMES } from "@/features/shared/config/queryPatterns";
import { knowledgeKeys } from "../../hooks/useKnowledgeQueries";
import { knowledgeService } from "../../services";
import type { ChunksResponse, CodeExample, CodeExamplesResponse, DocumentChunk } from "../../types";

export interface UseInspectorPaginationProps {
  sourceId: string;
  viewMode: "documents" | "code";
  searchQuery: string;
}

export interface UseInspectorPaginationResult {
  items: (DocumentChunk | CodeExample)[];
  isLoading: boolean;
  hasNextPage: boolean;
  fetchNextPage: (options?: any) => Promise<any>;
  isFetchingNextPage: boolean;
  totalCount: number;
  loadedCount: number;
}

export function useInspectorPagination({
  sourceId,
  viewMode,
  searchQuery,
}: UseInspectorPaginationProps): UseInspectorPaginationResult {
  const PAGE_SIZE = 100;

  // Use infinite query for the current view mode
  // Include searchQuery in key for documents (server-side search)
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useInfiniteQuery<
    ChunksResponse | CodeExamplesResponse,
    Error
  >({
    queryKey: [
      ...knowledgeKeys.detail(sourceId),
      viewMode === "documents" ? "chunks-infinite" : "code-examples-infinite",
      viewMode === "documents" ? searchQuery : undefined, // Only include search in key for documents
    ],
    queryFn: ({ pageParam }: { pageParam: unknown }) => {
      const page = Number(pageParam) || 0;

      if (viewMode === "documents") {
        // Documents API supports server-side search
        return knowledgeService.getKnowledgeItemChunks(sourceId, {
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          search: searchQuery || undefined,
        });
      }
      // Code examples API doesn't support search - will filter client-side
      return knowledgeService.getCodeExamples(sourceId, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      });
    },
    getNextPageParam: (lastPage, allPages) => {
      const hasMore = (lastPage as ChunksResponse | CodeExamplesResponse)?.has_more;
      return hasMore ? allPages.length : undefined;
    },
    enabled: !!sourceId,
    staleTime: STALE_TIMES.normal,
    initialPageParam: 0,
  });

  // Flatten the paginated data and apply client-side search filtering (for code examples only)
  const { items, totalCount, loadedCount } = useMemo(() => {
    type Page = ChunksResponse | CodeExamplesResponse;
    if (!data || !data.pages) {
      return { items: [], totalCount: 0, loadedCount: 0 };
    }

    // Flatten all pages - data has 'pages' property from useInfiniteQuery
    const pages = data.pages as Page[];
    const allItems = pages.flatMap((page): (DocumentChunk | CodeExample)[] =>
      "chunks" in page ? (page.chunks ?? []) : "code_examples" in page ? (page.code_examples ?? []) : [],
    );

    // Get total from first page (fallback to loadedCount)
    const first = pages[0];
    const totalCount = first && "total" in first && typeof first.total === "number" ? first.total : allItems.length;
    const loadedCount = allItems.length;

    // Documents use server-side search (passed to API), so no client-side filtering needed
    if (viewMode === "documents" || !searchQuery) {
      return { items: allItems, totalCount, loadedCount };
    }

    // Code examples API doesn't support search, so apply client-side filtering
    const query = searchQuery.toLowerCase();
    const filteredItems = allItems.filter((item: DocumentChunk | CodeExample) => {
      const code = item as CodeExample;
      return (
        code.content?.toLowerCase().includes(query) ||
        code.summary?.toLowerCase().includes(query) ||
        code.language?.toLowerCase().includes(query) ||
        code.file_path?.toLowerCase().includes(query) ||
        code.title?.toLowerCase().includes(query)
      );
    });

    return { items: filteredItems, totalCount, loadedCount };
  }, [data, viewMode, searchQuery]);

  return {
    items,
    isLoading,
    hasNextPage: !!hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    totalCount,
    loadedCount,
  };
}
