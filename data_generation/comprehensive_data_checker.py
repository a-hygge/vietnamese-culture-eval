"""
Comprehensive Data Checker for Vietnamese Culture Benchmark

Checks all data files for:
1. Missing/empty fields (id, source, category, context, question, answer)
2. Wrong source field values
3. Missing chatgpt_answer entries
4. Duplicate questions
5. ID sequence errors
6. Inconsistent category values
7. Mismatched IDs between benchmark and chatgpt_web_answers
"""

import json
import os
from collections import Counter, defaultdict

BASE_DIR = r"D:/dichdata/vietnamese-culture-eval-2"

def load_json(file_path):
    """Load JSON file safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  ⚠ File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON error in {file_path}: {e}")
        return None

def check_benchmark_file(file_path, expected_category, expected_source_prefix):
    """
    Check a benchmark JSON file for errors.

    Returns dict with:
    - total: number of items
    - errors: list of error descriptions
    - items: the loaded data
    """
    print(f"\n{'='*60}")
    print(f"Checking: {os.path.basename(file_path)}")
    print(f"{'='*60}")

    data = load_json(file_path)
    if data is None:
        return {"total": 0, "errors": ["File not found or invalid JSON"], "items": []}

    errors = []
    warnings = []

    required_fields = ["id", "source", "category", "context", "question", "answer"]

    # Track for duplicates
    seen_ids = set()
    seen_questions = {}  # question -> id

    # Track ID sequence
    id_prefix = "VH_" if expected_category == "culture" else "PL_"
    id_numbers = []

    for idx, item in enumerate(data):
        item_id = item.get("id", f"MISSING_ID_{idx}")

        # 1. Check required fields
        for field in required_fields:
            if field not in item:
                errors.append(f"{item_id}: Missing field '{field}'")
            elif not item[field] or (isinstance(item[field], str) and not item[field].strip()):
                errors.append(f"{item_id}: Empty field '{field}'")

        # 2. Check source field
        source = item.get("source", "")
        if source:
            # Check if source is correct format
            if not source.startswith(expected_source_prefix) and source not in [
                "Bản sắc văn hóa Việt Nam",
                "Pháp luật đại cương"
            ]:
                warnings.append(f"{item_id}: Unusual source format: '{source[:50]}...'")

        # 3. Check category
        category = item.get("category", "")
        if category != expected_category:
            errors.append(f"{item_id}: Wrong category '{category}', expected '{expected_category}'")

        # 4. Check for duplicate IDs
        if item_id in seen_ids:
            errors.append(f"{item_id}: Duplicate ID")
        seen_ids.add(item_id)

        # 5. Check for duplicate questions
        question = item.get("question", "").strip()
        if question:
            if question in seen_questions:
                warnings.append(f"{item_id}: Duplicate question (same as {seen_questions[question]})")
            seen_questions[question] = item_id

        # 6. Check ID format and sequence
        if item_id.startswith(id_prefix):
            try:
                num = int(item_id.split("_")[1])
                id_numbers.append(num)
            except (ValueError, IndexError):
                errors.append(f"{item_id}: Invalid ID format")
        else:
            errors.append(f"{item_id}: ID doesn't match expected prefix '{id_prefix}'")

    # Check ID sequence continuity
    if id_numbers:
        id_numbers_sorted = sorted(id_numbers)
        expected_seq = list(range(1, max(id_numbers_sorted) + 1))
        missing_ids = set(expected_seq) - set(id_numbers_sorted)
        if missing_ids and len(missing_ids) < 20:
            warnings.append(f"Missing IDs in sequence: {sorted(missing_ids)[:10]}...")
        duplicate_nums = [n for n, count in Counter(id_numbers).items() if count > 1]
        if duplicate_nums:
            errors.append(f"Duplicate ID numbers: {duplicate_nums[:10]}")

    # Print summary
    print(f"\n  Total items: {len(data)}")
    print(f"  ✗ Errors: {len(errors)}")
    print(f"  ⚠ Warnings: {len(warnings)}")

    if errors:
        print("\n  ERRORS:")
        for e in errors[:20]:
            print(f"    - {e}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more errors")

    if warnings:
        print("\n  WARNINGS:")
        for w in warnings[:10]:
            print(f"    - {w}")
        if len(warnings) > 10:
            print(f"    ... and {len(warnings) - 10} more warnings")

    return {"total": len(data), "errors": errors, "warnings": warnings, "items": data}


def check_chatgpt_answers(answers_file, benchmark_data, source_name):
    """
    Check ChatGPT web answers file.

    Returns:
    - missing_answers: IDs in benchmark but not in answers
    - extra_answers: IDs in answers but not in benchmark
    - empty_answers: IDs with empty/null answers
    - wrong_format: IDs with wrong answer format
    """
    print(f"\n{'='*60}")
    print(f"Checking: {os.path.basename(answers_file)}")
    print(f"{'='*60}")

    answers = load_json(answers_file)
    if answers is None:
        return {
            "missing_answers": [],
            "extra_answers": [],
            "empty_answers": [],
            "wrong_format": []
        }

    # Get all IDs from benchmark
    benchmark_ids = {item.get("id") for item in benchmark_data if item.get("id")}

    # Get all IDs from answers
    answer_ids = set(answers.keys())

    # Find discrepancies
    missing_answers = benchmark_ids - answer_ids
    extra_answers = answer_ids - benchmark_ids

    # Check for empty or malformed answers
    empty_answers = []
    wrong_format = []

    for item_id, answer_data in answers.items():
        if isinstance(answer_data, dict):
            gpt_answer = answer_data.get("gpt_web_answer", "")
            if not gpt_answer or gpt_answer == "[NO RESPONSE]":
                empty_answers.append(item_id)
            # Check if question/context match
            if "question" in answer_data and "context" in answer_data:
                # Verify match with benchmark
                for bm_item in benchmark_data:
                    if bm_item.get("id") == item_id:
                        if bm_item.get("question") != answer_data.get("question"):
                            wrong_format.append(f"{item_id}: Question mismatch")
                        break
        elif isinstance(answer_data, str):
            if not answer_data or answer_data == "[NO RESPONSE]":
                empty_answers.append(item_id)
        else:
            wrong_format.append(f"{item_id}: Unexpected format type {type(answer_data)}")

    # Print summary
    print(f"\n  Total answers: {len(answers)}")
    print(f"  Benchmark IDs ({source_name}): {len(benchmark_ids)}")
    print(f"  ✗ Missing answers: {len(missing_answers)}")
    print(f"  ⚠ Extra answers (not in benchmark): {len(extra_answers)}")
    print(f"  ⚠ Empty/null answers: {len(empty_answers)}")
    print(f"  ⚠ Wrong format: {len(wrong_format)}")

    if missing_answers:
        print(f"\n  Missing answer IDs (first 20):")
        for mid in sorted(missing_answers)[:20]:
            print(f"    - {mid}")

    if empty_answers:
        print(f"\n  Empty answer IDs (first 20):")
        for eid in sorted(empty_answers)[:20]:
            print(f"    - {eid}")

    return {
        "missing_answers": sorted(missing_answers),
        "extra_answers": sorted(extra_answers),
        "empty_answers": sorted(empty_answers),
        "wrong_format": wrong_format
    }


def check_answer_content_mismatch(answers_file, benchmark_data):
    """
    Check if the question/context in answers file matches the benchmark.
    This catches cases where answers were collected for wrong questions.
    """
    print(f"\n{'='*60}")
    print(f"Checking answer-question matching: {os.path.basename(answers_file)}")
    print(f"{'='*60}")

    answers = load_json(answers_file)
    if answers is None:
        return []

    # Create lookup from benchmark
    benchmark_lookup = {item.get("id"): item for item in benchmark_data}

    mismatches = []

    for item_id, answer_data in answers.items():
        if not isinstance(answer_data, dict):
            continue

        if item_id not in benchmark_lookup:
            continue

        bm_item = benchmark_lookup[item_id]

        # Check question match
        ans_question = answer_data.get("question", "").strip()
        bm_question = bm_item.get("question", "").strip()

        if ans_question and bm_question:
            if ans_question != bm_question:
                mismatches.append({
                    "id": item_id,
                    "type": "question_mismatch",
                    "answer_question": ans_question[:100],
                    "benchmark_question": bm_question[:100]
                })

        # Check context match
        ans_context = answer_data.get("context", "").strip()
        bm_context = bm_item.get("context", "").strip()

        if ans_context and bm_context:
            if ans_context != bm_context:
                mismatches.append({
                    "id": item_id,
                    "type": "context_mismatch",
                    "answer_context": ans_context[:100],
                    "benchmark_context": bm_context[:100]
                })

    print(f"\n  Total mismatches: {len(mismatches)}")

    if mismatches:
        print("\n  Mismatches (first 10):")
        for m in mismatches[:10]:
            print(f"    - {m['id']} ({m['type']})")
            if m['type'] == 'question_mismatch':
                print(f"      Answer Q: {m['answer_question'][:50]}...")
                print(f"      Benchmark Q: {m['benchmark_question'][:50]}...")

    return mismatches


def check_cross_file_consistency(culture_data, law_data, culture_answers, law_answers):
    """
    Check consistency across all files.
    """
    print(f"\n{'='*60}")
    print("Cross-file Consistency Check")
    print(f"{'='*60}")

    issues = []

    # Check for IDs that appear in both culture and law
    culture_ids = {item.get("id") for item in culture_data}
    law_ids = {item.get("id") for item in law_data}

    overlapping_ids = culture_ids & law_ids
    if overlapping_ids:
        issues.append(f"IDs appear in both culture and law: {list(overlapping_ids)[:10]}")

    # Check for culture IDs in law answers file and vice versa
    if culture_answers and law_answers:
        culture_in_law = set(culture_answers.keys()) & law_ids
        law_in_culture = set(law_answers.keys()) & culture_ids

        if culture_in_law:
            issues.append(f"Culture answer IDs found for law questions: {list(culture_in_law)[:10]}")
        if law_in_culture:
            issues.append(f"Law answer IDs found for culture questions: {list(law_in_culture)[:10]}")

    # Print summary
    if issues:
        print("\n  Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("\n  ✓ No cross-file consistency issues found")

    return issues


def generate_fix_report(all_results):
    """
    Generate a summary report of all issues and suggested fixes.
    """
    print(f"\n{'='*60}")
    print("FIX REPORT SUMMARY")
    print(f"{'='*60}")

    total_errors = 0
    total_warnings = 0

    fixes_needed = []

    # Benchmark errors
    for source, result in [("Culture", all_results.get("culture_benchmark")),
                           ("Law", all_results.get("law_benchmark"))]:
        if result:
            total_errors += len(result.get("errors", []))
            total_warnings += len(result.get("warnings", []))

            for error in result.get("errors", []):
                fixes_needed.append(f"[{source}] {error}")

    # Answer file issues
    for source, result in [("Culture Answers", all_results.get("culture_answers")),
                           ("Law Answers", all_results.get("law_answers"))]:
        if result:
            if result.get("missing_answers"):
                fixes_needed.append(f"[{source}] {len(result['missing_answers'])} missing answers")
            if result.get("empty_answers"):
                fixes_needed.append(f"[{source}] {len(result['empty_answers'])} empty answers")

    print(f"\n  Total errors: {total_errors}")
    print(f"  Total warnings: {total_warnings}")
    print(f"  Fixes needed: {len(fixes_needed)}")

    if fixes_needed:
        print("\n  Actions required:")
        for idx, fix in enumerate(fixes_needed[:30], 1):
            print(f"    {idx}. {fix}")
        if len(fixes_needed) > 30:
            print(f"    ... and {len(fixes_needed) - 30} more")

    return fixes_needed


def main():
    """Run comprehensive data check."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE DATA CHECK FOR VIETNAMESE CULTURE BENCHMARK")
    print("=" * 70)

    all_results = {}

    # 1. Check Culture Benchmark
    culture_benchmark_path = os.path.join(
        BASE_DIR,
        "data_question_answer/ban_sac_van_hoa_viet_nam/culture_benchmark.json"
    )
    culture_result = check_benchmark_file(
        culture_benchmark_path,
        expected_category="culture",
        expected_source_prefix="data_sources\\ban_sac_van_hoa_viet_nam"
    )
    all_results["culture_benchmark"] = culture_result

    # 2. Check Law Benchmark
    law_benchmark_path = os.path.join(
        BASE_DIR,
        "data_question_answer/bai_giang_phap_luat_dai_cuong/law_benchmark.json"
    )
    law_result = check_benchmark_file(
        law_benchmark_path,
        expected_category="law",
        expected_source_prefix="data_sources\\bai_giang_phap_luat_dai_cuong"
    )
    all_results["law_benchmark"] = law_result

    # 3. Check ChatGPT Web Answers (Culture)
    culture_answers_path = os.path.join(BASE_DIR, "chatgpt_web_answers.json")
    culture_answers_result = check_chatgpt_answers(
        culture_answers_path,
        culture_result["items"],
        "Culture"
    )
    all_results["culture_answers"] = culture_answers_result

    # 4. Check ChatGPT Web Answers (Law)
    law_answers_path = os.path.join(BASE_DIR, "chatgpt_web_answers_law.json")
    law_answers_result = check_chatgpt_answers(
        law_answers_path,
        law_result["items"],
        "Law"
    )
    all_results["law_answers"] = law_answers_result

    # 5. Check answer-question matching
    print("\n--- Checking Content Matching ---")
    culture_mismatches = check_answer_content_mismatch(
        culture_answers_path,
        culture_result["items"]
    )
    all_results["culture_mismatches"] = culture_mismatches

    law_mismatches = check_answer_content_mismatch(
        law_answers_path,
        law_result["items"]
    )
    all_results["law_mismatches"] = law_mismatches

    # 6. Cross-file consistency
    culture_answers = load_json(culture_answers_path) or {}
    law_answers = load_json(law_answers_path) or {}

    cross_issues = check_cross_file_consistency(
        culture_result["items"],
        law_result["items"],
        culture_answers,
        law_answers
    )
    all_results["cross_issues"] = cross_issues

    # 7. Generate fix report
    fixes = generate_fix_report(all_results)

    # Save detailed report to JSON
    report_path = os.path.join(BASE_DIR, "data_check_report.json")

    # Convert sets to lists for JSON serialization
    serializable_results = {
        "culture_benchmark": {
            "total": culture_result["total"],
            "errors": culture_result["errors"],
            "warnings": culture_result.get("warnings", [])
        },
        "law_benchmark": {
            "total": law_result["total"],
            "errors": law_result["errors"],
            "warnings": law_result.get("warnings", [])
        },
        "culture_answers": culture_answers_result,
        "law_answers": law_answers_result,
        "culture_mismatches": culture_mismatches,
        "law_mismatches": law_mismatches,
        "cross_issues": cross_issues,
        "fixes_needed": fixes
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    print(f"\n\n✓ Detailed report saved to: {report_path}")

    return all_results


if __name__ == "__main__":
    main()
