import docx

def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    p._element = p._parent = None

def remove_experience_from_docx(file_path):
    doc = docx.Document(file_path)
    paragraphs_to_remove = []
    
    # Tìm các đoạn văn thuộc phần EXPERIENCE / KINH NGHIỆM LÀM VIỆC
    is_exp_section = False
    for p in doc.paragraphs:
        text = p.text.strip().upper()
        if "EXPERIENCE" in text or "KINH NGHIỆM LÀM VIỆC" in text:
            is_exp_section = True
            paragraphs_to_remove.append(p)
            continue
            
        if is_exp_section:
            # Dừng lại khi gặp phần PROJECTS / DỰ ÁN TIÊU BIỂU
            if "PROJECTS" in text or "DỰ ÁN TIÊU BIỂU" in text:
                is_exp_section = False
                continue
            paragraphs_to_remove.append(p)
            
    for p in paragraphs_to_remove:
        try:
            delete_paragraph(p)
        except Exception as e:
            print(f"Lỗi khi xóa: {e}")
            
    doc.save(file_path)
    print(f"Đã xóa phần kinh nghiệm khỏi {file_path}")

def main():
    remove_experience_from_docx('/home/truongan/Downloads/resume_truongan.docx')
    remove_experience_from_docx('/home/truongan/Downloads/resume_truongan_vi.docx')

if __name__ == "__main__":
    main()
