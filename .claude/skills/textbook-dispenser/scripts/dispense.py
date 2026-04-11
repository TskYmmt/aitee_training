#!/usr/bin/env python3
"""textbook-dispenser: Read-only access layer to textbook_structure.json.

Resolves fuzzy queries about the AP exam textbook table of contents into
strict (leaf_id, title) pairs, and provides neighbor lookups for sequential
study flows. Designed to be invoked from other skills (e.g. pre-training).

The dispenser is stateless and idempotent. It does not track progress or
learner state — that responsibility belongs elsewhere.
"""

import argparse
import json
import sys
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "textbook_structure.json"
MAX_AMBIGUOUS = 10


# ---------- Data loading and indexing ----------

def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_flat_index(data):
    """Build a linear list of all leaves (subsections) with parent info.

    Columns are included as leaves with is_column=True. The linear_index
    field gives a stable position used by neighbors lookups.
    """
    flat = []
    for ch in data["chapters"]:
        for sec in ch.get("sections", []):
            for sub in sec.get("subsections", []):
                flat.append({
                    "id": sub["id"],
                    "title": sub["title"],
                    "is_column": bool(sub.get("column", False)),
                    "chapter": {"id": ch["id"], "title": ch["title"]},
                    "section": {"id": sec["id"], "title": sec["title"]},
                    "linear_index": len(flat),
                })
    return flat


def build_section_index(data):
    """Build a list of all sections."""
    sections = []
    for ch in data["chapters"]:
        for sec in ch.get("sections", []):
            sections.append({
                "id": sec["id"],
                "title": sec["title"],
                "chapter": {"id": ch["id"], "title": ch["title"]},
            })
    return sections


def build_chapter_index(data):
    return [{"id": ch["id"], "title": ch["title"]} for ch in data["chapters"]]


def index_by_id(items):
    return {item["id"]: item for item in items}


# ---------- Query normalization ----------

def normalize_id(query):
    """Convert dashed forms ('4-3', '4-3-1') to canonical IDs.

    Returns a list of plausible canonical IDs to try.
    """
    candidates = [query]
    parts = query.split("-")
    if all(p.isdigit() for p in parts):
        if len(parts) == 1:
            candidates.append(f"ch{parts[0].zfill(2)}")
        elif len(parts) == 2:
            candidates.append(f"ch{parts[0].zfill(2)}_{parts[1].zfill(2)}")
        elif len(parts) == 3:
            candidates.append(f"ch{parts[0].zfill(2)}_{parts[1].zfill(2)}_{parts[2].zfill(2)}")
    return candidates


# ---------- Title-based search ----------

def search_titles(query, items, max_results=MAX_AMBIGUOUS):
    """Search items by title with priority: exact > prefix > substring.

    Returns (matches, total_count). matches is capped at max_results.
    """
    q_lower = query.lower()
    exact, prefix, substring = [], [], []
    for item in items:
        title_lower = item["title"].lower()
        if title_lower == q_lower:
            exact.append(item)
        elif title_lower.startswith(q_lower):
            prefix.append(item)
        elif q_lower in title_lower:
            substring.append(item)
    all_matches = exact + prefix + substring
    return all_matches[:max_results], len(all_matches)


# ---------- Result builders ----------

def attach_neighbors(leaf, flat):
    """Return a copy of leaf with prev/next leaf summaries attached."""
    idx = leaf["linear_index"]
    out = dict(leaf)
    out["prev"] = _summary(flat[idx - 1]) if idx > 0 else None
    out["next"] = _summary(flat[idx + 1]) if idx + 1 < len(flat) else None
    return out


def _summary(leaf):
    return {
        "id": leaf["id"],
        "title": leaf["title"],
        "is_column": leaf["is_column"],
        "chapter": leaf["chapter"]["id"],
        "section": leaf["section"]["id"],
    }


def _full_path(leaf):
    return f"{leaf['chapter']['title']} > {leaf['section']['title']} > {leaf['title']}"


def _candidate_leaf(leaf):
    return {
        "id": leaf["id"],
        "title": leaf["title"],
        "type": "leaf",
        "is_column": leaf["is_column"],
        "full_path": _full_path(leaf),
    }


def _candidate_section(sec):
    return {
        "id": sec["id"],
        "title": sec["title"],
        "type": "section",
        "full_path": f"{sec['chapter']['title']} > {sec['title']}",
    }


def _candidate_chapter(ch):
    return {
        "id": ch["id"],
        "title": ch["title"],
        "type": "chapter",
        "full_path": ch["title"],
    }


# ---------- Commands ----------

def cmd_resolve(query):
    """Resolve a fuzzy query to a leaf, candidate list, or not_found.

    Resolution order:
      1. Direct ID match (leaf, section, chapter; with normalization)
      2. Leaf title search
      3. Section title search
      4. Chapter title search
    """
    data = load_data()
    flat = build_flat_index(data)
    sections = build_section_index(data)
    chapters = build_chapter_index(data)

    leaf_by_id = index_by_id(flat)
    sec_by_id = index_by_id(sections)
    ch_by_id = index_by_id(chapters)

    # 1. Direct ID match (with normalization for "4-3-1" style)
    for q in normalize_id(query):
        if q in leaf_by_id:
            return {
                "status": "ok",
                "mode": "resolve",
                "query": query,
                "match_type": "leaf_id_exact",
                "result": attach_neighbors(leaf_by_id[q], flat),
            }
        if q in sec_by_id:
            section_leaves = [l for l in flat if l["section"]["id"] == q]
            return {
                "status": "ambiguous",
                "mode": "resolve",
                "query": query,
                "match_type": "section_id_expand",
                "section": sec_by_id[q],
                "candidates": [_candidate_leaf(l) for l in section_leaves],
            }
        if q in ch_by_id:
            ch_sections = [s for s in sections if s["chapter"]["id"] == q]
            return {
                "status": "ambiguous",
                "mode": "resolve",
                "query": query,
                "match_type": "chapter_id_expand",
                "chapter": ch_by_id[q],
                "candidates": [_candidate_section(s) for s in ch_sections],
            }

    # 2. Leaf title search
    leaf_matches, leaf_total = search_titles(query, flat)
    if leaf_total == 1:
        return {
            "status": "ok",
            "mode": "resolve",
            "query": query,
            "match_type": "leaf_title_unique",
            "result": attach_neighbors(leaf_matches[0], flat),
        }
    if leaf_total > MAX_AMBIGUOUS:
        return {
            "status": "too_many",
            "mode": "resolve",
            "query": query,
            "total_matches": leaf_total,
            "hint": f"マッチするleafが多すぎます({leaf_total}件)。より具体的な用語で検索してください",
            "preview": [_candidate_leaf(l) for l in leaf_matches[:5]],
        }
    if leaf_total > 1:
        return {
            "status": "ambiguous",
            "mode": "resolve",
            "query": query,
            "match_type": "leaf_title_multiple",
            "candidates": [_candidate_leaf(l) for l in leaf_matches],
        }

    # 3. Section title search
    sec_matches, sec_total = search_titles(query, sections)
    if sec_matches:
        return {
            "status": "ambiguous",
            "mode": "resolve",
            "query": query,
            "match_type": "section_title_match",
            "candidates": [_candidate_section(s) for s in sec_matches],
        }

    # 4. Chapter title search
    ch_matches, ch_total = search_titles(query, chapters)
    if ch_matches:
        return {
            "status": "ambiguous",
            "mode": "resolve",
            "query": query,
            "match_type": "chapter_title_match",
            "candidates": [_candidate_chapter(c) for c in ch_matches],
        }

    return {
        "status": "not_found",
        "mode": "resolve",
        "query": query,
        "hint": "該当するleaf/section/chapterが見つかりませんでした。leaf ID（例: ch04_03_01）、節番号（例: 4-3）、または章名・節名・leaf名の一部で再検索してください",
    }


def cmd_lookup(leaf_id):
    """Strict ID-only leaf lookup with neighbors attached."""
    data = load_data()
    flat = build_flat_index(data)
    leaf_by_id = index_by_id(flat)

    if leaf_id not in leaf_by_id:
        return {
            "status": "not_found",
            "mode": "lookup",
            "query": leaf_id,
            "hint": "leaf IDが存在しません。resolveモードで曖昧検索を試してください",
        }

    return {
        "status": "ok",
        "mode": "lookup",
        "result": attach_neighbors(leaf_by_id[leaf_id], flat),
    }


def cmd_neighbors(leaf_id):
    """Return prev/current/next leaf summaries for a given leaf ID."""
    data = load_data()
    flat = build_flat_index(data)
    leaf_by_id = index_by_id(flat)

    if leaf_id not in leaf_by_id:
        return {
            "status": "not_found",
            "mode": "neighbors",
            "query": leaf_id,
            "hint": "leaf IDが存在しません",
        }

    leaf = leaf_by_id[leaf_id]
    idx = leaf["linear_index"]

    return {
        "status": "ok",
        "mode": "neighbors",
        "of": leaf_id,
        "current": _summary(leaf),
        "prev": _summary(flat[idx - 1]) if idx > 0 else None,
        "next": _summary(flat[idx + 1]) if idx + 1 < len(flat) else None,
    }


# ---------- CLI entry ----------

def main():
    parser = argparse.ArgumentParser(
        description="textbook-dispenser: read-only access to AP textbook structure",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    p_resolve = sub.add_parser("resolve", help="Resolve a fuzzy query to leaf/section/chapter")
    p_resolve.add_argument("query", help="ID, dashed form, or title fragment")

    p_lookup = sub.add_parser("lookup", help="Strict ID lookup of a leaf")
    p_lookup.add_argument("leaf_id")

    p_neighbors = sub.add_parser("neighbors", help="Get prev/current/next leaf for a given leaf ID")
    p_neighbors.add_argument("leaf_id")

    args = parser.parse_args()

    if args.mode == "resolve":
        result = cmd_resolve(args.query)
    elif args.mode == "lookup":
        result = cmd_lookup(args.leaf_id)
    elif args.mode == "neighbors":
        result = cmd_neighbors(args.leaf_id)
    else:
        parser.error(f"unknown mode: {args.mode}")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
