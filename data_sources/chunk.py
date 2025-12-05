"""
Split PDF(s) into structured chunks based on document structure (chapters, sections, subsections).
Uses semantic markers like roman numerals (I, II, III), decimal numbering (1.1, 2.1), 
and chapter headers to intelligently split content.
"""

import os
import re
from langchain_community.document_loaders import PyPDFLoader
from typing import List, Tuple

# Complete Vietnamese uppercase characters
VN_UPPER = r"A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ"


def detect_section_headers(text: str) -> List[Tuple[int, str, str, int]]:
    """
    Phát hiện các đầu mục/tiêu đề trong văn bản.
    Trả về list của (vị trí, loại, nội dung)
    """
    patterns = [
        # Chương với số La Mã: "CHƯƠNG I", "CHƯƠNG II", etc.
        (r'^CHƯƠNG\s+([IVX]+)[\s\.:]*(.*)$', 'chapter_roman', 1),
        # Chương với số Ả Rập: "CHƯƠNG 1", "CHƯƠNG 2", etc.
        (r'^CHƯƠNG\s+(\d+)[\s\.:]*(.*)$', 'chapter_numeric', 1),
        # Phần với số La Mã lớn: "I.", "II.", "III." (độc lập trên 1 dòng hoặc có tiêu đề ngắn)
        (rf'^([IVX]+)[\.\s]+([{VN_UPPER}].{{0,80}})$', 'section_roman', 2),
        # Mục đánh số thập phân: "1.1", "2.1.3", etc.
        (r'^(\d+\.\d+(?:\.\d+)*)[\.\s]+(.{0,100})$', 'subsection_decimal', 3),
        # Mục đánh số đơn giản: "1.", "2.", etc với chữ hoa đầu
        (rf'^(\d+)[\.\)]\s+([{VN_UPPER}].{{3,100}})$', 'section_numeric', 2),
        # Mục con với ký tự đặc biệt: "- ", "+ ", "• ", "* "
        (rf'^[•\-\+\*]\s+([{VN_UPPER}].{{10,100}})$', 'bullet_point', 4),
        # Tiêu đề ngắn IN HOA (độc lập trên 1 dòng, 3-50 ký tự)
        (rf'^([{VN_UPPER}\s]{{3,50}})$', 'title_caps', 3),
    ]
    
    markers = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 3:
            continue
            
        for pattern, section_type, priority in patterns:
            match = re.match(pattern, line, re.IGNORECASE | re.MULTILINE)
            if match:
                # Tính vị trí ký tự trong toàn bộ text
                char_pos = sum(len(lines[j]) + 1 for j in range(i))
                markers.append((char_pos, section_type, line, priority))
                break
    
    return markers


def split_by_structure(text: str, min_chunk_size: int = 200, max_chunk_size: int = 1500) -> List[str]:
    """
    Tách văn bản theo cấu trúc đầu mục.
    Ưu tiên giữ nguyên các section hoàn chỉnh nhưng tách nhỏ hơn.
    """
    markers = detect_section_headers(text)
    
    if not markers:
        # Nếu không tìm thấy markers, fallback về split theo đoạn văn
        return split_by_paragraphs(text, max_chunk_size)
    
    chunks = []
    
    # Thêm marker bắt đầu và kết thúc
    markers = [(0, 'start', '', 0)] + markers + [(len(text), 'end', '', 999)]
    
    for i in range(len(markers) - 1):
        start_pos = markers[i][0]
        end_pos = markers[i + 1][0]
        chunk_text = text[start_pos:end_pos].strip()
        
        if not chunk_text:
            continue
        
        # Nếu chunk quá lớn, chia nhỏ hơn theo đoạn văn
        if len(chunk_text) > max_chunk_size:
            sub_chunks = split_by_paragraphs(chunk_text, max_chunk_size)
            chunks.extend(sub_chunks)
        elif len(chunk_text) >= min_chunk_size:
            chunks.append(chunk_text)
        else:
            # Chunk quá nhỏ, gộp vào chunk trước đó
            if chunks and len(chunks[-1]) < max_chunk_size * 0.7:
                chunks[-1] = chunks[-1] + "\n\n" + chunk_text
            else:
                chunks.append(chunk_text)
    
    return chunks


def split_by_paragraphs(text: str, max_size: int = 1500) -> List[str]:
    """
    Fallback: Tách theo đoạn văn khi không có cấu trúc rõ ràng.
    Tách nhỏ hơn để dễ xử lý.
    """
    # Tách theo dấu xuống dòng kép hoặc dấu câu + xuống dòng
    paragraphs = re.split(r'\n\s*\n|(?<=[.!?])\s*\n', text)
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Nếu thêm paragraph này vào không vượt quá max_size
        if len(current_chunk) + len(para) + 2 <= max_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            # Lưu chunk hiện tại nếu có
            if current_chunk:
                chunks.append(current_chunk)
            
            # Nếu paragraph đơn lẻ quá dài, chia nhỏ theo câu
            if len(para) > max_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) + 1 <= max_size:
                        temp_chunk += (" " if temp_chunk else "") + sent
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = sent
                if temp_chunk:
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def split_pdf_to_txt(pdf_path: str, out_dir: str, min_chunk_size: int = 200, max_chunk_size: int = 1500):
    """
    Tách PDF thành các chunks theo cấu trúc văn bản.
    
    Args:
        pdf_path: Đường dẫn đến file PDF (hoặc thư mục chứa nhiều PDF)
        out_dir: Thư mục đầu ra
        min_chunk_size: Kích thước tối thiểu của chunk (ký tự) - mặc định 200
        max_chunk_size: Kích thước tối đa của chunk (ký tự) - mặc định 1500
    """
    os.makedirs(out_dir, exist_ok=True)
    
    # Xử lý cả file đơn lẻ hoặc thư mục
    pdf_files = []
    if os.path.isfile(pdf_path):
        pdf_files = [pdf_path]
    elif os.path.isdir(pdf_path):
        pdf_files = sorted([
            os.path.join(pdf_path, f) 
            for f in os.listdir(pdf_path) 
            if f.endswith('.pdf')
        ])
    
    all_chunks = []
    chunk_counter = 1
    
    for pdf_file in pdf_files:
        print(f"\nĐang xử lý: {os.path.basename(pdf_file)}")
        
        try:
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()
            
            # Gộp tất cả pages thành một văn bản duy nhất
            full_text = "\n\n".join([doc.page_content for doc in docs])
            
            # Tách theo cấu trúc
            chunks = split_by_structure(full_text, min_chunk_size, max_chunk_size)
            
            # Lưu từng chunk
            for chunk in chunks:
                fname = f"chunk_{chunk_counter:03d}.txt"
                out_path = os.path.join(out_dir, fname)
                
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                
                all_chunks.append(out_path)
                chunk_counter += 1
            
            print(f"  → Đã tạo {len(chunks)} chunks từ {os.path.basename(pdf_file)}")
            
        except Exception as e:
            print(f"  ✗ Lỗi khi xử lý {os.path.basename(pdf_file)}: {str(e)}")
            continue
    
    print(f"\n{'='*60}")
    print(f"Hoàn thành! Đã tạo {len(all_chunks)} chunk files trong {out_dir}")
    print(f"{'='*60}")
    return all_chunks


def process_all_sources():
    """
    Process both culture and law PDF sources.
    Target chunk size: 150-300 words (~750-1500 characters for Vietnamese)
    """
    # Configuration for both sources
    sources = [
        {
            "name": "Văn hóa Việt Nam",
            "pdf_path": r"D:/dichdata/vietnamese-culture-eval-2/data_base/ban_sac_van_hoa_viet_nam",
            "out_dir": r"D:/dichdata/vietnamese-culture-eval-2/data_sources/ban_sac_van_hoa_viet_nam/structured_chunks_v2"
        },
        {
            "name": "Pháp luật đại cương",
            "pdf_path": r"D:/dichdata/vietnamese-culture-eval-2/data_base/bai_giang_phap_luat_dai_cuong",
            "out_dir": r"D:/dichdata/vietnamese-culture-eval-2/data_sources/bai_giang_phap_luat_dai_cuong/structured_chunks_v2"
        }
    ]

    min_chunk_size = 750    
    max_chunk_size = 1500   

    for source in sources:
        print(f"\n{'='*60}")
        print(f"Processing: {source['name']}")
        print(f"{'='*60}")

        if os.path.exists(source['pdf_path']):
            split_pdf_to_txt(
                source['pdf_path'],
                source['out_dir'],
                min_chunk_size,
                max_chunk_size
            )
        else:
            print(f"  ⚠ Path not found: {source['pdf_path']}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Split PDFs into structured chunks')
    parser.add_argument('--source', choices=['culture', 'law', 'all'], default='all',
                        help='Source to process (culture, law, or all)')
    parser.add_argument('--min-size', type=int, default=750,
                        help='Minimum chunk size in characters (default: 750 ≈ 150 words)')
    parser.add_argument('--max-size', type=int, default=1500,
                        help='Maximum chunk size in characters (default: 1500 ≈ 300 words)')

    args = parser.parse_args()

    if args.source == 'all':
        process_all_sources()
    else:
        sources = {
            'culture': {
                "pdf_path": r"D:/dichdata/vietnamese-culture-eval-2/data_base/ban_sac_van_hoa_viet_nam",
                "out_dir": r"D:/dichdata/vietnamese-culture-eval-2/data_sources/ban_sac_van_hoa_viet_nam/structured_chunks_v2"
            },
            'law': {
                "pdf_path": r"D:/dichdata/vietnamese-culture-eval-2/data_base/bai_giang_phap_luat_dai_cuong",
                "out_dir": r"D:/dichdata/vietnamese-culture-eval-2/data_sources/bai_giang_phap_luat_dai_cuong/structured_chunks_v2"
            }
        }

        source = sources[args.source]
        if os.path.exists(source['pdf_path']):
            split_pdf_to_txt(
                source['pdf_path'],
                source['out_dir'],
                args.min_size,
                args.max_size
            )
        else:
            print(f"Path not found: {source['pdf_path']}")
