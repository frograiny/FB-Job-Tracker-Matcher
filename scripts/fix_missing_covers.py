import asyncio
import os
import time
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig
from run_batch_applications import load_cv_content, generate_cover_letter, JOBS

load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CV_EN_PATH = os.path.join(BASE_DIR, "cv.txt")
CV_VI_PATH = os.path.join(BASE_DIR, "cv_vi.txt")

async def fix():
    cv_en = load_cv_content(CV_EN_PATH)
    cv_vi = load_cv_content(CV_VI_PATH)
    
    # 1. Sửa VinAI English
    print("Đang sửa VinAI English...")
    # Sleep 30s để giải phóng rate limit quota
    time.sleep(30)
    vinai_job = [j for j in JOBS if j["company"] == "VinAI"][0]
    cl_vinai_en = await generate_cover_letter(cv_en, vinai_job, "en")
    with open(os.path.join(BASE_DIR, "cover_letter_vinai_en.txt"), "w", encoding="utf-8") as f:
        f.write(cl_vinai_en)
    print("Đã sửa xong VinAI English!")

    # 2. Sửa VNG Vietnamese
    print("Đang sửa VNG Vietnamese...")
    # Sleep 30s để tránh dính tiếp
    time.sleep(30)
    vng_job = [j for j in JOBS if j["company"] == "VNG Corporation"][0]
    cl_vng_vi = await generate_cover_letter(cv_vi, vng_job, "vi")
    with open(os.path.join(BASE_DIR, "cover_letter_vng_vi.txt"), "w", encoding="utf-8") as f:
        f.write(cl_vng_vi)
    print("Đã sửa xong VNG Vietnamese!")

if __name__ == "__main__":
    asyncio.run(fix())
