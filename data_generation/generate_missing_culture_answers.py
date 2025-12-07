"""
Generate Missing Culture Answers (VH_1875 to VH_3295)

This script generates the 1421 missing answers for culture questions
using Azure OpenAI API.

Progress is saved after each answer, so you can stop and resume.
"""

import os
import json
import time
import openai
from datetime import datetime

# Azure OpenAI Configuration
client = openai.AzureOpenAI(
    api_key="a6705b22532443ee8c0cfda232e57e06",
    azure_endpoint="https://vietgpt.openai.azure.com/",
    api_version="2024-02-15-preview"
)

BASE_DIR = r"D:/dichdata/vietnamese-culture-eval-2"


def get_gpt_answer(context: str, question: str, retries=3) -> str:
    """
    Get GPT's answer for a question.
    """
    for attempt in range(retries):
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
        except openai.RateLimitError:
            print(f"    Rate limit hit, waiting 60s...")
            time.sleep(60)
        except Exception as e:
            print(f"    Error (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return f"[API ERROR: {str(e)}]"

    return "[API ERROR: Max retries exceeded]"


def main():
    print("=" * 60)
    print("GENERATE MISSING CULTURE ANSWERS")
    print("=" * 60)

    # Load files
    answers_file = os.path.join(BASE_DIR, "chatgpt_web_answers.json")
    benchmark_file = os.path.join(BASE_DIR, "data_question_answer/ban_sac_van_hoa_viet_nam/culture_benchmark.json")

    print("\nLoading files...")

    with open(answers_file, 'r', encoding='utf-8') as f:
        answers = json.load(f)
    print(f"  Loaded {len(answers)} existing answers")

    with open(benchmark_file, 'r', encoding='utf-8') as f:
        benchmark = json.load(f)
    print(f"  Loaded {len(benchmark)} benchmark items")

    # Find missing IDs
    existing_ids = set(answers.keys())
    all_ids = {item.get("id") for item in benchmark}
    missing_ids = sorted(all_ids - existing_ids, key=lambda x: int(x.split("_")[1]))

    print(f"\n  Missing answers: {len(missing_ids)}")
    if not missing_ids:
        print("  No missing answers to generate!")
        return

    print(f"  Range: {missing_ids[0]} to {missing_ids[-1]}")

    # Create lookup
    benchmark_lookup = {item.get("id"): item for item in benchmark}

    # Generate answers
    print(f"\nGenerating answers...")
    generated = 0
    errors = 0

    for idx, item_id in enumerate(missing_ids, 1):
        bm_item = benchmark_lookup.get(item_id)
        if not bm_item:
            print(f"  {item_id}: Not found in benchmark")
            continue

        question = bm_item.get("question", "")
        context = bm_item.get("context", "")

        if not question:
            print(f"  {item_id}: No question")
            continue

        print(f"  [{idx}/{len(missing_ids)}] {item_id}...", end=" ", flush=True)

        # Get answer
        answer = get_gpt_answer(context, question)

        if answer.startswith("[API ERROR"):
            print(f"ERROR: {answer}")
            errors += 1
        else:
            print(f"OK ({len(answer)} chars)")
            generated += 1

        # Save answer
        answers[item_id] = {
            "question": question,
            "context": context,
            "gpt_web_answer": answer,
            "timestamp": datetime.now().isoformat()
        }

        # Save progress after each answer
        with open(answers_file, 'w', encoding='utf-8') as f:
            json.dump(answers, f, ensure_ascii=False, indent=2)

        # Small delay to avoid rate limits
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"COMPLETE: Generated {generated}, Errors {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
