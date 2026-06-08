import csv
import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

from cv_profile import extract_cv_profile, score_text_against_profile, summarize_profile
from fb_config import BASE_DIR, CV_PATH
from job_storage import JobDatabase


TRACKER_PATH = os.getenv(
    "APPLICATION_TRACKER_PATH",
    os.path.join(BASE_DIR, "resume", "applications_tracker.csv"),
)


def load_cv() -> str:
    if not os.path.exists(CV_PATH):
        raise FileNotFoundError(f"CV not found: {CV_PATH}")
    with open(CV_PATH, "r", encoding="utf-8") as f:
        return f.read()


def job_to_text(job: dict) -> str:
    fields = [
        job.get("company", ""),
        job.get("position", ""),
        job.get("requirements", ""),
        job.get("work_type", ""),
        job.get("experience_level", ""),
        job.get("location", ""),
        job.get("recommendation", ""),
    ]
    return " ".join(str(field) for field in fields)


def rank_jobs_for_cv(jobs: list[dict], cv_text: str, min_score: int = 20) -> tuple[list[dict], object]:
    profile = extract_cv_profile(cv_text)
    ranked = []
    for job in jobs:
        profile_score = score_text_against_profile(job_to_text(job), profile)
        ai_score = int(job.get("match_score") or 0)
        final_score = max(profile_score, ai_score)
        if final_score >= min_score:
            ranked.append({**job, "profile_score": profile_score, "final_score": final_score})

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked, profile


def append_tracker_rows(jobs: list[dict], status: str):
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    file_exists = os.path.exists(TRACKER_PATH)
    with open(TRACKER_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Công ty", "Vị trí", "Trạng thái", "Match Score", "Profile Score", "Link"])
        for job in jobs:
            writer.writerow([
                job.get("company") or "Unknown",
                job.get("position") or "Unknown",
                status,
                job.get("match_score", 0),
                job.get("profile_score", 0),
                job.get("post_url", ""),
            ])


def log_cv_matched_jobs(limit: int = 10, min_score: int = 20):
    cv_text = load_cv()
    with JobDatabase() as db:
        jobs = db.get_jobs(min_score=0, limit=999)

    ranked_jobs, profile = rank_jobs_for_cv(jobs, cv_text, min_score=min_score)

    print("CV profile extracted:")
    print(summarize_profile(profile))

    if not jobs:
        print("\nNo scraped jobs found in the database yet.")
        print("Run the Facebook scraper first, or use these CV-based search queries:")
        for query in profile.search_queries:
            print(f"- {query}")
        return

    selected_jobs = ranked_jobs[:limit]
    if not selected_jobs:
        print("\nNo database jobs matched this CV strongly enough.")
        print("Suggested CV-based Facebook search queries:")
        for query in profile.search_queries:
            print(f"- {query}")
        return

    append_tracker_rows(selected_jobs, "CV matched - ready to review")
    print(f"\nLogged {len(selected_jobs)} CV-matched jobs to: {TRACKER_PATH}")
    for job in selected_jobs:
        print(
            f"- {job.get('company') or 'Unknown'} | {job.get('position') or 'Unknown'} "
            f"(final={job['final_score']}, profile={job['profile_score']}, ai={job.get('match_score', 0)})"
        )


if __name__ == "__main__":
    log_cv_matched_jobs()
