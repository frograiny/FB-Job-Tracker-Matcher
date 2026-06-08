import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import subprocess
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from job_storage import JobDatabase
from pydantic import BaseModel
from fb_config import BASE_DIR, CV_PATH, CV_VI_PATH
from job_analyzer import match_with_cv
import json

class CvRequest(BaseModel):
    text: str


app = FastAPI(title="Facebook Job Tracker API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Global state for scraping
scrape_in_progress = False
scrape_log = []


def run_scraper_task():
    global scrape_in_progress, scrape_log
    scrape_in_progress = True
    scrape_log = ["--- Bắt đầu tiến trình quét tin Facebook ---"]
    try:
        # Use absolute paths so the dashboard can be started from any cwd.
        script_path = os.path.join(BASE_DIR, "src", "fb_job_bot.py")
        cmd = [sys.executable, script_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=BASE_DIR,
        )
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                scrape_log.append(clean_line)
                if len(scrape_log) > 500:
                    scrape_log.pop(0)

        process.wait()
        scrape_log.append("--- Quét tin thành công và cập nhật database ---")

    except Exception as e:
        scrape_log.append(f"Lỗi hệ thống: {str(e)}")
    finally:
        scrape_in_progress = False


@app.get("/")
def get_dashboard():
    """Serve the frontend dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


@app.get("/api/jobs")
def get_jobs(min_score: int = 0):
    try:
        with JobDatabase() as db:
            jobs = db.get_jobs(min_score=min_score, limit=999)
        return JSONResponse(content=jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    try:
        with JobDatabase() as db:
            stats = db.get_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    global scrape_in_progress
    if scrape_in_progress:
        return {"status": "running", "message": "Bot đang quét rồi!"}

    background_tasks.add_task(run_scraper_task)
    return {"status": "started", "message": "Bắt đầu quét tin Facebook ngầm..."}


@app.get("/api/scrape/status")
def get_scrape_status():
    global scrape_in_progress, scrape_log
    return {
        "in_progress": scrape_in_progress,
        "logs": scrape_log[-20:]  # Return last 20 lines of logs
    }


@app.get("/api/cv")
def get_cv():
    try:
        cv_text = ""
        if os.path.exists(CV_PATH):
            with open(CV_PATH, "r", encoding="utf-8") as f:
                cv_text = f.read()
        return JSONResponse({"text": cv_text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cv")
def update_cv(cv_req: CvRequest):
    try:
        cv_text = cv_req.text.strip()
        if not cv_text:
            raise HTTPException(status_code=400, detail="Nội dung CV trống")

        # Đảm bảo thư mục tồn tại
        for path in (CV_PATH, CV_VI_PATH):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(cv_text)

        # Tính toán lại điểm số
        with JobDatabase() as db:
            db.recalculate_keyword_scores(cv_text)

        return JSONResponse({"status": "success", "message": "Đã lưu CV và cập nhật lại điểm đối khớp!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/match")
async def match_job_with_ai(job_id: int):
    try:
        with JobDatabase() as db:
            # Lấy thông tin job hiện có
            cur = db._conn.execute("SELECT * FROM job_listings WHERE id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Không tìm thấy tin tuyển dụng")
            
            job = dict(row)
            # Parse requirements từ JSON string
            reqs = []
            if job.get("requirements"):
                try:
                    reqs = json.loads(job["requirements"])
                except Exception:
                    reqs = []
            
            job_info = {
                "company": job.get("company"),
                "position": job.get("position"),
                "requirements": reqs
            }
            
            # Đọc CV hiện tại
            cv_text = ""
            if os.path.exists(CV_PATH):
                with open(CV_PATH, "r", encoding="utf-8") as f:
                    cv_text = f.read()
            
            if not cv_text:
                raise HTTPException(status_code=400, detail="Vui lòng tải CV lên trước khi phân tích AI")
            
            # Gọi Gemini AI so khớp
            analysis = await match_with_cv(job_info, cv_text)
            
            # Cập nhật kết quả vào DB
            db.update_job_match(
                job_id=job_id,
                match_score=analysis.get("match_score", 0),
                matched_skills=analysis.get("matched_skills", []),
                missing_skills=analysis.get("missing_skills", []),
                recommendation=analysis.get("recommendation", "")
            )
            
            # Lấy lại job đã cập nhật để trả về cho frontend
            cur = db._conn.execute("SELECT * FROM job_listings WHERE id = ?", (job_id,))
            updated_row = cur.fetchone()
            updated_job = dict(updated_row)
            
            # Parse fields
            for field in ("requirements", "matched_skills", "missing_skills"):
                if updated_job.get(field):
                    try:
                        updated_job[field] = json.loads(updated_job[field])
                    except Exception:
                        pass
            
            return JSONResponse(content=updated_job)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
