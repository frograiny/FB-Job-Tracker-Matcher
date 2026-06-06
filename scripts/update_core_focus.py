import docx
import os

# 1. Update text files
def update_txt_file(file_path, old_text, new_text):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_text in content:
        content = content.replace(old_text, new_text)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated txt: {file_path}")

# 2. Update HTML files
def update_html_file(file_path, old_text, new_text):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_text in content:
        content = content.replace(old_text, new_text)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated html: {file_path}")

# 3. Update DOCX files
def update_docx_file(file_path, search_text, new_text):
    if not os.path.exists(file_path):
        return
    doc = docx.Document(file_path)
    updated = False
    for p in doc.paragraphs:
        if search_text in p.text:
            print(f"Found paragraph in {file_path}: {p.text}")
            p.text = new_text
            updated = True
    if updated:
        doc.save(file_path)
        print(f"Updated docx: {file_path}")

def main():
    # English versions
    old_en = "Core Focus: Data Structures and Algorithms, Advanced Database Systems, Network Security, Software Architecture, and AI-Driven Software Development."
    new_en_txt = "Core Focus: Artificial Intelligence & Machine Learning, Agentic Workflows, Web Application Development, and Software Architecture."
    
    # HTML en
    old_html_en = "<strong>Core Focus:</strong> Data Structures and Algorithms, Advanced Database Systems, Network Security, Software Architecture, and AI-Driven Software Development."
    new_html_en = "<strong>Core Focus:</strong> Artificial Intelligence & Machine Learning, Agentic Workflows, Web Application Development, and Software Architecture."
    
    # DOCX en has different formatting maybe? Let's check paragraph style or search text
    # In resume_truongan.docx, Education has:
    # "B.Sc. Computer and Information Science  |  University of Science - VNU   Sep 2022 – Jun 2026"
    # Followed by a bullet point paragraph. Let's find it.
    
    # Vietnamese versions
    old_vi = "Trọng tâm đào tạo: Cấu trúc dữ liệu và giải thuật, Hệ quản trị cơ sở dữ liệu nâng cao, An toàn thông tin mạng, Kiến trúc phần mềm và Phát triển phần mềm hướng AI."
    new_vi_txt = "Trọng tâm đào tạo: Trí tuệ nhân tạo & Học sâu, Hệ thống AI Agent, Phát triển ứng dụng Web và Kiến trúc phần mềm."
    
    # HTML vi
    old_html_vi = "<strong>Trọng tâm đào tạo:</strong> Cấu trúc dữ liệu và giải thuật, Hệ quản trị cơ sở dữ liệu nâng cao, An toàn thông tin mạng, Kiến trúc phần mềm và Phát triển phần mềm hướng AI."
    new_html_vi = "<strong>Trọng tâm đào tạo:</strong> Trí tuệ nhân tạo & Học sâu, Hệ thống AI Agent, Phát triển ứng dụng Web và Kiến trúc phần mềm."

    # Update TXT
    update_txt_file('/home/truongan/my_agent_project/cv.txt', "Core Focus: Data Structures and Algorithms, Advanced Database Systems, Network Security, Software Architecture, and AI-Driven Software Development.", new_en_txt)
    update_txt_file('/home/truongan/my_agent_project/cv_vi.txt', "Trọng tâm đào tạo: Cấu trúc dữ liệu và giải thuật, Hệ quản trị cơ sở dữ liệu nâng cao, An toàn thông tin mạng, Kiến trúc phần mềm và Phát triển phần mềm hướng AI.", new_vi_txt)

    # Update HTML
    update_html_file('/home/truongan/my_agent_project/resume.html', old_html_en, new_html_en)
    update_html_file('/home/truongan/my_agent_project/resume_vi.html', old_html_vi, new_html_vi)

    # Update DOCX - let's search for "Core Focus" or "Trọng tâm đào tạo" in docx
    update_docx_file('/home/truongan/Downloads/resume_truongan.docx', "Core Focus:", "Core Focus: Artificial Intelligence & Machine Learning, Agentic Workflows, Web Application Development, and Software Architecture.")
    update_docx_file('/home/truongan/Downloads/resume_truongan_vi.docx', "Trọng tâm đào tạo:", "Trọng tâm đào tạo: Trí tuệ nhân tạo & Học sâu, Hệ thống AI Agent, Phát triển ứng dụng Web và Kiến trúc phần mềm.")

if __name__ == "__main__":
    main()
