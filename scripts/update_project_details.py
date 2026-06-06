import docx
import os
import subprocess

def update_file_content(file_path, old_text, new_text):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_text in content:
        content = content.replace(old_text, new_text)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated content in: {file_path}")

def update_docx_project_headings(file_path):
    if not os.path.exists(file_path):
        return
    doc = docx.Document(file_path)
    updated = False
    for p in doc.paragraphs:
        # Project 1 update: remove Docker
        if "AI Security WAF & Active Vulnerability Scanner" in p.text and "Docker" in p.text:
            print(f"Updating Project 1 in {file_path}...")
            p.text = p.text.replace(" · Docker", "").replace(", Docker", "")
            updated = True
        
        # Project 4 update: rename and add Docker
        if "Scalable Research Paper Search Engine" in p.text:
            print(f"Updating Project 4 in {file_path}...")
            p.text = p.text.replace("Scalable Research Paper Search Engine", "HUS Scientific Works")
            p.text = p.text.replace("FastAPI · SQL", "FastAPI · SQL · Docker")
            updated = True
            
    if updated:
        doc.save(file_path)
        print(f"Saved docx: {file_path}")

def main():
    # 1. Update cv.txt
    update_file_content(
        '/home/truongan/my_agent_project/cv.txt',
        '1. AI Security WAF & Active Vulnerability Scanner (Jan. 2026 -- May 2026)\n- Developed an active vulnerability scanner and a passive Web Application Firewall (WAF) powered by a Deep Learning model (Bi-LSTM architecture) achieving 99.68% accuracy in classifying payload attacks.',
        '1. AI Security WAF & Active Vulnerability Scanner (Jan. 2026 -- May 2026)\n- Developed an active vulnerability scanner and a passive Web Application Firewall (WAF) powered by a Deep Learning model (Bi-LSTM architecture) achieving 99.68% accuracy in classifying payload attacks.' # actually wait, we just want to remove the Docker reference if any. Let's see if Docker is in cv.txt projects.
    )
    # Let's do a direct replace in cv.txt for:
    # "1. AI Security WAF & Active Vulnerability Scanner (Jan. 2026 -- May 2026)" -> wait, in cv.txt Project 1 didn't have Docker in the title.
    # In cv.txt Project 4:
    # "4. Scalable Research Paper Search Engine (Jan. 2026 -- Mar. 2026)"
    update_file_content('/home/truongan/my_agent_project/cv.txt', '4. Scalable Research Paper Search Engine (Jan. 2026 -- Mar. 2026)', '4. HUS Scientific Works (Jan. 2026 -- Mar. 2026)')
    update_file_content('/home/truongan/my_agent_project/cv_vi.txt', '4. Hệ thống tìm kiếm đề tài nghiên cứu khoa học quy mô lớn (Th1. 2026 -- Th3. 2026)', '4. HUS Scientific Works (Th1. 2026 -- Th3. 2026)')

    # 2. Update HTML
    update_file_content(
        '/home/truongan/my_agent_project/resume.html',
        '<span><strong>AI Security WAF & Active Vulnerability Scanner</strong> | <em>Python, TensorFlow/Keras, Flask, Docker</em> | <a href="https://github.com/frograiny/ai_security">Link Repo</a></span>',
        '<span><strong>AI Security WAF & Active Vulnerability Scanner</strong> | <em>Python, TensorFlow/Keras, Flask</em> | <a href="https://github.com/frograiny/ai_security">Link Repo</a></span>'
    )
    update_file_content(
        '/home/truongan/my_agent_project/resume.html',
        '<span><strong>Scalable Research Paper Search Engine</strong> | <em>React, TypeScript, FastAPI, SQL</em> | <a href="https://hus-scientific-works.vercel.app/">Live Demo</a></span>',
        '<span><strong>HUS Scientific Works</strong> | <em>React, TypeScript, FastAPI, SQL, Docker</em> | <a href="https://hus-scientific-works.vercel.app/">Live Demo</a></span>'
    )
    update_file_content(
        '/home/truongan/my_agent_project/resume_vi.html',
        '<span><strong>Tường lửa WAF & Bộ quét lỗ hổng bảo mật ứng dụng AI</strong> | <em>Python, TensorFlow/Keras, Flask, Docker</em> | <a href="https://github.com/frograiny/ai_security">Link Repo</a></span>',
        '<span><strong>Tường lửa WAF & Bộ quét lỗ hổng bảo mật ứng dụng AI</strong> | <em>Python, TensorFlow/Keras, Flask</em> | <a href="https://github.com/frograiny/ai_security">Link Repo</a></span>'
    )
    update_file_content(
        '/home/truongan/my_agent_project/resume_vi.html',
        '<span><strong>Hệ thống tìm kiếm đề tài nghiên cứu khoa học quy mô lớn</strong> | <em>React, TypeScript, FastAPI, SQL</em> | <a href="https://hus-scientific-works.vercel.app/">Link sản phẩm</a></span>',
        '<span><strong>HUS Scientific Works</strong> | <em>React, TypeScript, FastAPI, SQL, Docker</em> | <a href="https://hus-scientific-works.vercel.app/">Link sản phẩm</a></span>'
    )

    # 3. Update DOCX
    update_docx_project_headings('/home/truongan/Downloads/resume_truongan.docx')
    update_docx_project_headings('/home/truongan/Downloads/resume_truongan_vi.docx')

    # 4. Convert to PDF again
    print("Re-converting to PDF...")
    subprocess.run([
        'libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', '/home/truongan/Downloads',
        '/home/truongan/Downloads/resume_truongan.docx'
    ])
    subprocess.run([
        'mv', '/home/truongan/Downloads/resume_truongan.pdf', '/home/truongan/Downloads/DinhTruongAn_CV_EN.pdf'
    ])
    
    subprocess.run([
        'libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', '/home/truongan/Downloads',
        '/home/truongan/Downloads/resume_truongan_vi.docx'
    ])
    subprocess.run([
        'mv', '/home/truongan/Downloads/resume_truongan_vi.pdf', '/home/truongan/Downloads/DinhTruongAn_CV_VI.pdf'
    ])
    print("PDF Conversion Complete.")

if __name__ == "__main__":
    main()
