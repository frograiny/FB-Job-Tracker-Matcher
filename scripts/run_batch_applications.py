import asyncio
import os
import sys
# Thêm thư mục gốc vào sys.path để import từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig
from src.job_app_agent import search_job_postings, log_application

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CV_EN_PATH = os.path.join(PROJECT_ROOT, "resume", "cv.txt")
CV_VI_PATH = os.path.join(PROJECT_ROOT, "resume", "cv_vi.txt")

# Khởi tạo mô tả công việc của 3 vị trí đích
JOBS = [
    {
        "company": "FPT Software",
        "position": "Python Developer Intern",
        "desc": "Yêu cầu kiến thức về Python cơ bản, FastAPI/Django, cơ sở dữ liệu SQL, Git."
    },
    {
        "company": "VinAI",
        "position": "AI Research Intern",
        "desc": "Yêu cầu kiến thức về Học sâu (Deep Learning), PyTorch/TensorFlow, toán tối ưu."
    },
    {
        "company": "VNG Corporation",
        "position": "Machine Learning Engineer Intern",
        "desc": "Phát triển và tối ưu hóa các mô hình ML, xử lý dữ liệu lớn bằng Python, Pandas."
    }
]

def load_cv_content(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def generate_cover_letter(cv_content, job, lang):
    config = LocalAgentConfig(
        system_instructions=(
            "You are a professional recruitment assistant. Your task is to write a highly tailored, "
            f"persuasive cover letter for an internship position in {'Vietnamese' if lang == 'vi' else 'English'}. "
            "Match the candidate's core projects and technical skills from their CV to the job description requirements."
        )
    )
    
    prompt = (
        f"Candidate CV:\n{cv_content}\n\n"
        f"Target Company: {job['company']}\n"
        f"Target Position: {job['position']}\n"
        f"Job Description: {job['desc']}\n\n"
        f"Please write a professional cover letter in {'Vietnamese' if lang == 'vi' else 'English'} "
        "addressing the hiring team. Do not include placeholders, output the complete ready-to-use letter."
    )
    
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()

async def main():
    print("=" * 60)
    print("Bắt đầu quy trình tự động hóa rải CV / viết Cover Letter hàng loạt...")
    print("=" * 60)
    
    cv_en = load_cv_content(CV_EN_PATH)
    cv_vi = load_cv_content(CV_VI_PATH)
    
    if not cv_en or not cv_vi:
        print("Lỗi: Không tìm thấy cv.txt hoặc cv_vi.txt. Vui lòng tạo 2 file này trước.")
        return

    for job in JOBS:
        print(f"\n[+] Đang xử lý hồ sơ ứng tuyển vào: {job['company']} - {job['position']}...")
        
        # 1. Sinh Cover Letter tiếng Anh
        print("  - Đang viết Cover Letter tiếng Anh...")
        cl_en = await generate_cover_letter(cv_en, job, "en")
        file_en_name = f"cover_letter_{job['company'].lower().split()[0]}_en.txt"
        file_en_path = os.path.join(PROJECT_ROOT, "resume", file_en_name)
        with open(file_en_path, "w", encoding="utf-8") as f:
            f.write(cl_en)
        print(f"  -> Lưu file: {file_en_name}")
        
        # 2. Sinh Cover Letter tiếng Việt
        print("  - Đang viết Cover Letter tiếng Việt...")
        cl_vi = await generate_cover_letter(cv_vi, job, "vi")
        file_vi_name = f"cover_letter_{job['company'].lower().split()[0]}_vi.txt"
        file_vi_path = os.path.join(PROJECT_ROOT, "resume", file_vi_name)
        with open(file_vi_path, "w", encoding="utf-8") as f:
            f.write(cl_vi)
        print(f"  -> Lưu file: {file_vi_name}")
        
        # 3. Ghi log lịch sử ứng tuyển
        log_application(job['company'], job['position'], "Đã chuẩn bị Cover Letter")
        print(f"  -> Ghi log ứng tuyển thành công.")
        
    print("\n" + "=" * 60)
    print("Hoàn thành quy trình tự động hóa! Các file đã sẵn sàng trong thư mục dự án.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
