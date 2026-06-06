import docx

def main():
    doc_path = '/home/truongan/Downloads/resume_truongan.docx'
    doc = docx.Document(doc_path)
    
    # Cập nhật ngày tháng cho các dự án trong file Word
    for p in doc.paragraphs:
        # 1. Cập nhật Autonomous Job Application
        if "Autonomous Job Application" in p.text and "Jun 2026" in p.text:
            print("Cập nhật ngày dự án Agent:", p.text)
            # Thay thế Jun 2026 bằng Mar 2026 – Jun 2026
            p.text = p.text.replace("Jun 2026", "Mar 2026 – Jun 2026")
            
        # 2. Cập nhật Cross-Platform Clipboard Translator
        if "Cross-Platform Clipboard Translator" in p.text and "2025" in p.text:
            print("Cập nhật ngày dự án Translator:", p.text)
            # Thay thế 2025 bằng Sep 2025 – Dec 2025
            p.text = p.text.replace("2025", "Sep 2025 – Dec 2025")
            
    doc.save(doc_path)
    print("Đã cập nhật ngày tháng trong DOCX thành công!")

if __name__ == "__main__":
    main()
