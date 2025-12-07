"""
Fix Missing/Empty/Error Answers in ChatGPT Web Answers Files

This script:
1. Identifies all empty/error answers in chatgpt_web_answers.json and chatgpt_web_answers_law.json
2. Re-generates answers using Azure OpenAI API
3. Updates the answer files

Issues found:
- Culture answers (chatgpt_web_answers.json):
  - Empty answers: VH_003, VH_006, VH_016, VH_149
  - Error answers: VH_014, VH_148 (truncated), VH_723, VH_727, VH_1460
  - Missing: VH_1875 to VH_3295 (1421 items) - too many to fix via API

- Law answers (chatgpt_web_answers_law.json):
  - Error answers: PL_294
"""

import os
import json
import openai
from datetime import datetime

# Azure OpenAI Configuration
client = openai.AzureOpenAI(
    api_key="a6705b22532443ee8c0cfda232e57e06",
    azure_endpoint="https://vietgpt.openai.azure.com/",
    api_version="2024-02-15-preview"
)

BASE_DIR = r"D:/dichdata/vietnamese-culture-eval-2"


def get_gpt_answer(context: str, question: str) -> str:
    """
    Get GPT's answer for a question (without the source passage).
    This simulates how GPT would answer in web interface.
    """
    try:
        user_message = f"{context}\n\n{question}" if context else question

        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là trợ lý AI có kiến thức về văn hóa và pháp luật Việt Nam. Trả lời ngắn gọn, chính xác, đi thẳng vào vấn đề. Không cần giải thích dài dòng."
                },
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[API ERROR: {str(e)}]"


def find_problematic_answers(answers_file: str) -> dict:
    """
    Find all empty, error, or truncated answers.

    Returns dict with:
    - empty: list of IDs with empty answers
    - error: list of IDs with error messages
    - truncated: list of IDs with truncated answers
    """
    if not os.path.exists(answers_file):
        print(f"File not found: {answers_file}")
        return {"empty": [], "error": [], "truncated": []}

    with open(answers_file, 'r', encoding='utf-8') as f:
        answers = json.load(f)

    empty = []
    error = []
    truncated = []

    for item_id, data in answers.items():
        if isinstance(data, dict):
            gpt_answer = data.get("gpt_web_answer", "")
        else:
            gpt_answer = str(data) if data else ""

        if not gpt_answer:
            empty.append(item_id)
        elif "Something went wrong" in gpt_answer:
            error.append(item_id)
        elif len(gpt_answer) < 30 and not gpt_answer.endswith(('.', '。', '!', '?')):
            # Likely truncated answer
            truncated.append(item_id)

    return {"empty": empty, "error": error, "truncated": truncated}


def fix_answers(answers_file: str, benchmark_file: str, ids_to_fix: list):
    """
    Fix specific answer IDs by regenerating with API.
    """
    # Load answers
    with open(answers_file, 'r', encoding='utf-8') as f:
        answers = json.load(f)

    # Load benchmark to get questions
    with open(benchmark_file, 'r', encoding='utf-8') as f:
        benchmark = json.load(f)

    # Create lookup
    benchmark_lookup = {item.get("id"): item for item in benchmark}

    fixed_count = 0

    for item_id in ids_to_fix:
        if item_id not in benchmark_lookup:
            print(f"  Warning: {item_id} not found in benchmark")
            continue

        bm_item = benchmark_lookup[item_id]
        question = bm_item.get("question", "")
        context = bm_item.get("context", "")

        if not question:
            print(f"  Warning: {item_id} has no question")
            continue

        print(f"  Fixing {item_id}...")

        # Get new answer
        new_answer = get_gpt_answer(context, question)

        if new_answer.startswith("[API ERROR"):
            print(f"    Error: {new_answer}")
            continue

        # Update answer
        if item_id in answers:
            if isinstance(answers[item_id], dict):
                answers[item_id]["gpt_web_answer"] = new_answer
                answers[item_id]["timestamp"] = datetime.now().isoformat()
                answers[item_id]["fixed"] = True
            else:
                answers[item_id] = {
                    "question": question,
                    "context": context,
                    "gpt_web_answer": new_answer,
                    "timestamp": datetime.now().isoformat(),
                    "fixed": True
                }
        else:
            # Add new answer
            answers[item_id] = {
                "question": question,
                "context": context,
                "gpt_web_answer": new_answer,
                "timestamp": datetime.now().isoformat(),
                "fixed": True
            }

        print(f"    OK: {new_answer[:60]}...")
        fixed_count += 1

    # Save updated answers
    with open(answers_file, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    print(f"\n  Fixed {fixed_count}/{len(ids_to_fix)} answers")
    return fixed_count


def main():
    print("=" * 60)
    print("FIX MISSING/ERROR ANSWERS")
    print("=" * 60)

    # Culture answers
    culture_answers_file = os.path.join(BASE_DIR, "chatgpt_web_answers.json")
    culture_benchmark_file = os.path.join(BASE_DIR, "data_question_answer/ban_sac_van_hoa_viet_nam/culture_benchmark.json")

    print("\n1. Checking culture answers...")
    culture_issues = find_problematic_answers(culture_answers_file)
    print(f"   Empty: {len(culture_issues['empty'])} - {culture_issues['empty']}")
    print(f"   Error: {len(culture_issues['error'])} - {culture_issues['error']}")
    print(f"   Truncated: {len(culture_issues['truncated'])} - {culture_issues['truncated']}")

    # Fix culture answers
    culture_to_fix = culture_issues['empty'] + culture_issues['error'] + culture_issues['truncated']
    if culture_to_fix:
        print(f"\n   Fixing {len(culture_to_fix)} culture answers...")
        fix_answers(culture_answers_file, culture_benchmark_file, culture_to_fix)

    # Law answers
    law_answers_file = os.path.join(BASE_DIR, "chatgpt_web_answers_law.json")
    law_benchmark_file = os.path.join(BASE_DIR, "data_question_answer/bai_giang_phap_luat_dai_cuong/law_benchmark.json")

    print("\n2. Checking law answers...")
    law_issues = find_problematic_answers(law_answers_file)
    print(f"   Empty: {len(law_issues['empty'])} - {law_issues['empty']}")
    print(f"   Error: {len(law_issues['error'])} - {law_issues['error']}")
    print(f"   Truncated: {len(law_issues['truncated'])} - {law_issues['truncated']}")

    # Fix law answers
    law_to_fix = law_issues['empty'] + law_issues['error'] + law_issues['truncated']
    if law_to_fix:
        print(f"\n   Fixing {len(law_to_fix)} law answers...")
        fix_answers(law_answers_file, law_benchmark_file, law_to_fix)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
