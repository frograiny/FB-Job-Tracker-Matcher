import docx

def update_docx(file_path, search_text, suffix):
    doc = docx.Document(file_path)
    updated = False
    for p in doc.paragraphs:
        if search_text in p.text:
            print(f"Found paragraph in {file_path}: {p.text}")
            p.text = p.text.strip() + suffix
            updated = True
            break
    if updated:
        doc.save(file_path)
        print(f"Successfully saved {file_path}")
    else:
        print(f"Could not find matching paragraph in {file_path}")

def main():
    # English CV
    update_docx(
        '/home/truongan/Downloads/resume_truongan.docx',
        'orchestrated full-stack deployment via Docker Compose',
        ' (Live Demo: https://hus-scientific-works.vercel.app/)'
    )
    # Vietnamese CV
    update_docx(
        '/home/truongan/Downloads/resume_truongan_vi.docx',
        'đóng gói triển khai bằng Docker Compose',
        ' (Link sản phẩm: https://hus-scientific-works.vercel.app/)'
    )

if __name__ == "__main__":
    main()
