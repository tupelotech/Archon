#!/usr/bin/env python3
"""
One-time migration script to fix "Untitled" documents in the knowledge base.

This script:
1. Updates titles in archon_crawled_pages by extracting H1/H2 headers from content
2. Syncs chunk_count in archon_page_metadata based on actual chunk counts

Run with: uv run python scripts/fix_untitled_documents.py
"""

import asyncio
import json
import os
import sys
from urllib.parse import urlparse

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if env vars are already set

from supabase import create_client


def extract_title_from_content(content: str, url: str) -> str:
    """Extract title from markdown content or URL."""
    if not content:
        return extract_title_from_url(url)

    lines = content.split('\n')[:15]
    for line in lines:
        line = line.strip()
        # Match H1 headers
        if line.startswith('# ') and not line.startswith('##'):
            return line[2:].strip()
        # Match H2 headers as fallback
        elif line.startswith('## '):
            return line[3:].strip()

    # Fallback to URL-based title
    return extract_title_from_url(url)


def extract_title_from_url(url: str) -> str:
    """Extract a meaningful title from URL path."""
    if not url:
        return "Untitled"

    parsed = urlparse(url)
    if parsed.path and parsed.path != '/':
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        if path_parts:
            return path_parts[-1].replace('-', ' ').replace('_', ' ').title()

    return parsed.netloc.replace('www.', '').title() if parsed.netloc else "Untitled"


async def fix_untitled_documents():
    """Fix all documents with 'Untitled' title."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    print("Fetching documents with 'Untitled' title...")

    # Get all chunks where metadata contains "Untitled" title
    result = supabase.from_("archon_crawled_pages").select(
        "id, url, content, metadata"
    ).execute()

    if not result.data:
        print("No documents found")
        return

    untitled_count = 0
    updated_count = 0
    errors = []

    for chunk in result.data:
        metadata = chunk.get("metadata", {}) or {}
        current_title = metadata.get("title", "")

        if current_title == "Untitled" or not current_title:
            untitled_count += 1
            content = chunk.get("content", "")
            url = chunk.get("url", "")

            new_title = extract_title_from_content(content, url)

            if new_title and new_title != "Untitled":
                # Update metadata with new title
                metadata["title"] = new_title

                try:
                    supabase.from_("archon_crawled_pages").update({
                        "metadata": metadata
                    }).eq("id", chunk["id"]).execute()
                    updated_count += 1
                    print(f"  Updated: {url[:60]}... -> '{new_title[:50]}'")
                except Exception as e:
                    errors.append(f"Failed to update {chunk['id']}: {e}")

    print(f"\nResults:")
    print(f"  Total untitled documents: {untitled_count}")
    print(f"  Successfully updated: {updated_count}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for error in errors[:5]:
            print(f"    - {error}")


async def sync_chunk_counts():
    """Sync chunk_count in archon_page_metadata with actual chunk counts."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        return

    supabase = create_client(supabase_url, supabase_key)

    print("\nSyncing chunk counts in page_metadata...")

    # Get all page metadata records
    pages_result = supabase.from_("archon_page_metadata").select(
        "id, source_id, url, chunk_count"
    ).execute()

    if not pages_result.data:
        print("No page metadata found")
        return

    updated_count = 0

    for page in pages_result.data:
        page_id = page["id"]

        # Count actual chunks for this page
        chunk_count_result = supabase.from_("archon_crawled_pages").select(
            "id", count="exact", head=True
        ).eq("page_id", page_id).execute()

        actual_count = chunk_count_result.count if hasattr(chunk_count_result, "count") else 0

        if actual_count != page.get("chunk_count", 0):
            try:
                supabase.from_("archon_page_metadata").update({
                    "chunk_count": actual_count
                }).eq("id", page_id).execute()
                updated_count += 1
                print(f"  Updated chunk_count for {page['url'][:50]}...: {page.get('chunk_count', 0)} -> {actual_count}")
            except Exception as e:
                print(f"  Error updating {page_id}: {e}")

    print(f"\nChunk count sync results:")
    print(f"  Pages checked: {len(pages_result.data)}")
    print(f"  Pages updated: {updated_count}")


async def main():
    print("=" * 60)
    print("Knowledge Base Document Fix Migration")
    print("=" * 60)

    await fix_untitled_documents()
    await sync_chunk_counts()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
