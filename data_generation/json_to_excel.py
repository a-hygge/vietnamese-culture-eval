"""
Chuyển đổi các file JSON câu hỏi thành file Excel
Cột 1: Tên chunk
Cột 2: List câu hỏi (JSON array)
"""

import os
import json
import pandas as pd
from pathlib import Path


def json_to_excel(input_dir: str, output_file: str):
    """
    Đọc tất cả file JSON trong thư mục và chuyển thành Excel.
    
    Args:
        input_dir: Thư mục chứa các file JSON
        output_file: Đường dẫn file Excel đầu ra
    """
    
    # Lấy danh sách tất cả file JSON
    json_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.json')])
    
    if not json_files:
        print(f"Không tìm thấy file JSON nào trong {input_dir}")
        return
    
    print(f"Tìm thấy {len(json_files)} file JSON")
    
    # Danh sách để lưu dữ liệu
    data = []
    
    for json_file in json_files:
        file_path = os.path.join(input_dir, json_file)
        chunk_name = json_file.replace('.json', '')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            
            # Kiểm tra xem có phải là list không
            if isinstance(questions, list):
                # Chuyển list câu hỏi thành JSON string để hiển thị đẹp
                questions_str = json.dumps(questions, ensure_ascii=False, indent=2)
                
                data.append({
                    'Chunk': chunk_name,
                    'Questions': questions_str,
                    'Number_of_Questions': len(questions)
                })
                
                print(f"  ✓ {chunk_name}: {len(questions)} câu hỏi")
            else:
                print(f"  ⚠ {chunk_name}: Không phải list")
                data.append({
                    'Chunk': chunk_name,
                    'Questions': str(questions),
                    'Number_of_Questions': 0
                })
                
        except Exception as e:
            print(f"  ✗ Lỗi khi đọc {json_file}: {str(e)}")
            data.append({
                'Chunk': chunk_name,
                'Questions': f"ERROR: {str(e)}",
                'Number_of_Questions': 0
            })
    
    # Tạo DataFrame
    df = pd.DataFrame(data)
    
    # Lưu ra Excel
    try:
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n{'='*60}")
        print(f"✓ Đã lưu thành công vào: {output_file}")
        print(f"  Tổng số chunks: {len(data)}")
        print(f"  Tổng số câu hỏi: {df['Number_of_Questions'].sum()}")
        print(f"{'='*60}")
    except Exception as e:
        print(f"✗ Lỗi khi lưu Excel: {str(e)}")


def json_to_excel_detailed(input_dir: str, output_file: str):
    """
    Tạo Excel chi tiết với mỗi câu hỏi trên một dòng.
    
    Args:
        input_dir: Thư mục chứa các file JSON
        output_file: Đường dẫn file Excel đầu ra
    """
    
    json_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.json')])
    
    if not json_files:
        print(f"Không tìm thấy file JSON nào trong {input_dir}")
        return
    
    print(f"Tìm thấy {len(json_files)} file JSON")
    
    # Danh sách để lưu dữ liệu
    data = []
    
    for json_file in json_files:
        file_path = os.path.join(input_dir, json_file)
        chunk_name = json_file.replace('.json', '')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                questions = json.load(f)
            
            if isinstance(questions, list):
                for q in questions:
                    data.append({
                        'Chunk': chunk_name,
                        'Question_ID': q.get('question_id', ''),
                        'Question': q.get('question', ''),
                        'Answer': q.get('answer', ''),
                        'Context': q.get('context', ''),
                        'Cite': q.get('cite', '')
                    })
                
                print(f"  ✓ {chunk_name}: {len(questions)} câu hỏi")
            else:
                print(f"  ⚠ {chunk_name}: Không phải list")
                
        except Exception as e:
            print(f"  ✗ Lỗi khi đọc {json_file}: {str(e)}")
    
    # Tạo DataFrame
    df = pd.DataFrame(data)
    
    # Lưu ra Excel
    try:
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n{'='*60}")
        print(f"✓ Đã lưu thành công vào: {output_file}")
        print(f"  Tổng số câu hỏi: {len(data)}")
        print(f"{'='*60}")
    except Exception as e:
        print(f"✗ Lỗi khi lưu Excel: {str(e)}")


if __name__ == '__main__':
    # Cấu hình đường dẫn
    input_dir = r"D:/dichdata/vietnamese-culture-eval-2/data_question_answer/ban_sac_van_hoa_viet_nam/structured_chunks_v2"
    
    
    # 2. Format chi tiết: Mỗi câu hỏi một dòng
    output_detailed = r"D:/dichdata/vietnamese-culture-eval-2/questions_detailed.xlsx"
    print("=" * 60)
    print("XUẤT FILE CHI TIẾT (mỗi câu hỏi một dòng)")
    print("=" * 60)
    json_to_excel_detailed(input_dir, output_detailed)
