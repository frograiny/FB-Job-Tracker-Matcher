import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import subprocess
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from job_storage import JobDatabase

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
        # Use sys.executable to work both locally (venv) and in Docker
        cmd = [sys.executable, "src/fb_job_bot.py"]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
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
