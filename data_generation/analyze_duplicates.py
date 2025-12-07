"""
Analyze Duplicate Questions in Benchmark Files

This script:
1. Finds all duplicate questions
2. Shows the context, question, and answer for each duplicate pair
3. Recommends whether to keep or remove duplicates
"""

import os
import json
from collections import defaultdict

BASE_DIR = r"D:/dichdata/vietnamese-culture-eval-2"


def analyze_duplicates(benchmark_file: str, name: str):
    """Analyze duplicates in a benchmark file."""
    print(f"\n{'='*70}")
    print(f"DUPLICATE ANALYSIS: {name}")
    print(f"{'='*70}")

    with open(benchmark_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find duplicates by question text
    question_to_items = defaultdict(list)
    for item in data:
        question = item.get("question", "").strip()
        if question:
            question_to_items[question].append(item)

    # Filter to only duplicates
    duplicates = {q: items for q, items in question_to_items.items() if len(items) > 1}

    print(f"\nTotal items: {len(data)}")
    print(f"Unique questions: {len(question_to_items)}")
    print(f"Duplicate groups: {len(duplicates)}")
    print(f"Total duplicate items: {sum(len(items) for items in duplicates.values())}")

    # Show each duplicate group
    for i, (question, items) in enumerate(duplicates.items(), 1):
        print(f"\n{'-'*60}")
        print(f"DUPLICATE GROUP {i}")
        print(f"{'-'*60}")
        print(f"Question: {question[:100]}...")
        print(f"Count: {len(items)} occurrences")
        print()

        for j, item in enumerate(items, 1):
            item_id = item.get("id", "?")
            source = item.get("source", "?")
            context = item.get("context", "")[:80]
            answer = item.get("answer", "")[:100]

            print(f"  [{j}] ID: {item_id}")
            print(f"      Source: {source[:60]}...")
            print(f"      Context: {context}...")
            print(f"      Answer: {answer}...")
            print()

        # Check if answers are the same
        answers = [item.get("answer", "") for item in items]
        if len(set(answers)) == 1:
            print("  => SAME ANSWERS: Can safely remove duplicates (keep first)")
        else:
            print("  => DIFFERENT ANSWERS: Need manual review")

    return duplicates


def main():
    print("=" * 70)
    print("ANALYZING DUPLICATE QUESTIONS IN BENCHMARK FILES")
    print("=" * 70)

    # Culture benchmark
    culture_file = os.path.join(
        BASE_DIR, "data_question_answer/ban_sac_van_hoa_viet_nam/culture_benchmark.json"
    )
    culture_dups = analyze_duplicates(culture_file, "CULTURE")

    # Law benchmark
    law_file = os.path.join(
        BASE_DIR, "data_question_answer/bai_giang_phap_luat_dai_cuong/law_benchmark.json"
    )
    law_dups = analyze_duplicates(law_file, "LAW")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Culture: {len(culture_dups)} duplicate groups")
    print(f"Law: {len(law_dups)} duplicate groups")


if __name__ == "__main__":
    main()
