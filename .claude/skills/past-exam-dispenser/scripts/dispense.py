#!/usr/bin/env python3
"""past-exam-dispenser: Read-only access layer to AP past exam questions.

Loads all past exam JSON files and provides search by section tag, exam ID,
or keyword. Designed to be invoked by other skills (e.g. SFT skill) that
need past exam questions as seed data for question generation.

Stateless and idempotent. Does not track learner progress.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------- Data loading ----------

def load_all_exams():
    """Load all exam files and return a flat list of questions with exam metadata."""
    questions = []
    for exam_file in sorted(DATA_DIR.glob("*.json")):
        with open(exam_file, encoding="utf-8") as f:
            data = json.load(f)
        exam_id = data.get("exam_id", exam_file.stem)
        exam_name = data.get("exam_name", "")
        for q in data.get("questions", []):
            q_copy = dict(q)
            q_copy["exam_id"] = exam_id
            q_copy["exam_name"] = exam_name
            questions.append(q_copy)
    return questions


# ---------- Result formatting ----------

def _question_summary(q):
    """Compact summary for listing."""
    return {
        "exam_id": q["exam_id"],
        "exam_name": q.get("exam_name", ""),
        "number": q["number"],
        "body": q["body"][:120] + ("..." if len(q["body"]) > 120 else ""),
        "answer": q["answer"],
        "tags": q.get("tags", []),
        "has_figure": q.get("has_figure", False),
    }


def _question_full(q):
    """Full question data."""
    return {
        "exam_id": q["exam_id"],
        "exam_name": q.get("exam_name", ""),
        "number": q["number"],
        "body": q["body"],
        "choices": q.get("choices", {}),
        "answer": q["answer"],
        "tags": q.get("tags", []),
        "has_figure": q.get("has_figure", False),
        "figure_description": q.get("figure_description"),
    }


# ---------- Commands ----------

def cmd_by_section(section_id, full=False):
    """Return all questions tagged with a given section ID."""
    questions = load_all_exams()
    matches = [q for q in questions if section_id in q.get("tags", [])]

    if not matches:
        return {
            "status": "not_found",
            "mode": "by-section",
            "query": section_id,
            "hint": f"セクション '{section_id}' にタグ付けされた問題が見つかりません。タグは ch01_01 のようなセクションレベルです。",
        }

    fmt = _question_full if full else _question_summary
    return {
        "status": "ok",
        "mode": "by-section",
        "section": section_id,
        "count": len(matches),
        "questions": [fmt(q) for q in matches],
    }


def cmd_by_exam(exam_id, full=False):
    """Return all questions from a specific exam."""
    questions = load_all_exams()
    matches = [q for q in questions if q["exam_id"] == exam_id]

    if not matches:
        return {
            "status": "not_found",
            "mode": "by-exam",
            "query": exam_id,
            "hint": "exam_id が見つかりません。例: 2025r07h, 2024r06a",
        }

    fmt = _question_full if full else _question_summary
    return {
        "status": "ok",
        "mode": "by-exam",
        "exam_id": exam_id,
        "exam_name": matches[0].get("exam_name", ""),
        "count": len(matches),
        "questions": [fmt(q) for q in matches],
    }


def cmd_search(keyword, full=False, max_results=30):
    """Full-text search in question bodies."""
    questions = load_all_exams()
    keyword_lower = keyword.lower()
    matches = [q for q in questions if keyword_lower in q["body"].lower()]

    if not matches:
        return {
            "status": "not_found",
            "mode": "search",
            "query": keyword,
        }

    total = len(matches)
    capped = matches[:max_results]
    fmt = _question_full if full else _question_summary
    result = {
        "status": "ok",
        "mode": "search",
        "query": keyword,
        "count": total,
        "returned": len(capped),
        "questions": [fmt(q) for q in capped],
    }
    if total > max_results:
        result["hint"] = f"全 {total} 件中 {max_results} 件を返しています。より具体的なキーワードで絞り込んでください。"
    return result


def cmd_stats():
    """Summary statistics across all exams."""
    questions = load_all_exams()

    tag_counts = Counter()
    exam_counts = Counter()
    figure_count = 0
    for q in questions:
        for t in q.get("tags", []):
            tag_counts[t] += 1
        exam_counts[q["exam_id"]] += 1
        if q.get("has_figure"):
            figure_count += 1

    return {
        "status": "ok",
        "mode": "stats",
        "total_questions": len(questions),
        "total_exams": len(exam_counts),
        "total_section_tags": len(tag_counts),
        "questions_with_figures": figure_count,
        "per_section": {
            tag: cnt for tag, cnt in sorted(tag_counts.items())
        },
        "per_exam": {
            eid: cnt for eid, cnt in sorted(exam_counts.items())
        },
    }


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="past-exam-dispenser: read-only access to AP past exam questions",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    p_section = sub.add_parser("by-section", help="Get questions by section tag")
    p_section.add_argument("section_id", help="Section tag (e.g. ch04_03)")
    p_section.add_argument("--full", action="store_true", help="Return full question data including choices")

    p_exam = sub.add_parser("by-exam", help="Get questions from a specific exam")
    p_exam.add_argument("exam_id", help="Exam ID (e.g. 2025r07h)")
    p_exam.add_argument("--full", action="store_true", help="Return full question data including choices")

    p_search = sub.add_parser("search", help="Full-text search in question bodies")
    p_search.add_argument("keyword", help="Search keyword")
    p_search.add_argument("--full", action="store_true", help="Return full question data including choices")

    p_stats = sub.add_parser("stats", help="Summary statistics")

    args = parser.parse_args()

    if args.mode == "by-section":
        result = cmd_by_section(args.section_id, full=args.full)
    elif args.mode == "by-exam":
        result = cmd_by_exam(args.exam_id, full=args.full)
    elif args.mode == "search":
        result = cmd_search(args.keyword, full=args.full)
    elif args.mode == "stats":
        result = cmd_stats()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
