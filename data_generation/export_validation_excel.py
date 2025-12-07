"""
Export Q&A Benchmark to Excel for Manual Validation

Creates an Excel file with columns for manual quality control:
- ID, Source, Category, Context, Question, Answer, GPT_Answer
- Validation columns for 4 criteria (1/0.5/0 scoring)
- Final score calculation

4 Validation Criteria:
1. text_based: Dựa hoàn toàn vào văn bản (Based entirely on text)
2. no_temporal: Không có thông tin thay đổi theo thời gian (No time-varying info)
3. relevant: Liên quan đến văn hóa hoặc pháp luật Việt Nam (Related to VN culture/law)
4. objective: Trung lập, khách quan, không ý kiến cá nhân (Neutral, objective)
"""

import os
import json
import openai
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

# Import data quality checker
from data_quality_checker import (
    analyze_benchmark, analyze_benchmark_with_status, analyze_item,
    generate_quality_report, get_quality_status, classify_issues
)

# Azure OpenAI Configuration
client = openai.AzureOpenAI(
    api_key="a6705b22532443ee8c0cfda232e57e06",
    azure_endpoint="https://vietgpt.openai.azure.com/",
    api_version="2024-02-15-preview"
)

# Danh sách các chủ đề có thể dự đoán
TOPIC_LIST = [
    "Pháp luật",
    "Văn hóa",
    "Lịch sử",
    "Kinh tế",
    "Chính trị",
    "Xã hội",
    "Giáo dục",
    "Tôn giáo",
    "Nghệ thuật",
    "Phong tục tập quán",
    "Địa lý",
    "Khác"
]


def predict_topic(question: str, context: str = "", answer: str = "") -> str:
    """
    Dự đoán chủ đề của câu hỏi bằng LLM.

    Args:
        question: Câu hỏi cần phân loại
        context: Ngữ cảnh (nếu có)
        answer: Đáp án (nếu có)

    Returns:
        Tên chủ đề dự đoán
    """
    try:
        topic_list_str = ", ".join(TOPIC_LIST)

        prompt = f"""Phân loại câu hỏi sau vào MỘT trong các chủ đề: {topic_list_str}

Câu hỏi: {question}
{f'Đáp án: {answer}' if answer else ''}

Chỉ trả lời tên chủ đề, không giải thích."""

        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là chuyên gia phân loại chủ đề. Chỉ trả lời tên chủ đề, không giải thích."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=20
        )

        topic = response.choices[0].message.content.strip()

        # Normalize topic - kiểm tra xem có trong danh sách không
        for t in TOPIC_LIST:
            if t.lower() in topic.lower():
                return t

        return "Khác"

    except Exception as e:
        print(f"  Error predicting topic: {e}")
        return "Khác"


def predict_topics_batch(data: list, progress_file: str = None) -> list:
    """
    Dự đoán chủ đề cho tất cả câu hỏi.
    Hỗ trợ resume từ progress file.

    Args:
        data: List of Q&A dictionaries
        progress_file: Path to save/load progress

    Returns:
        List of Q&A dictionaries with predicted_topic field
    """
    # Load existing progress
    processed = {}
    if progress_file and os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                processed = json.load(f)
            print(f"  Loaded {len(processed)} existing topic predictions")
        except:
            pass

    total = len(data)
    for idx, item in enumerate(data, 1):
        item_id = item.get("id", f"Q{idx}")

        # Skip if already processed
        if item_id in processed:
            item["predicted_topic"] = processed[item_id]
            continue

        if idx % 10 == 1:
            print(f"  [{idx}/{total}] Predicting topics...")

        question = item.get("question", "")
        context = item.get("context", "")
        answer = item.get("answer", "")

        topic = predict_topic(question, context, answer)
        item["predicted_topic"] = topic
        processed[item_id] = topic

        # Save progress every 10 items
        if progress_file and idx % 10 == 0:
            try:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
            except:
                pass

    # Final save
    if progress_file:
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
        except:
            pass

    return data


def load_benchmark_data(json_paths: list) -> list:
    """
    Load Q&A data from JSON files.

    Args:
        json_paths: List of paths to JSON files

    Returns:
        List of Q&A dictionaries
    """
    all_data = []

    for json_path in json_paths:
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                        print(f"  ✓ Loaded {len(data)} items from {os.path.basename(json_path)}")
            except Exception as e:
                print(f"  ✗ Error loading {json_path}: {str(e)}")
        else:
            print(f"  ⚠ File not found: {json_path}")

    return all_data


def load_benchmark_from_chunks(chunks_dir: str, source_type: str) -> list:
    """
    Load Q&A data from individual chunk JSON files.
    This preserves the chunk file information in the source field.

    Args:
        chunks_dir: Directory containing chunk JSON files
        source_type: "culture" or "law"

    Returns:
        List of Q&A dictionaries with proper source paths
    """
    all_data = []

    if not os.path.exists(chunks_dir):
        print(f"  ⚠ Chunks directory not found: {chunks_dir}")
        return all_data

    chunk_files = sorted([f for f in os.listdir(chunks_dir) if f.endswith('.json')])

    if not chunk_files:
        print(f"  ⚠ No chunk files found in {chunks_dir}")
        return all_data

    # Determine source path prefix based on type
    if source_type == "culture":
        source_prefix = "data_sources\\ban_sac_van_hoa_viet_nam\\structured_chunks_v2"
    else:
        source_prefix = "data_sources\\bai_giang_phap_luat_dai_cuong\\structured_chunks_v2"

    for chunk_file in chunk_files:
        file_path = os.path.join(chunks_dir, chunk_file)
        chunk_txt_name = chunk_file.replace('.json', '.txt')
        source_path = f"{source_prefix}\\{chunk_txt_name}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                questions = json.load(f)

            # Update source field for each question
            for q in questions:
                # Check if source is old format (just name) or already has path
                if q.get("source") and not q["source"].startswith("data_sources"):
                    q["source"] = source_path

            all_data.extend(questions)

        except Exception as e:
            print(f"  ✗ Error loading {chunk_file}: {str(e)}")

    print(f"  ✓ Loaded {len(all_data)} items from {len(chunk_files)} chunk files ({source_type})")
    return all_data


def get_gpt_answer(context: str, question: str) -> str:
    """
    Get GPT's answer for a question (without the source passage).
    This simulates how GPT would answer in web interface.

    Args:
        context: Context hint (e.g., "Sau đây là câu hỏi về văn hóa Việt Nam")
        question: The question to answer

    Returns:
        GPT's answer as string
    """
    try:
        # Combine context and question like in web interface
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
        return f"[ERROR: {str(e)}]"


def generate_gpt_answers(data: list, progress_file: str = None) -> list:
    """
    Generate GPT answers for all questions using API.
    Supports resuming from progress file.

    Args:
        data: List of Q&A dictionaries
        progress_file: Path to save/load progress

    Returns:
        List of Q&A dictionaries with gpt_answer field
    """
    # Load existing progress
    processed = {}
    if progress_file and os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                processed = json.load(f)
            print(f"  Loaded {len(processed)} existing GPT answers")
        except:
            pass

    total = len(data)
    for idx, item in enumerate(data, 1):
        item_id = item.get("id", f"Q{idx}")

        # Skip if already processed
        if item_id in processed:
            item["gpt_answer"] = processed[item_id]
            continue

        print(f"  [{idx}/{total}] Getting GPT answer for {item_id}...")

        context = item.get("context", "")
        question = item.get("question", "")

        gpt_answer = get_gpt_answer(context, question)
        item["gpt_answer"] = gpt_answer
        processed[item_id] = gpt_answer

        # Save progress after each answer
        if progress_file:
            try:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
            except:
                pass

    return data


# ============================================================================
# LLM JUDGE SCORING
# ============================================================================

JUDGE_SYSTEM_PROMPT = """
Bạn là giám khảo đánh giá câu trả lời của mô hình AI về văn hóa và pháp luật Việt Nam.

## NHIỆM VỤ:
So sánh câu trả lời của mô hình với đáp án chuẩn và cho điểm.

## THANG ĐIỂM (0.0 - 1.0):
- 1.0 (excellent): Câu trả lời đúng hoàn toàn, đầy đủ và chính xác như đáp án chuẩn
- 0.9 (very_good): Đúng hoàn toàn về ý chính, chỉ khác biệt nhỏ về cách diễn đạt
- 0.8 (good): Đúng các điểm quan trọng, thiếu 1 chi tiết nhỏ không ảnh hưởng đến ý nghĩa
- 0.7 (fairly_good): Đúng phần lớn, thiếu 1-2 chi tiết phụ
- 0.6 (acceptable): Đúng ý chính nhưng thiếu một số thông tin bổ sung quan trọng
- 0.5 (partial): Đúng khoảng một nửa nội dung, thiếu nhiều thông tin quan trọng
- 0.4 (weak): Có một số ý đúng nhưng thiếu phần lớn nội dung chính
- 0.3 (poor): Chỉ đúng một phần nhỏ, phần lớn không chính xác hoặc thiếu
- 0.2 (very_poor): Hầu như không đúng, chỉ có liên quan mơ hồ đến đáp án
- 0.1 (almost_wrong): Gần như hoàn toàn sai, chỉ đề cập đúng chủ đề
- 0.0 (incorrect): Hoàn toàn sai, không liên quan, hoặc trả lời lạc đề

## NGUYÊN TẮC ĐÁNH GIÁ:
1. Đánh giá dựa trên NỘI DUNG và Ý NGHĨA, không phải cách diễn đạt
2. Chấp nhận các cách diễn đạt khác nhau nếu ý nghĩa tương đương
3. Ưu tiên độ chính xác của thông tin cốt lõi
4. Xem xét tính đầy đủ của câu trả lời so với đáp án chuẩn
5. Trừ điểm nặng nếu có thông tin SAI (không chỉ thiếu)
6. Câu trả lời dài hơn không có nghĩa là tốt hơn nếu thêm thông tin sai

## ĐỊNH DẠNG TRẢ LỜI:
{
  "score": <điểm từ 0.0 đến 1.0, bước 0.1>,
  "verdict": "excellent" | "very_good" | "good" | "fairly_good" | "acceptable" | "partial" | "weak" | "poor" | "very_poor" | "almost_wrong" | "incorrect",
  "reason": "<giải thích ngắn gọn lý do cho điểm>"
}

Chỉ trả về JSON, không giải thích thêm.
"""

JUDGE_USER_TEMPLATE = """
## CÂU HỎI:
{question}

## ĐÁP ÁN CHUẨN:
{correct_answer}

## CÂU TRẢ LỜI CỦA MÔ HÌNH:
{model_answer}

Hãy đánh giá câu trả lời của mô hình.
"""


def judge_response(question: str, correct_answer: str, model_answer: str) -> dict:
    """
    Use LLM as judge to score model response against reference answer.

    Args:
        question: The question asked
        correct_answer: The correct/reference answer
        model_answer: The model's response to evaluate

    Returns:
        Dictionary with score, verdict, and reason
    """
    try:
        user_prompt = JUDGE_USER_TEMPLATE.format(
            question=question,
            correct_answer=correct_answer,
            model_answer=model_answer
        )

        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        result = response.choices[0].message.content.strip()

        # Parse JSON
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()

        return json.loads(result)

    except json.JSONDecodeError as e:
        return {"score": 0, "verdict": "error", "reason": f"JSON parse error: {str(e)}"}
    except Exception as e:
        return {"score": 0, "verdict": "error", "reason": f"Error: {str(e)}"}


def run_llm_judge_scoring(data: list, progress_file: str = None) -> list:
    """
    Run LLM Judge scoring for all items.
    Saves progress after each item to JSON file.

    Args:
        data: List of Q&A dictionaries with gpt_answer field
        progress_file: Path to save/load progress JSON

    Returns:
        List of Q&A dictionaries with judge_score, judge_verdict, judge_reason fields
    """
    # Load existing progress
    processed = {}
    if progress_file and os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                processed = json.load(f)
            print(f"  Loaded {len(processed)} existing judge scores")
        except:
            pass

    total = len(data)
    scored_count = 0
    skipped_count = 0

    for idx, item in enumerate(data, 1):
        item_id = item.get("id", f"Q{idx}")

        # Skip if already processed
        if item_id in processed:
            item["judge_score"] = processed[item_id].get("score", 0)
            item["judge_verdict"] = processed[item_id].get("verdict", "")
            item["judge_reason"] = processed[item_id].get("reason", "")
            continue

        # Skip if no GPT answer
        gpt_answer = item.get("gpt_answer", "")
        if not gpt_answer or gpt_answer.startswith("[ERROR") or gpt_answer == "[NO RESPONSE]":
            item["judge_score"] = None
            item["judge_verdict"] = "no_answer"
            item["judge_reason"] = "Không có câu trả lời GPT"
            skipped_count += 1
            continue

        print(f"  [{idx}/{total}] Judging {item_id}...")

        question = item.get("question", "")
        correct_answer = item.get("answer", "")

        # Get judge score
        judgment = judge_response(question, correct_answer, gpt_answer)

        item["judge_score"] = judgment.get("score", 0)
        item["judge_verdict"] = judgment.get("verdict", "error")
        item["judge_reason"] = judgment.get("reason", "")
        scored_count += 1

        # Save to processed dict
        processed[item_id] = {
            "score": item["judge_score"],
            "verdict": item["judge_verdict"],
            "reason": item["judge_reason"]
        }

        # Save progress after EACH item
        if progress_file:
            try:
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"    ⚠ Error saving progress: {e}")

        # Print progress
        if scored_count % 10 == 0:
            print(f"    Progress: {scored_count} scored, {skipped_count} skipped")

    print(f"  ✓ Completed: {scored_count} scored, {skipped_count} skipped (no GPT answer)")
    return data


def load_chatgpt_web_answers(web_answers_files: list, data: list) -> list:
    """
    Load câu trả lời từ ChatGPT web scraper và merge vào data.
    Hỗ trợ load từ nhiều file (văn hóa + pháp luật).

    Args:
        web_answers_files: List of paths to JSON files (e.g., [culture.json, law.json])
        data: List of Q&A dictionaries

    Returns:
        List of Q&A dictionaries with gpt_answer field
    """
    # Merge all answers from multiple files
    all_web_answers = {}

    for web_file in web_answers_files:
        if not os.path.exists(web_file):
            print(f"  ⚠ File not found: {web_file}")
            continue

        try:
            with open(web_file, 'r', encoding='utf-8') as f:
                web_answers = json.load(f)
            all_web_answers.update(web_answers)
            print(f"  ✓ Loaded {len(web_answers)} answers from {os.path.basename(web_file)}")
        except Exception as e:
            print(f"  ✗ Error loading {web_file}: {e}")

    print(f"  Total: {len(all_web_answers)} ChatGPT web answers")

    # Merge answers into data
    matched = 0
    for item in data:
        item_id = item.get("id", "")
        if item_id in all_web_answers:
            answer_data = all_web_answers[item_id]
            # Get the answer text
            if isinstance(answer_data, dict):
                item["gpt_answer"] = answer_data.get("gpt_web_answer", "")
            else:
                item["gpt_answer"] = str(answer_data)
            matched += 1

    print(f"  ✓ Matched {matched}/{len(data)} answers")
    return data


def create_validation_excel(data: list, output_path: str, include_gpt_answer: bool = True, include_judge_score: bool = False):
    """
    Create Excel file with validation columns for manual scoring.

    Args:
        data: List of Q&A dictionaries
        output_path: Path to output Excel file
        include_gpt_answer: Whether to include GPT_Answer column
        include_judge_score: Whether to include LLM Judge Score columns
    """
    # Pre-analyze data quality for all items
    print("  Analyzing data quality...")
    quality_results = analyze_benchmark_with_status(data)
    critical_count = sum(1 for r in quality_results.values() if r["status"] == "CRITICAL")
    warning_count = sum(1 for r in quality_results.values() if r["status"] == "OK (warning)")
    ok_count = sum(1 for r in quality_results.values() if r["status"] == "OK")
    print(f"  ✓ OK: {ok_count} | OK (warning): {warning_count} | ✗ CRITICAL: {critical_count}")

    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Validation"

    # Define headers based on options
    headers = [
        "ID",
        "Source",
        "Category",
        "Predicted Topic\n(Chủ đề dự đoán)",
        "Context",
        "Question",
        "Answer\n(Đáp án chuẩn)",
    ]
    col_widths = [10, 20, 10, 15, 35, 45, 50]

    if include_gpt_answer:
        headers.append("GPT_Answer\n(GPT trả lời)")
        col_widths.append(50)

    if include_judge_score:
        headers.extend([
            "GPT Score\n(Điểm GPT)",
            "GPT Verdict",
            "GPT Reason\n(Lý do)"
        ])
        col_widths.extend([12, 12, 40])

    headers.extend([
        "Data Quality\n(Lỗi dữ liệu)",
        "Notes"
    ])
    col_widths.extend([45, 30])

    # Styles
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    wrap_align = Alignment(vertical='top', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Write headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    # Set column widths
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # Write data rows
    for row_idx, item in enumerate(data, 2):
        col = 1

        # ID
        ws.cell(row=row_idx, column=col, value=item.get("id", "")).border = thin_border
        col += 1

        # Source
        ws.cell(row=row_idx, column=col, value=item.get("source", "")).border = thin_border
        col += 1

        # Category
        ws.cell(row=row_idx, column=col, value=item.get("category", "")).border = thin_border
        col += 1

        # Predicted Topic
        topic_cell = ws.cell(row=row_idx, column=col, value=item.get("predicted_topic", ""))
        topic_cell.alignment = center_align
        topic_cell.border = thin_border
        # Màu sắc theo chủ đề
        topic = item.get("predicted_topic", "")
        topic_colors = {
            "Pháp luật": "B4C6E7",      # Xanh dương nhạt
            "Văn hóa": "F8CBAD",         # Cam nhạt
            "Lịch sử": "FFE699",         # Vàng nhạt
            "Kinh tế": "C6EFCE",         # Xanh lá nhạt
            "Chính trị": "D9E1F2",       # Xanh tím nhạt
            "Xã hội": "E2EFDA",          # Xanh lá nhạt 2
            "Giáo dục": "FCE4D6",        # Hồng nhạt
            "Tôn giáo": "DDEBF7",        # Xanh dương nhạt 2
            "Nghệ thuật": "FFF2CC",      # Vàng nhạt 2
            "Phong tục tập quán": "E4DFEC",  # Tím nhạt
            "Địa lý": "D0CECE",          # Xám nhạt
            "Khác": "F2F2F2"             # Xám rất nhạt
        }
        if topic in topic_colors:
            topic_cell.fill = PatternFill(start_color=topic_colors[topic], end_color=topic_colors[topic], fill_type="solid")
        col += 1

        # Context
        ctx_cell = ws.cell(row=row_idx, column=col, value=item.get("context", ""))
        ctx_cell.alignment = wrap_align
        ctx_cell.border = thin_border
        col += 1

        # Question
        q_cell = ws.cell(row=row_idx, column=col, value=item.get("question", ""))
        q_cell.alignment = wrap_align
        q_cell.border = thin_border
        col += 1

        # Answer (đáp án chuẩn)
        a_cell = ws.cell(row=row_idx, column=col, value=item.get("answer", ""))
        a_cell.alignment = wrap_align
        a_cell.border = thin_border
        col += 1

        # GPT Answer (nếu có)
        if include_gpt_answer:
            gpt_cell = ws.cell(row=row_idx, column=col, value=item.get("gpt_answer", ""))
            gpt_cell.alignment = wrap_align
            gpt_cell.border = thin_border
            # Highlight if GPT answer exists
            if item.get("gpt_answer"):
                gpt_cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
            col += 1

        # Judge Score columns (nếu có)
        if include_judge_score:
            # Score
            judge_score = item.get("judge_score")
            score_cell = ws.cell(row=row_idx, column=col, value=judge_score if judge_score is not None else "")
            score_cell.alignment = center_align
            score_cell.border = thin_border
            # Color based on score
            if judge_score is not None:
                score_fills = {
                    1.0: "00B050",  # Dark Green
                    0.9: "92D050",  # Light Green
                    0.8: "C6EFCE",  # Pale Green
                    0.7: "D9EAD3",  # Very Pale Green
                    0.6: "FFF2CC",  # Light Yellow
                    0.5: "FFEB9C",  # Yellow
                    0.4: "FFD966",  # Dark Yellow
                    0.3: "F4B183",  # Light Orange
                    0.2: "FF9999",  # Light Red
                    0.1: "FF6666",  # Red
                    0.0: "FF0000",  # Dark Red
                }
                if judge_score in score_fills:
                    score_cell.fill = PatternFill(start_color=score_fills[judge_score], end_color=score_fills[judge_score], fill_type="solid")
            col += 1

            # Verdict
            verdict_cell = ws.cell(row=row_idx, column=col, value=item.get("judge_verdict", ""))
            verdict_cell.alignment = center_align
            verdict_cell.border = thin_border
            col += 1

            # Reason
            reason_cell = ws.cell(row=row_idx, column=col, value=item.get("judge_reason", ""))
            reason_cell.alignment = wrap_align
            reason_cell.border = thin_border
            col += 1

        # Data Quality Issues
        item_id = item.get("id", f"Q{row_idx-1}")
        quality_info = quality_results.get(item_id, {"issues": [], "status": "OK"})
        quality_status = quality_info["status"]
        item_issues = quality_info["issues"]

        # Hiển thị status + issues
        if quality_status == "OK":
            display_text = "OK"
        elif quality_status == "OK (warning)":
            display_text = f"✓ OK"
        else:
            display_text = f"✗ CRITICAL\n" + "; ".join(item_issues)

        quality_cell = ws.cell(row=row_idx, column=col, value=display_text)
        quality_cell.alignment = wrap_align
        quality_cell.border = thin_border

        # Màu sắc theo status
        if quality_status == "OK":
            # Xanh lá đậm - hoàn toàn tốt
            quality_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        elif quality_status == "OK (warning)":
            # Xanh lá nhạt - vẫn ổn
            quality_cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        else:
            # Cam - cần xem lại
            quality_cell.fill = PatternFill(start_color="FFE4B5", end_color="FFE4B5", fill_type="solid")
        col += 1

        # Notes column (empty for manual input)
        notes_cell = ws.cell(row=row_idx, column=col, value="")
        notes_cell.alignment = wrap_align
        notes_cell.border = thin_border

    # Freeze top row
    ws.freeze_panes = 'A2'

    # Add AutoFilter for sorting/filtering
    last_col_letter = get_column_letter(len(headers))
    last_row = len(data) + 1
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    # Add instruction sheet
    ws_guide = wb.create_sheet("Hướng dẫn")
    guide_content = [
        ["HƯỚNG DẪN ĐÁNH GIÁ Q&A BENCHMARK"],
        [""],
        ["=" * 60],
        ["CỘT DATA QUALITY (Kiểm tra tự động - góc nhìn 'người chưa đọc sách')"],
        ["=" * 60],
        [""],
        ["[NGU_CANH] - Lỗi Mất Ngữ Cảnh:"],
        ["   - Đại từ mơ hồ (anh ấy, họ, việc đó...)"],
        ["   - Context quá ngắn hoặc không cung cấp đủ thông tin"],
        [""],
        ["[TRI_THUC] - Lỗi Tri thức giả định:"],
        ["   - Câu hỏi yêu cầu thông tin không có trong context"],
        ["   - Câu hỏi 'tại sao' nhưng context không giải thích nguyên nhân"],
        [""],
        ["[NHIEU] - Lỗi Nhiễu Dữ liệu:"],
        ["   - Số trang, header/footer lẫn vào nội dung"],
        ["   - Câu bị ngắt giữa chừng"],
        [""],
        ["[MO_HO] - Lỗi Mơ hồ:"],
        ["   - Câu hỏi thiếu định danh cụ thể"],
        ["   - Câu hỏi mang tính chủ quan"],
        [""],
        ["[CAU_TRUC] - Lỗi Cấu trúc:"],
        ["   - Context quá ngắn/dài"],
        ["   - Cắt giữa câu quan trọng"],
        [""],
        ["[TRUNG_LAP] - Câu hỏi trùng lặp"],
        [""],
        ["=" * 60],
        ["TIÊU CHÍ ĐÁNH GIÁ THỦ CÔNG (Scoring: 1 = Đạt, 0.5 = Gần đạt, 0 = Không đạt)"],
        ["=" * 60],
        [""],
        ["1. text_based (Dựa vào văn bản)"],
        ["   - 1: Câu hỏi và đáp án dựa hoàn toàn vào nội dung văn bản gốc"],
        ["   - 0.5: Phần lớn dựa vào văn bản, có một chút suy luận nhẹ"],
        ["   - 0: Suy luận ngoài văn bản hoặc thông tin không có trong nguồn"],
        [""],
        ["2. no_temporal (Không thời gian)"],
        ["   - 1: Không có thông tin thay đổi theo thời gian (GDP, dân số, năm cụ thể...)"],
        ["   - 0.5: Có đề cập nhưng không ảnh hưởng đến tính đúng đắn của câu hỏi"],
        ["   - 0: Có thông tin có thể lỗi thời (số liệu năm X, sự kiện cụ thể...)"],
        [""],
        ["3. relevant (Liên quan)"],
        ["   - 1: Hoàn toàn liên quan đến văn hóa hoặc pháp luật Việt Nam"],
        ["   - 0.5: Liên quan nhưng có phần chung chung hoặc không đặc thù VN"],
        ["   - 0: Không liên quan hoặc quá xa vời"],
        [""],
        ["4. objective (Khách quan)"],
        ["   - 1: Trung lập, khách quan, không có ý kiến cá nhân"],
        ["   - 0.5: Có một chút thiên vị nhưng không nghiêm trọng"],
        ["   - 0: Có ý kiến cá nhân, thiên vị rõ ràng"],
        [""],
        ["Tổng điểm tối đa: 4 điểm"],
        [""],
        ["Quy ước chất lượng:"],
        ["   - 4.0 điểm: Xuất sắc"],
        ["   - 3.0-3.5 điểm: Tốt"],
        ["   - 2.0-2.5 điểm: Trung bình (cần xem xét lại)"],
        ["   - < 2.0 điểm: Không đạt (cần loại bỏ hoặc sửa)"],
    ]

    for row_idx, row_content in enumerate(guide_content, 1):
        cell = ws_guide.cell(row=row_idx, column=1, value=row_content[0] if row_content else "")
        if row_idx == 1:
            cell.font = Font(bold=True, size=14)
        elif "tiêu chí" in str(row_content[0]).lower() if row_content else False:
            cell.font = Font(bold=True, size=12)

    ws_guide.column_dimensions['A'].width = 80

    # Add summary sheet
    ws_summary = wb.create_sheet("Tổng kết")
    summary_headers = ["Metric", "Value"]
    ws_summary.append(summary_headers)

    total_items = len(data)
    culture_count = sum(1 for d in data if d.get("category") == "culture")
    law_count = sum(1 for d in data if d.get("category") == "law")

    # Tính điểm GPT Judge trung bình
    judge_scores = [d.get("judge_score") for d in data if d.get("judge_score") is not None]
    avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else 0

    ws_summary.append(["Tổng số câu hỏi", total_items])
    ws_summary.append(["Nguồn: Văn hóa", culture_count])
    ws_summary.append(["Nguồn: Pháp luật", law_count])
    ws_summary.append([""])
    ws_summary.append(["Có câu trả lời GPT", sum(1 for d in data if d.get("gpt_answer"))])
    ws_summary.append(["Có điểm Judge", len(judge_scores)])
    ws_summary.append(["Điểm Judge trung bình", f"{avg_judge_score:.3f}"])

    # Data Quality Statistics
    ws_summary.append([""])
    ws_summary.append(["=" * 40, ""])
    ws_summary.append(["DATA QUALITY (Kiểm tra tự động)", ""])
    ws_summary.append(["=" * 40, ""])

    # Count by status
    status_counts = {"OK": ok_count, "OK (warning)": warning_count, "CRITICAL": critical_count}
    items_ok_total = ok_count + warning_count

    ws_summary.append(["✓ OK (hoàn toàn tốt)", f"{ok_count}"])
    ws_summary.append(["✓ OK (warning - vẫn ổn)", f"{warning_count} ({warning_count/total_items*100:.1f}%)"])
    ws_summary.append(["✗ CRITICAL (cần xem lại)", f"{critical_count} ({critical_count/total_items*100:.1f}%)"])
    ws_summary.append([""])
    ws_summary.append(["=> Câu hỏi vẫn OK:", f"{items_ok_total} ({items_ok_total/total_items*100:.1f}%)"])

    # Count by issue type
    issue_type_counts = {
        "NGU_CANH": 0,
        "TRI_THUC": 0,
        "NHIEU": 0,
        "MO_HO": 0,
        "CAU_TRUC": 0,
        "TRUNG_LAP": 0,
        "KHO_HIEU": 0,
        "NHAY_CAM": 0,
    }
    for item_id, info in quality_results.items():
        for issue in info["issues"]:
            for issue_type in issue_type_counts.keys():
                if f"[{issue_type}]" in issue:
                    issue_type_counts[issue_type] += 1

    ws_summary.append([""])
    ws_summary.append(["[WARNING - Vẫn OK]:", ""])
    ws_summary.append(["  NGU_CANH (Context ngắn)", f"{issue_type_counts['NGU_CANH']}"])
    ws_summary.append(["  TRI_THUC (Tri thức chung)", f"{issue_type_counts['TRI_THUC']}"])
    ws_summary.append(["  CAU_TRUC (Cấu trúc)", f"{issue_type_counts['CAU_TRUC']}"])

    ws_summary.append([""])
    ws_summary.append(["[CRITICAL - Cần sửa]:", ""])
    ws_summary.append(["  TRUNG_LAP (Trùng lặp)", f"{issue_type_counts['TRUNG_LAP']}"])
    ws_summary.append(["  NHIEU (Nhiễu)", f"{issue_type_counts['NHIEU']}"])
    ws_summary.append(["  MO_HO (Mơ hồ)", f"{issue_type_counts['MO_HO']}"])
    ws_summary.append(["  KHO_HIEU (Khó hiểu)", f"{issue_type_counts['KHO_HIEU']}"])
    ws_summary.append(["  NHAY_CAM (Nhạy cảm)", f"{issue_type_counts['NHAY_CAM']}"])

    # Topic Statistics
    ws_summary.append([""])
    ws_summary.append(["=" * 40, ""])
    ws_summary.append(["CHỦ ĐỀ DỰ ĐOÁN", ""])
    ws_summary.append(["=" * 40, ""])

    # Count by topic
    topic_counts = {}
    for item in data:
        topic = item.get("predicted_topic", "Khác")
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

    # Sort by count descending
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        ws_summary.append([f"  {topic}", f"{count} ({count/total_items*100:.1f}%)"])

    # Style summary headers
    for cell in ws_summary[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")

    ws_summary.column_dimensions['A'].width = 25
    ws_summary.column_dimensions['B'].width = 20

    # Save workbook
    wb.save(output_path)
    print(f"\n✓ Excel file saved to: {output_path}")
    print(f"  - Total Q&A pairs: {len(data)}")
    print(f"  - Sheets: Validation, Hướng dẫn, Tổng kết")


def main():
    """Main function to export validation Excel."""
    import argparse

    parser = argparse.ArgumentParser(description='Export Q&A Benchmark to Validation Excel')
    parser.add_argument('--no-gpt', action='store_true',
                        help='Skip generating GPT answers (faster, no API calls)')
    parser.add_argument('--from-web', action='store_true',
                        help='Load GPT answers from ChatGPT web scraper (both culture and law files)')
    parser.add_argument('--web-file', type=str, default=None,
                        help='Path to additional ChatGPT web answers JSON file')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of questions to process (for testing)')
    parser.add_argument('--from-chunks', action='store_true',
                        help='Load from chunk files (preserves source file paths)')
    parser.add_argument('--predict-topics', action='store_true',
                        help='Predict topics for each question using LLM')
    parser.add_argument('--no-topics', action='store_true',
                        help='Skip topic prediction (faster)')
    parser.add_argument('--judge', action='store_true',
                        help='Run LLM Judge scoring (GPT evaluates GPT answers)')
    parser.add_argument('--no-judge', action='store_true',
                        help='Skip LLM Judge scoring')
    args = parser.parse_args()

    # Paths
    base_dir = r"D:/dichdata/vietnamese-culture-eval-2"
    qa_dir = os.path.join(base_dir, "data_question_answer")

    output_path = os.path.join(base_dir, "vietnamese_benchmark_validation.xlsx")
    progress_file = os.path.join(base_dir, "gpt_answers_progress.json")
    topics_progress_file = os.path.join(base_dir, "topics_progress.json")
    judge_progress_file = os.path.join(base_dir, "judge_scores_progress.json")

    print("=" * 60)
    print("EXPORTING VIETNAMESE BENCHMARK TO VALIDATION EXCEL")
    print("=" * 60)

    # Load data
    print("\nLoading benchmark data...")

    if args.from_chunks:
        # Load from individual chunk files (preserves source paths)
        print("  (Loading from chunk files to preserve source paths)")
        data = []

        # Culture chunks
        culture_chunks_dir = os.path.join(qa_dir, "ban_sac_van_hoa_viet_nam", "chunks")
        data.extend(load_benchmark_from_chunks(culture_chunks_dir, "culture"))

        # Law chunks
        law_chunks_dir = os.path.join(qa_dir, "bai_giang_phap_luat_dai_cuong", "chunks")
        data.extend(load_benchmark_from_chunks(law_chunks_dir, "law"))
    else:
        # Load from merged benchmark files
        json_paths = [
            os.path.join(qa_dir, "ban_sac_van_hoa_viet_nam", "culture_benchmark.json"),
            os.path.join(qa_dir, "bai_giang_phap_luat_dai_cuong", "law_benchmark.json"),
        ]
        data = load_benchmark_data(json_paths)

    if not data:
        print("\n⚠ No data found. Please run generate_qa_benchmark.py first.")
        return

    # Apply limit if specified
    if args.limit:
        data = data[:args.limit]
        print(f"  Limited to {args.limit} questions for testing")

    include_gpt_answer = not args.no_gpt
    include_judge_score = args.judge and not args.no_judge

    # Get GPT answers
    if args.from_web:
        # Load từ ChatGPT web scraper - CẢ 2 FILE (văn hóa + pháp luật)
        web_files = [
            os.path.join(base_dir, "chatgpt_web_answers.json"),       # Văn hóa
            os.path.join(base_dir, "chatgpt_web_answers_law.json"),   # Pháp luật
        ]
        # Thêm file custom nếu có
        if args.web_file:
            web_files.append(args.web_file)

        print(f"\nLoading GPT answers from ChatGPT web scraper...")
        for f in web_files:
            print(f"  - {os.path.basename(f)}")
        data = load_chatgpt_web_answers(web_files, data)
        include_gpt_answer = True
    elif include_gpt_answer:
        # Generate qua API
        print(f"\nGenerating GPT answers via API for {len(data)} questions...")
        print("  (This may take a while. Progress is saved after each answer.)")
        print("  (You can stop and resume later.)")
        data = generate_gpt_answers(data, progress_file)
    else:
        print("\nSkipping GPT answer generation (--no-gpt flag)")

    # Run LLM Judge scoring
    if include_judge_score:
        print(f"\nRunning LLM Judge scoring for {len(data)} questions...")
        print("  (Progress saved after EACH item to JSON)")
        print("  (You can stop and resume later.)")
        data = run_llm_judge_scoring(data, judge_progress_file)
    else:
        # Load existing judge scores if available
        if os.path.exists(judge_progress_file):
            print(f"\nLoading existing judge scores from {judge_progress_file}...")
            try:
                with open(judge_progress_file, 'r', encoding='utf-8') as f:
                    judge_progress = json.load(f)
                for item in data:
                    item_id = item.get("id", "")
                    if item_id in judge_progress:
                        item["judge_score"] = judge_progress[item_id].get("score")
                        item["judge_verdict"] = judge_progress[item_id].get("verdict", "")
                        item["judge_reason"] = judge_progress[item_id].get("reason", "")
                include_judge_score = True
                print(f"  ✓ Loaded {len(judge_progress)} judge scores")
            except Exception as e:
                print(f"  ⚠ Error loading judge scores: {e}")

    # Predict topics
    if not args.no_topics:
        print(f"\nPredicting topics for {len(data)} questions...")
        print("  (This may take a while. Progress is saved every 10 items.)")
        data = predict_topics_batch(data, topics_progress_file)
    else:
        print("\nSkipping topic prediction (--no-topics flag)")

    # Create Excel
    print(f"\nCreating validation Excel with {len(data)} Q&A pairs...")
    create_validation_excel(data, output_path, include_gpt_answer, include_judge_score)

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"\nOutput: {output_path}")

    if include_gpt_answer:
        print("\nColumns in Excel:")
        print("  - Source: Đường dẫn file chunk nguồn")
        print("  - Answer: Đáp án chuẩn (gen từ đoạn văn gốc)")
        print("  - GPT_Answer: Câu trả lời của GPT (không có đoạn văn)")
        print("\n→ So sánh 2 cột này để đánh giá GPT 'biết' hay 'không biết' câu trả lời")


if __name__ == "__main__":
    main()
