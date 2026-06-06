"""
SQLite Storage & Reporting cho Facebook Job Scraper.

Lưu trữ:
- Bài viết đã scrape (tránh đọc lại)
- Tin tuyển dụng đã phân tích
- Kết quả matching CV

Xuất báo cáo: CSV, Markdown
"""
import csv
import logging
import os
import sqlite3
import json
import time
from typing import Optional

from fb_config import DATABASE_PATH, REPORT_DIR

logger = logging.getLogger(__name__)


# ============================================================
# Database Schema
# ============================================================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT UNIQUE NOT NULL,
    text TEXT NOT NULL,
    author TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    group_url TEXT DEFAULT '',
    post_url TEXT DEFAULT '',
    scraped_at TEXT NOT NULL,
    is_job_posting INTEGER DEFAULT 0,
    analyzed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS job_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_hash TEXT NOT NULL,
    company TEXT,
    position TEXT,
    requirements TEXT,
    salary TEXT,
    location TEXT,
    contact TEXT,
    deadline TEXT,
    work_type TEXT,
    experience_level TEXT,
    match_score INTEGER DEFAULT 0,
    matched_skills TEXT,
    missing_skills TEXT,
    recommendation TEXT,
    classification_confidence REAL DEFAULT 0.0,
    group_url TEXT DEFAULT '',
    post_url TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (post_hash) REFERENCES raw_posts(content_hash)
);

CREATE INDEX IF NOT EXISTS idx_posts_hash ON raw_posts(content_hash);
CREATE INDEX IF NOT EXISTS idx_posts_analyzed ON raw_posts(analyzed);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON job_listings(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON job_listings(created_at DESC);
"""


class JobDatabase:
    """SQLite database manager cho job scraper."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Mở connection và tạo bảng nếu chưa có."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        logger.info(f"Kết nối database: {self.db_path}")

    def close(self):
        """Đóng connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ============================================================
    # Raw Posts
    # ============================================================
    def post_exists(self, content_hash: str) -> bool:
        """Kiểm tra bài viết đã tồn tại trong DB chưa (tránh trùng)."""
        cur = self._conn.execute(
            "SELECT 1 FROM raw_posts WHERE content_hash = ?", (content_hash,)
        )
        return cur.fetchone() is not None

    def save_post(self, post: dict) -> bool:
        """
        Lưu bài viết mới vào database.
        
        Args:
            post: Dict từ fb_scraper.make_post()
            
        Returns:
            True nếu lưu thành công, False nếu đã tồn tại.
        """
        if self.post_exists(post["content_hash"]):
            return False

        self._conn.execute(
            """INSERT INTO raw_posts 
               (content_hash, text, author, timestamp, group_url, post_url, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                post["content_hash"],
                post["text"],
                post.get("author", ""),
                post.get("timestamp", ""),
                post.get("group_url", ""),
                post.get("post_url", ""),
                post.get("scraped_at", time.strftime("%Y-%m-%d %H:%M:%S")),
            ),
        )
        self._conn.commit()
        return True

    def save_posts_batch(self, posts: list[dict]) -> int:
        """Lưu nhiều bài viết, trả về số bài mới."""
        new_count = 0
        for post in posts:
            if self.save_post(post):
                new_count += 1
        return new_count

    def mark_post_analyzed(self, content_hash: str, is_job: bool):
        """Đánh dấu bài viết đã được phân tích."""
        self._conn.execute(
            "UPDATE raw_posts SET analyzed = 1, is_job_posting = ? WHERE content_hash = ?",
            (1 if is_job else 0, content_hash),
        )
        self._conn.commit()

    def get_unanalyzed_posts(self) -> list[dict]:
        """Lấy danh sách bài chưa được phân tích."""
        cur = self._conn.execute(
            "SELECT * FROM raw_posts WHERE analyzed = 0 ORDER BY scraped_at DESC"
        )
        return [dict(row) for row in cur.fetchall()]

    # ============================================================
    # Job Listings
    # ============================================================
    def save_job(self, post_hash: str, analysis: dict, group_url: str = "", post_url: str = ""):
        """
        Lưu tin tuyển dụng đã phân tích.
        
        Args:
            post_hash: Hash bài viết gốc
            analysis: Kết quả từ job_analyzer.analyze_post()
            group_url: URL nhóm gốc
            post_url: URL bài viết gốc
        """
        job_info = analysis.get("job_info", {})
        cv_match = analysis.get("cv_match", {})
        classification = analysis.get("classification", {})

        # Convert list thành JSON string
        requirements = json.dumps(job_info.get("requirements", []), ensure_ascii=False)
        matched_skills = json.dumps(cv_match.get("matched_skills", []), ensure_ascii=False)
        missing_skills = json.dumps(cv_match.get("missing_skills", []), ensure_ascii=False)

        self._conn.execute(
            """INSERT OR IGNORE INTO job_listings 
               (post_hash, company, position, requirements, salary, location,
                contact, deadline, work_type, experience_level,
                match_score, matched_skills, missing_skills, recommendation,
                classification_confidence, group_url, post_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_hash,
                job_info.get("company"),
                job_info.get("position"),
                requirements,
                job_info.get("salary"),
                job_info.get("location"),
                job_info.get("contact"),
                job_info.get("deadline"),
                job_info.get("work_type"),
                job_info.get("experience_level"),
                cv_match.get("match_score", 0),
                matched_skills,
                missing_skills,
                cv_match.get("recommendation"),
                classification.get("confidence", 0.0),
                group_url,
                post_url,
                time.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        self._conn.commit()

    def recalculate_keyword_scores(self, cv_text: str):
        """
        Tính toán lại điểm match_score và các kỹ năng phù hợp/thiếu cho toàn bộ job hiện có dựa trên từ khóa CV mới.
        """
        if not cv_text:
            return

        cv_lower = cv_text.lower()
        
        # Danh sách kỹ năng IT tiêu chuẩn dùng để đối khớp từ khóa
        skills_dict = [
            "python", "fastapi", "flask", "django", "pytorch", "tensorflow", "keras", "scikit-learn", 
            "opencv", "react", "vue", "angular", "nodejs", "javascript", "typescript", "golang", "go",
            "c++", "c#", ".net", "java", "sql", "mysql", "postgresql", "mongodb", "docker", "docker compose", 
            "kubernetes", "git", "github", "linux", "deep learning", "machine learning", "artificial intelligence", 
            "ai agent", "llm", "nlp", "computer vision", "rest api", "waf", "security", "devops", "cloud", "aws"
        ]

        # Lấy tất cả job hiện có
        cur = self._conn.execute("SELECT id, requirements, match_score FROM job_listings")
        rows = cur.fetchall()

        for row in rows:
            job_id = row[0]
            reqs_str = row[1]
            original_score = row[2] or 0

            # Parse requirements
            reqs = []
            if reqs_str:
                try:
                    reqs = json.loads(reqs_str)
                except Exception:
                    reqs = []

            if not reqs:
                continue

            # Nối các yêu cầu lại thành 1 chuỗi để tìm kiếm kỹ năng
            req_text = " ".join(reqs).lower()
            job_skills = [s for s in skills_dict if s in req_text]

            if not job_skills:
                continue

            # Kiểm tra kỹ năng nào khớp trong CV
            matched_skills = [s for s in job_skills if s in cv_lower]
            missing_skills = [s for s in job_skills if s not in cv_lower]

            ratio = len(matched_skills) / len(job_skills)
            computed_score = round(ratio * 100)

            # Pha trộn 70% điểm tính toán từ khóa + 30% điểm gốc
            new_score = min(100, round(computed_score * 0.7 + original_score * 0.3))

            # Lưu lại vào DB
            self._conn.execute(
                """UPDATE job_listings
                   SET match_score = ?, matched_skills = ?, missing_skills = ?
                   WHERE id = ?""",
                (
                    new_score,
                    json.dumps(matched_skills, ensure_ascii=False),
                    json.dumps(missing_skills, ensure_ascii=False),
                    job_id
                )
            )
        self._conn.commit()

    def update_job_match(self, job_id: int, match_score: int, matched_skills: list, missing_skills: list, recommendation: str):
        """Cập nhật chi tiết kết quả so khớp của AI cho một công việc cụ thể."""
        self._conn.execute(
            """UPDATE job_listings
               SET match_score = ?, matched_skills = ?, missing_skills = ?, recommendation = ?
               WHERE id = ?""",
            (
                match_score,
                json.dumps(matched_skills, ensure_ascii=False),
                json.dumps(missing_skills, ensure_ascii=False),
                recommendation,
                job_id
            )
        )
        self._conn.commit()

    def get_jobs(self, min_score: int = 0, limit: int = 50) -> list[dict]:
        """Lấy danh sách job, sắp xếp theo match_score giảm dần."""
        cur = self._conn.execute(
            """SELECT * FROM job_listings 
               WHERE match_score >= ?
               ORDER BY match_score DESC, created_at DESC
               LIMIT ?""",
            (min_score, limit),
        )
        rows = [dict(row) for row in cur.fetchall()]

        # Parse JSON strings trở lại list
        for row in rows:
            for field in ("requirements", "matched_skills", "missing_skills"):
                if row.get(field):
                    try:
                        row[field] = json.loads(row[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
        return rows

    def get_new_jobs(self, since_hours: int = 24) -> list[dict]:
        """Lấy job mới trong N giờ gần nhất."""
        since_time = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(time.time() - since_hours * 3600),
        )
        cur = self._conn.execute(
            """SELECT * FROM job_listings 
               WHERE created_at >= ?
               ORDER BY match_score DESC""",
            (since_time,),
        )
        rows = [dict(row) for row in cur.fetchall()]
        for row in rows:
            for field in ("requirements", "matched_skills", "missing_skills"):
                if row.get(field):
                    try:
                        row[field] = json.loads(row[field])
                    except (json.JSONDecodeError, TypeError):
                        pass
        return rows

    def get_stats(self) -> dict:
        """Lấy thống kê tổng quan."""
        total_posts = self._conn.execute("SELECT COUNT(*) FROM raw_posts").fetchone()[0]
        analyzed = self._conn.execute("SELECT COUNT(*) FROM raw_posts WHERE analyzed = 1").fetchone()[0]
        job_posts = self._conn.execute("SELECT COUNT(*) FROM raw_posts WHERE is_job_posting = 1").fetchone()[0]
        total_jobs = self._conn.execute("SELECT COUNT(*) FROM job_listings").fetchone()[0]
        avg_score = self._conn.execute("SELECT AVG(match_score) FROM job_listings").fetchone()[0] or 0

        return {
            "total_posts_scraped": total_posts,
            "posts_analyzed": analyzed,
            "job_posts_found": job_posts,
            "total_job_listings": total_jobs,
            "average_match_score": round(avg_score, 1),
        }

    # ============================================================
    # Export Reports
    # ============================================================
    def export_csv(self, filepath: str = None, min_score: int = 0) -> str:
        """Xuất báo cáo CSV."""
        if not filepath:
            filepath = os.path.join(REPORT_DIR, f"job_report_{time.strftime('%Y%m%d_%H%M%S')}.csv")

        jobs = self.get_jobs(min_score=min_score, limit=999)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Công ty", "Vị trí", "Lương", "Địa điểm", "Loại",
                "Level", "Hạn nộp", "Liên hệ", "Match Score (%)",
                "Skills phù hợp", "Skills thiếu", "Nhận xét",
                "Nhóm FB", "Link bài viết"
            ])

            for job in jobs:
                matched = ", ".join(job.get("matched_skills", [])) if isinstance(job.get("matched_skills"), list) else str(job.get("matched_skills", ""))
                missing = ", ".join(job.get("missing_skills", [])) if isinstance(job.get("missing_skills"), list) else str(job.get("missing_skills", ""))

                writer.writerow([
                    job.get("company", ""),
                    job.get("position", ""),
                    job.get("salary", ""),
                    job.get("location", ""),
                    job.get("work_type", ""),
                    job.get("experience_level", ""),
                    job.get("deadline", ""),
                    job.get("contact", ""),
                    job.get("match_score", 0),
                    matched,
                    missing,
                    job.get("recommendation", ""),
                    job.get("group_url", ""),
                    job.get("post_url", ""),
                ])

        logger.info(f"Đã xuất báo cáo CSV: {filepath}")
        return filepath

    def export_markdown(self, filepath: str = None, min_score: int = 0) -> str:
        """Xuất báo cáo Markdown đẹp."""
        if not filepath:
            filepath = os.path.join(REPORT_DIR, f"job_report_{time.strftime('%Y%m%d_%H%M%S')}.md")

        jobs = self.get_jobs(min_score=min_score, limit=999)
        stats = self.get_stats()

        lines = [
            f"# 📋 Báo Cáo Tuyển Dụng Facebook",
            f"",
            f"**Ngày quét:** {time.strftime('%d/%m/%Y %H:%M')}",
            f"",
            f"## 📊 Thống kê",
            f"- Tổng bài viết đã quét: **{stats['total_posts_scraped']}**",
            f"- Bài đã phân tích: **{stats['posts_analyzed']}**",
            f"- Tin tuyển dụng tìm thấy: **{stats['job_posts_found']}**",
            f"- Điểm phù hợp trung bình: **{stats['average_match_score']}%**",
            f"",
            f"---",
            f"",
        ]

        if not jobs:
            lines.append("_Không tìm thấy tin tuyển dụng nào._")
        else:
            for i, job in enumerate(jobs, 1):
                score = job.get("match_score", 0)
                # Emoji dựa trên score
                if score >= 70:
                    emoji = "🟢"
                elif score >= 40:
                    emoji = "🟡"
                else:
                    emoji = "🔴"

                matched = job.get("matched_skills", [])
                missing = job.get("missing_skills", [])
                if isinstance(matched, str):
                    matched = [matched]
                if isinstance(missing, str):
                    missing = [missing]

                lines.extend([
                    f"## {emoji} {i}. {job.get('company', 'N/A')} — {job.get('position', 'N/A')}",
                    f"",
                    f"| Thông tin | Chi tiết |",
                    f"|-----------|----------|",
                    f"| **Lương** | {job.get('salary', 'Không rõ')} |",
                    f"| **Địa điểm** | {job.get('location', 'Không rõ')} |",
                    f"| **Loại** | {job.get('work_type', 'Không rõ')} |",
                    f"| **Level** | {job.get('experience_level', 'Không rõ')} |",
                    f"| **Hạn nộp** | {job.get('deadline', 'Không rõ')} |",
                    f"| **Liên hệ** | {job.get('contact', 'Không rõ')} |",
                    f"| **Match Score** | **{score}%** {emoji} |",
                    f"",
                ])

                if matched:
                    lines.append(f"**✅ Skills phù hợp:** {', '.join(matched)}")
                if missing:
                    lines.append(f"**❌ Skills thiếu:** {', '.join(missing)}")

                rec = job.get("recommendation", "")
                if rec:
                    lines.append(f"")
                    lines.append(f"> 💡 {rec}")

                post_url = job.get("post_url", "")
                if post_url:
                    lines.append(f"")
                    lines.append(f"🔗 [Xem bài viết gốc]({post_url})")

                lines.extend(["", "---", ""])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Đã xuất báo cáo Markdown: {filepath}")
        return filepath

    def export_html(self, filepath: str = None, min_score: int = 0) -> str:
        """Xuất báo cáo HTML tĩnh tương tác tuyệt đẹp với chức năng tải CV và phân tích động."""
        if not filepath:
            filepath = os.path.join(REPORT_DIR, "job_dashboard.html")

        jobs = self.get_jobs(min_score=min_score, limit=999)
        stats = self.get_stats()
        
        # Tạo chuỗi JSON an toàn cho HTML
        jobs_json = json.dumps(jobs, ensure_ascii=False)
        stats_json = json.dumps(stats, ensure_ascii=False)

        html_template = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FB Job Tracker & CV Matcher</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- FontAwesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- PDF.js for client-side PDF parsing -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
    </script>
    
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-secondary: #111726;
            --bg-card: #151d30;
            --bg-card-hover: #1b263e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #2563eb;
            --accent-hover: #3b82f6;
            --accent-glow: rgba(37, 99, 235, 0.25);
            --border: rgba(255, 255, 255, 0.06);
            --border-hover: rgba(255, 255, 255, 0.12);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --glow-green: rgba(16, 185, 129, 0.12);
            --glow-yellow: rgba(245, 158, 11, 0.12);
            --glow-red: rgba(239, 68, 68, 0.12);
            --font-display: 'Outfit', sans-serif;
            --font-body: 'Inter', sans-serif;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
            --shadow-md: 0 8px 24px rgba(0,0,0,0.3);
            --radius-lg: 16px;
            --radius-md: 12px;
        }

        .light-mode {
            --bg-primary: #f1f5f9;
            --bg-secondary: #ffffff;
            --bg-card: #f8fafc;
            --bg-card-hover: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --accent: #1d4ed8;
            --accent-hover: #2563eb;
            --accent-glow: rgba(29, 78, 216, 0.15);
            --border: #e2e8f0;
            --border-hover: #cbd5e1;
            --success: #059669;
            --warning: #d97706;
            --danger: #dc2626;
            --glow-green: rgba(5, 150, 105, 0.08);
            --glow-yellow: rgba(217, 119, 6, 0.08);
            --glow-red: rgba(220, 38, 38, 0.08);
            --shadow-sm: 0 2px 8px rgba(148, 163, 184, 0.1);
            --shadow-md: 0 8px 24px rgba(148, 163, 184, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            transition: background-color 0.2s ease, border-color 0.2s ease, color 0.15s ease;
        }

        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-body);
            padding-bottom: 30px;
            overflow-x: hidden;
        }

        .container {
            max-width: 1550px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Top Bar Navigation */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding: 18px 24px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-sm);
        }

        .logo-section h1 {
            font-family: var(--font-display);
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, var(--text-primary) 30%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-section p {
            color: var(--text-secondary);
            font-size: 0.88rem;
            margin-top: 3px;
        }

        .actions-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .btn {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 10px 16px;
            border-radius: var(--radius-md);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-weight: 600;
            font-family: var(--font-body);
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }

        .btn:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-1px);
        }

        .btn-primary {
            background: var(--accent);
            color: #ffffff;
            border: none;
            box-shadow: 0 4px 12px var(--accent-glow);
        }

        .btn-primary:hover {
            background: var(--accent-hover);
            box-shadow: 0 6px 18px var(--accent-glow);
            color: #ffffff;
        }

        /* 3-Column Layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 340px 420px 1fr;
            gap: 20px;
            height: calc(100vh - 150px);
            min-height: 700px;
        }

        @media (max-width: 1280px) {
            .dashboard-grid {
                grid-template-columns: 320px 1fr;
                height: auto;
            }
            .job-details-view {
                grid-column: span 2;
                position: static !important;
            }
        }

        @media (max-width: 800px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
                height: auto;
            }
            .job-details-view {
                grid-column: span 1;
            }
        }

        .panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }

        .panel-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-title {
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .panel-body {
            padding: 20px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        /* Custom Scrollbar */
        .panel-body::-webkit-scrollbar {
            width: 5px;
        }
        .panel-body::-webkit-scrollbar-track {
            background: transparent;
        }
        .panel-body::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        .panel-body::-webkit-scrollbar-thumb:hover {
            background: var(--border-hover);
        }

        /* Stats in Sidebar */
        .sidebar-stats {
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
        }

        .stat-item {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 14px 18px;
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .stat-item-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 500;
        }

        .stat-item-val {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
        }

        /* CV Upload Area */
        .cv-upload-box {
            border: 2px dashed var(--border-hover);
            border-radius: var(--radius-md);
            padding: 24px 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            background: var(--bg-primary);
        }

        .cv-upload-box:hover {
            border-color: var(--accent);
            background: var(--bg-card-hover);
        }

        .cv-upload-box i {
            font-size: 2.2rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }

        .cv-text-preview {
            width: 100%;
            height: 120px;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            border-radius: var(--radius-md);
            padding: 12px;
            font-family: var(--font-body);
            font-size: 0.85rem;
            resize: none;
            outline: none;
        }

        .cv-text-preview:focus {
            border-color: var(--accent);
        }

        /* Job Cards Column */
        .jobs-list-panel {
            gap: 12px;
            padding: 16px !important;
        }

        .job-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            gap: 10px;
            transition: all 0.2s ease;
            position: relative;
        }

        .job-card:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-1px);
        }

        .job-card.active {
            background: var(--bg-card-hover);
            border-color: var(--accent);
            box-shadow: 0 4px 16px var(--accent-glow);
        }

        .job-card-title {
            font-family: var(--font-display);
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.35;
        }

        .job-card-company {
            font-size: 0.88rem;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .job-card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            font-size: 0.78rem;
            color: var(--text-secondary);
        }

        .job-card-meta span {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .job-card-meta i {
            color: var(--accent);
        }

        .badge-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 4px;
        }

        .score-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 0.8rem;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .score-badge.high { background: var(--glow-green); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.25); }
        .score-badge.mid { background: var(--glow-yellow); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.25); }
        .score-badge.low { background: var(--glow-red); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.25); }

        .new-match-indicator {
            font-size: 0.7rem;
            background: var(--accent-glow);
            color: var(--accent);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }

        /* Right Column: Detailed View */
        .job-details-view {
            padding: 30px;
            overflow-y: auto;
            position: relative;
        }

        .empty-details {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-secondary);
            gap: 15px;
            text-align: center;
            padding: 40px;
        }

        .empty-details i {
            font-size: 3rem;
            opacity: 0.3;
        }

        .details-title-section {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }

        .details-title-section h2 {
            font-family: var(--font-display);
            font-size: 1.6rem;
            font-weight: 800;
            margin-bottom: 6px;
        }

        .details-meta-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            background: var(--bg-primary);
            padding: 18px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }

        .details-meta-item {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .details-meta-icon {
            width: 38px;
            height: 38px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--accent);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }

        .details-meta-text h4 {
            font-size: 0.72rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .details-meta-text p {
            font-size: 0.92rem;
            font-weight: 600;
        }

        .details-body {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .details-section-title {
            font-family: var(--font-display);
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .details-section-title i {
            color: var(--accent);
        }

        .skills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .skill-tag {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid transparent;
        }

        .skill-tag.matched {
            background: rgba(16, 185, 129, 0.08);
            color: var(--success);
            border-color: rgba(16, 185, 129, 0.2);
        }

        .skill-tag.missing {
            background: rgba(239, 68, 68, 0.08);
            color: var(--danger);
            border-color: rgba(239, 68, 68, 0.2);
        }

        .ai-box {
            background: var(--accent-glow);
            border-left: 4px solid var(--accent);
            padding: 20px;
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            font-size: 0.92rem;
            line-height: 1.6;
        }

        /* Config Modal / Key input */
        .api-key-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 16px;
            border-radius: var(--radius-md);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* Form styling */
        label {
            font-size: 0.82rem;
            color: var(--text-secondary);
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Navigation Header -->
        <header>
            <div class="logo-section">
                <h1><i class="fa-brands fa-facebook"></i> FB Job Tracker & Matcher</h1>
                <p>Hệ thống lọc tin tuyển dụng và đối khớp CV thời gian thực</p>
            </div>
            <div class="actions-section">
                <button class="btn btn-primary" id="scrape-btn">
                    <i class="fa-solid fa-arrows-rotate"></i> <span>Quét tin Facebook mới</span>
                </button>
                <button class="btn" id="theme-btn">
                    <i class="fa-solid fa-moon"></i> <span>Giao diện</span>
                </button>
            </div>
        </header>

        <!-- Dashboard Layout Grid -->
        <div class="dashboard-grid">
            
            <!-- Column 1: CV Management & Filters -->
            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fa-solid fa-address-card"></i> Hồ sơ & Bộ lọc</span>
                </div>
                <div class="panel-body">
                    <!-- Statistics summary -->
                    <div class="sidebar-stats">
                        <div class="stat-item">
                            <span class="stat-item-label">Tổng bài viết</span>
                            <span class="stat-item-val" id="stat-scraped">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-item-label">Đã tìm thấy job</span>
                            <span class="stat-item-val" id="stat-jobs">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-item-label">Match score trung bình</span>
                            <span class="stat-item-val" id="stat-match">0%</span>
                        </div>
                    </div>

                    <!-- Upload CV section -->
                    <div class="filter-group">
                        <label>Tải CV của bạn lên để chấm điểm lại</label>
                        <div class="cv-upload-box" id="upload-box">
                            <i class="fa-solid fa-cloud-arrow-up"></i>
                            <p style="font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;">Tải lên CV (.pdf, .txt)</p>
                            <p style="font-size: 0.75rem; color: var(--text-secondary);">Click hoặc kéo thả file vào đây</p>
                            <input type="file" id="file-input" accept=".txt,.pdf" style="display: none;">
                        </div>
                    </div>

                    <!-- Paste CV text area -->
                    <div class="filter-group">
                        <label for="cv-textarea">Nội dung văn bản CV</label>
                        <textarea id="cv-textarea" class="cv-text-preview" placeholder="Dán nội dung CV tiếng Việt hoặc tiếng Anh của bạn tại đây để đối khớp tự động..."></textarea>
                    </div>

                    <!-- Text Keyword search -->
                    <div class="filter-group">
                        <label for="search-input">Tìm kiếm nhanh</label>
                        <input type="text" id="search-input" class="input-control" placeholder="Công ty, vị trí, kỹ năng...">
                    </div>

                    <!-- Match score slider -->
                    <div class="filter-group">
                        <label for="min-score-range">Match Score tối thiểu: <span id="score-val" style="color:var(--accent); font-weight:700;">0%</span></label>
                        <input type="range" id="min-score-range" class="input-control" min="0" max="100" value="0">
                    </div>

                    <!-- Level Select dropdown -->
                    <div class="filter-group">
                        <label for="level-select">Cấp bậc (Level)</label>
                        <select id="level-select" class="input-control">
                            <option value="">Tất cả</option>
                            <option value="intern">Intern / Thực tập</option>
                            <option value="fresher">Fresher</option>
                            <option value="junior">Junior</option>
                            <option value="mid">Mid-level</option>
                        </select>
                    </div>

                    <!-- Scrape status log console -->
                    <div id="scrape-status-container" style="display: none; background: rgba(37, 99, 235, 0.08); border: 1px solid var(--accent); padding: 12px; border-radius: var(--radius-md);">
                        <label style="color: var(--accent);"><i class="fa-solid fa-circle-notch fa-spin"></i> Tiến trình quét tin...</label>
                        <div id="scrape-log-console" style="font-family: monospace; font-size: 0.72rem; line-height: 1.4; color: var(--text-secondary); max-height: 120px; overflow-y: auto; margin-top: 6px; white-space: pre-wrap;">
                        </div>
                    </div>

                    <!-- Gemini API Key panel -->
                    <div class="api-key-section">
                        <label for="api-key-input"><i class="fa-solid fa-key"></i> Gemini API Key (Không bắt buộc)</label>
                        <input type="password" id="api-key-input" class="input-control" placeholder="Nhập để chấm điểm AI trực tiếp...">
                        <p style="font-size: 0.7rem; color: var(--text-secondary); line-height: 1.3;">
                            Key được lưu cục bộ ở trình duyệt của bạn (localStorage), dùng để phân tích tin tuyển dụng trực tiếp bằng AI.
                        </p>
                    </div>
                </div>
            </div>

            <!-- Column 2: Job Cards list -->
            <div class="panel">
                <div class="panel-header">
                    <span class="panel-title"><i class="fa-solid fa-briefcase"></i> Tin tuyển dụng</span>
                    <span class="stat-item-label" id="jobs-count">0 tin</span>
                </div>
                <div class="panel-body jobs-list-panel" id="jobs-list">
                    <!-- Cards will be dynamically rendered -->
                </div>
            </div>

            <!-- Column 3: Detailed Job Description -->
            <div class="panel job-details-view" id="job-details">
                <div class="empty-details">
                    <i class="fa-solid fa-briefcase"></i>
                    <h3>Vui lòng chọn một công việc bên danh sách để xem chi tiết</h3>
                    <p>Bộ đối khớp CV sẽ tự động tính điểm dựa trên hồ sơ của bạn</p>
                </div>
            </div>

        </div>
    </div>

    <!-- Embedded data -->
    <script>
        const JOBS_DATA = __JOBS_JSON__;
        const STATS_DATA = __STATS_JSON__;
    </script>

    <script>
        // DOM Nodes
        const themeBtn = document.getElementById('theme-btn');
        const uploadBox = document.getElementById('upload-box');
        const fileInput = document.getElementById('file-input');
        const cvTextarea = document.getElementById('cv-textarea');
        const searchInput = document.getElementById('search-input');
        const minScoreRange = document.getElementById('min-score-range');
        const scoreVal = document.getElementById('score-val');
        const levelSelect = document.getElementById('level-select');
        const apiKeyInput = document.getElementById('api-key-input');
        const jobsList = document.getElementById('jobs-list');
        const jobDetails = document.getElementById('job-details');
        const scrapeBtn = document.getElementById('scrape-btn');
        const scrapeStatusContainer = document.getElementById('scrape-status-container');
        const scrapeLogConsole = document.getElementById('scrape-log-console');

        // State variables
        let jobs = [...JOBS_DATA];
        let activeJobId = null;
        let userCvText = "";

        // Standard IT Skills Dictionary for client-side semantic matching
        const SKILLS_DICT = [
            "python", "fastapi", "flask", "django", "pytorch", "tensorflow", "keras", "scikit-learn", 
            "opencv", "react", "vue", "angular", "nodejs", "javascript", "typescript", "golang", "go",
            "c++", "c#", ".net", "java", "sql", "mysql", "postgresql", "mongodb", "docker", "docker compose", 
            "kubernetes", "git", "github", "linux", "deep learning", "machine learning", "artificial intelligence", 
            "ai agent", "llm", "nlp", "computer vision", "rest api", "waf", "security", "devops", "cloud", "aws"
        ];

        // Init Page
        document.addEventListener('DOMContentLoaded', () => {
            // Load stats
            document.getElementById('stat-scraped').textContent = STATS_DATA.total_posts_scraped || 0;
            document.getElementById('stat-jobs').textContent = STATS_DATA.job_posts_found || 0;
            document.getElementById('stat-match').textContent = (STATS_DATA.average_match_score || 0) + '%';

            // Load saved configurations from LocalStorage
            const savedApiKey = localStorage.getItem('fb_bot_gemini_key');
            if (savedApiKey) apiKeyInput.value = savedApiKey;

            const savedCv = localStorage.getItem('user_cv_text');
            if (savedCv) {
                cvTextarea.value = savedCv;
                userCvText = savedCv;
                recalculateAllScores(savedCv);
            }

            // Bind Event Listeners
            themeBtn.addEventListener('click', toggleTheme);
            
            uploadBox.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', handleFileUpload);

            // Drag and drop event listeners
            uploadBox.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadBox.style.borderColor = 'var(--accent)';
                uploadBox.style.background = 'var(--bg-card-hover)';
            });

            uploadBox.addEventListener('dragleave', () => {
                uploadBox.style.borderColor = 'var(--border-hover)';
                uploadBox.style.background = 'var(--bg-primary)';
            });

            uploadBox.addEventListener('drop', async (e) => {
                e.preventDefault();
                uploadBox.style.borderColor = 'var(--border-hover)';
                uploadBox.style.background = 'var(--bg-primary)';
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    fileInput.files = files;
                    const event = new Event('change');
                    fileInput.dispatchEvent(event);
                }
            });
            cvTextarea.addEventListener('input', (e) => {
                const text = e.target.value;
                userCvText = text;
                localStorage.setItem('user_cv_text', text);
                recalculateAllScores(text);
                applyFilters();
            });

            searchInput.addEventListener('input', applyFilters);
            minScoreRange.addEventListener('input', (e) => {
                scoreVal.textContent = e.target.value + '%';
                applyFilters();
            });
            levelSelect.addEventListener('change', applyFilters);
            apiKeyInput.addEventListener('input', (e) => {
                localStorage.setItem('fb_bot_gemini_key', e.target.value);
            });

            scrapeBtn.addEventListener('click', triggerScrape);

            // Fetch live API data if running on backend
            if (isHosted) {
                fetchJobsFromApi();
                fetchStatsFromApi();
                checkScrapeStatus();
            } else {
                applyFilters();
            }
        });

        // Check if hosted on web server
        const isHosted = window.location.protocol.startsWith('http');

        async function fetchJobsFromApi() {
            if (!isHosted) return;
            try {
                const res = await fetch('/api/jobs');
                if (res.ok) {
                    const data = await res.json();
                    jobs = data.map(job => {
                        const newScore = calculateKeywordScore(job, userCvText);
                        return {
                            ...job,
                            match_score: newScore,
                            is_recalculated: userCvText.trim().length > 0
                        };
                    });
                    jobs.sort((a, b) => b.match_score - a.match_score);
                    applyFilters();
                }
            } catch (e) {
                console.error("Lỗi lấy dữ liệu job từ API:", e);
            }
        }

        async function fetchStatsFromApi() {
            if (!isHosted) return;
            try {
                const res = await fetch('/api/stats');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('stat-scraped').textContent = data.total_posts_scraped || 0;
                    document.getElementById('stat-jobs').textContent = data.job_posts_found || 0;
                    document.getElementById('stat-match').textContent = (data.average_match_score || 0) + '%';
                }
            } catch (e) {
                console.error("Lỗi lấy dữ liệu stats từ API:", e);
            }
        }

        async function checkScrapeStatus() {
            if (!isHosted) return;
            try {
                const res = await fetch('/api/scrape/status');
                if (res.ok) {
                    const data = await res.json();
                    if (data.in_progress) {
                        scrapeBtn.disabled = true;
                        scrapeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang quét tin...';
                        scrapeStatusContainer.style.display = 'block';
                        scrapeLogConsole.textContent = data.logs.join('\\n');
                        scrapeLogConsole.scrollTop = scrapeLogConsole.scrollHeight; // Auto scroll
                        
                        setTimeout(checkScrapeStatus, 2000);
                    } else {
                        if (scrapeBtn.disabled) {
                            scrapeBtn.disabled = false;
                            scrapeBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Quét tin Facebook mới';
                            scrapeStatusContainer.style.display = 'none';
                            alert("Tiến trình quét Facebook hoàn tất!");
                            fetchJobsFromApi();
                            fetchStatsFromApi();
                        }
                    }
                }
            } catch (e) {
                console.error("Lỗi kiểm tra trạng thái quét:", e);
            }
        }

        async function triggerScrape() {
            if (!isHosted) {
                alert("Nút này chỉ hoạt động khi bạn chạy Web server (app.py)!");
                return;
            }
            try {
                const res = await fetch('/api/scrape', { method: 'POST' });
                if (res.ok) {
                    checkScrapeStatus();
                }
            } catch (e) {
                alert("Lỗi khi kết nối đến server: " + e.message);
            }
        }

        // Theme Toggle
        function toggleTheme() {
            document.body.classList.toggle('light-mode');
            const icon = themeBtn.querySelector('i');
            if (document.body.classList.contains('light-mode')) {
                icon.className = 'fa-solid fa-sun';
            } else {
                icon.className = 'fa-solid fa-moon';
            }
        }

        // File upload utility
        async function handleFileUpload(e) {
            const file = e.target.files[0];
            if (!file) return;

            let text = "";
            if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
                try {
                    cvTextarea.value = "Đang đọc nội dung file PDF...";
                    text = await extractTextFromPdf(file);
                } catch (err) {
                    console.error("Lỗi đọc PDF:", err);
                    alert("Không thể đọc tệp PDF này. Hãy thử dán trực tiếp.");
                    cvTextarea.value = userCvText;
                    return;
                }
            } else {
                text = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (evt) => resolve(evt.target.result);
                    reader.readAsText(file, "UTF-8");
                });
            }

            cvTextarea.value = text;
            userCvText = text;
            localStorage.setItem('user_cv_text', text);
            recalculateAllScores(text);
            applyFilters();
        }

        async function extractTextFromPdf(file) {
            const arrayBuffer = await file.arrayBuffer();
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            let fullText = "";
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(" ");
                fullText += pageText + "\\n";
            }
            return fullText;
        }

        // Fast keyword-based client-side score matching
        function calculateKeywordScore(job, cvText) {
            if (!cvText) return job.match_score; // fallback to DB score if CV is empty

            const cvLower = cvText.toLowerCase();
            const reqs = typeof job.requirements === 'string' ? JSON.parse(job.requirements) : (job.requirements || []);
            
            if (reqs.length === 0) return job.match_score;

            // Find tech skills mentioned in requirements
            const reqText = reqs.join(" ").toLowerCase();
            const jobSkills = SKILLS_DICT.filter(skill => reqText.includes(skill));

            if (jobSkills.length === 0) return job.match_score;

            // Check how many of those skills are matched in CV
            const matchedSkills = jobSkills.filter(skill => cvLower.includes(skill));
            
            // Calculate percentage matching score
            const ratio = matchedSkills.length / jobSkills.length;
            const computedScore = Math.round(ratio * 100);

            // Blend 70% computed score + 30% original score to keep context of experience level, etc.
            return Math.min(100, Math.round(computedScore * 0.7 + job.match_score * 0.3));
        }

        // Recalculate scores for all jobs
        function recalculateAllScores(cvText) {
            jobs = JOBS_DATA.map(job => {
                const newScore = calculateKeywordScore(job, cvText);
                return {
                    ...job,
                    match_score: newScore,
                    is_recalculated: cvText.trim().length > 0
                };
            });
            // Sort jobs by score descending
            jobs.sort((a, b) => b.match_score - a.match_score);
        }

        // Filter and Render logic
        function applyFilters() {
            const search = searchInput.value.toLowerCase().trim();
            const minScore = parseInt(minScoreRange.value, 10);
            const selectedLevel = levelSelect.value;

            const filtered = jobs.filter(job => {
                const company = (job.company || '').toLowerCase();
                const position = (job.position || '').toLowerCase();
                const matched = Array.isArray(job.matched_skills) ? job.matched_skills.join(" ") : (job.matched_skills || '');
                const skillsList = matched.toLowerCase();
                
                const searchMatch = !search || 
                                    company.includes(search) || 
                                    position.includes(search) || 
                                    skillsList.includes(search);

                const scoreMatch = job.match_score >= minScore;

                const level = (job.experience_level || '').toLowerCase();
                const levelMatch = !selectedLevel || level.includes(selectedLevel);

                return searchMatch && scoreMatch && levelMatch;
            });

            document.getElementById('jobs-count').textContent = filtered.length + ' tin';
            renderJobsList(filtered);
            
            // If active job is still in the filtered list, update details, otherwise clear details
            if (activeJobId) {
                const activeJob = filtered.find(j => j.id === activeJobId);
                if (activeJob) {
                    showJobDetails(activeJob);
                } else {
                    clearDetails();
                }
            }
        }

        function clearDetails() {
            jobDetails.innerHTML = `
                <div class="empty-details">
                    <i class="fa-solid fa-briefcase"></i>
                    <h3>Vui lòng chọn một công việc bên danh sách để xem chi tiết</h3>
                    <p>Bộ đối khớp CV sẽ tự động tính điểm dựa trên hồ sơ của bạn</p>
                </div>`;
            activeJobId = null;
        }

        function renderJobsList(jobsToRender) {
            jobsList.innerHTML = '';
            
            if (jobsToRender.length === 0) {
                jobsList.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                        <i class="fa-solid fa-magnifying-glass" style="font-size: 1.8rem; margin-bottom: 8px;"></i>
                        <p>Không tìm thấy tin phù hợp</p>
                    </div>`;
                return;
            }

            jobsToRender.forEach(job => {
                const card = document.createElement('div');
                card.className = `job-card ${activeJobId === job.id ? 'active' : ''}`;
                card.dataset.id = job.id;

                const scoreClass = job.match_score >= 70 ? 'high' : (job.match_score >= 40 ? 'mid' : 'low');

                card.innerHTML = `
                    <div class="job-card-header">
                        <h4 class="job-card-title">${job.position || 'Không rõ vị trí'}</h4>
                    </div>
                    <div class="job-card-company">
                        <i class="fa-solid fa-building"></i> ${job.company || 'N/A'}
                    </div>
                    <div class="job-card-meta">
                        <span><i class="fa-solid fa-location-dot"></i> ${job.location || 'N/A'}</span>
                        <span><i class="fa-solid fa-money-bill-wave"></i> ${job.salary || 'N/A'}</span>
                    </div>
                    <div class="badge-row">
                        <span class="score-badge ${scoreClass}">
                            <i class="fa-solid fa-circle-check"></i> ${job.match_score}%
                        </span>
                        ${job.is_recalculated ? '<span class="new-match-indicator">Đã chấm điểm CV</span>' : ''}
                    </div>
                `;

                card.addEventListener('click', () => {
                    const prevActive = jobsList.querySelector('.job-card.active');
                    if (prevActive) prevActive.classList.remove('active');
                    card.classList.add('active');
                    activeJobId = job.id;
                    showJobDetails(job);
                });

                jobsList.appendChild(card);
            });
        }

        // Display Detailed Job View
        function showJobDetails(job) {
            const reqs = typeof job.requirements === 'string' ? JSON.parse(job.requirements) : (job.requirements || []);
            
            // Extract dynamic match list based on loaded CV
            let matched = [];
            let missing = [];

            if (userCvText.trim().length > 0) {
                const cvLower = userCvText.toLowerCase();
                const reqText = reqs.join(" ").toLowerCase();
                const jobSkills = SKILLS_DICT.filter(skill => reqText.includes(skill));

                matched = jobSkills.filter(skill => cvLower.includes(skill));
                missing = jobSkills.filter(skill => !cvLower.includes(skill));
            } else {
                matched = typeof job.matched_skills === 'string' ? JSON.parse(job.matched_skills) : (job.matched_skills || []);
                missing = typeof job.missing_skills === 'string' ? JSON.parse(job.missing_skills) : (job.missing_skills || []);
            }

            const reqHtml = reqs.map(r => `<li>${r}</li>`).join('') || '<li>Không rõ yêu cầu cụ thể</li>';
            const matchedHtml = matched.map(s => `<span class="skill-tag matched">${s}</span>`).join('') || '<span style="color:var(--text-secondary); font-size:0.85rem;">Không khớp kỹ năng nào</span>';
            const missingHtml = missing.map(s => `<span class="skill-tag missing">${s}</span>`).join('') || '<span style="color:var(--text-secondary); font-size:0.85rem;">Không có</span>';
            
            const scoreClass = job.match_score >= 70 ? 'high' : (job.match_score >= 40 ? 'mid' : 'low');

            const applyButton = job.post_url ? `
                <a href="${job.post_url}" target="_blank" class="btn btn-primary" style="margin-top: 15px;">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Xem bài viết tuyển dụng trên Facebook
                </a>` : '';

            // Render AI Recalculate button if API key is present
            const hasApiKey = apiKeyInput.value.trim().length > 0;
            const aiAnalyzeButton = hasApiKey ? `
                <button class="btn" onclick="triggerAiReanalysis(${job.id})" style="background:var(--bg-primary); border-color:var(--accent);">
                    <i class="fa-solid fa-microchip text-accent"></i> Hỏi Gemini AI chấm điểm lại
                </button>` : '';

            jobDetails.innerHTML = `
                <div class="details-title-section">
                    <div>
                        <h2>${job.position || 'Không rõ vị trí'}</h2>
                        <div class="job-card-company" style="font-size: 1.05rem;">
                            <i class="fa-solid fa-building"></i> ${job.company || 'Không rõ tên công ty'}
                        </div>
                    </div>
                    <span class="score-badge ${scoreClass}" style="font-size: 0.95rem; padding: 8px 16px;">
                        Độ phù hợp: ${job.match_score}%
                    </span>
                </div>

                <div class="details-meta-grid">
                    <div class="details-meta-item">
                        <div class="details-meta-icon"><i class="fa-solid fa-money-bill-wave"></i></div>
                        <div class="details-meta-text">
                            <h4>Mức Lương</h4>
                            <p>${job.salary || 'Thỏa thuận'}</p>
                        </div>
                    </div>
                    <div class="details-meta-item">
                        <div class="details-meta-icon"><i class="fa-solid fa-location-dot"></i></div>
                        <div class="details-meta-text">
                            <h4>Địa Điểm</h4>
                            <p>${job.location || 'Hà Nội/TP.HCM'}</p>
                        </div>
                    </div>
                    <div class="details-meta-item">
                        <div class="details-meta-icon"><i class="fa-solid fa-briefcase"></i></div>
                        <div class="details-meta-text">
                            <h4>Cấp bậc</h4>
                            <p style="text-transform: capitalize;">${job.experience_level || 'Intern/Fresher'}</p>
                        </div>
                    </div>
                    <div class="details-meta-item">
                        <div class="details-meta-icon"><i class="fa-solid fa-clock"></i></div>
                        <div class="details-meta-text">
                            <h4>Hình thức</h4>
                            <p style="text-transform: uppercase;">${job.work_type || 'Full-time'}</p>
                        </div>
                    </div>
                </div>

                <div class="details-body">
                    <div>
                        <h3 class="details-section-title"><i class="fa-solid fa-list-check"></i> Yêu cầu chi tiết</h3>
                        <ul style="padding-left: 20px; line-height: 1.6; color: var(--text-secondary);">
                            ${reqHtml}
                        </ul>
                    </div>

                    <div>
                        <h3 class="details-section-title"><i class="fa-solid fa-circle-check text-success"></i> Kỹ năng phù hợp</h3>
                        <div class="skills-container">
                            ${matchedHtml}
                        </div>
                    </div>

                    <div>
                        <h3 class="details-section-title"><i class="fa-solid fa-triangle-exclamation text-danger"></i> Kỹ năng chưa đáp ứng</h3>
                        <div class="skills-container">
                            ${missingHtml}
                        </div>
                    </div>

                    <div id="ai-rec-section">
                        <h3 class="details-section-title"><i class="fa-solid fa-lightbulb text-warning"></i> Đánh giá từ AI</h3>
                        <div class="ai-box">
                            ${job.recommendation || 'Chưa có nhận xét chi tiết.'}
                        </div>
                    </div>

                    <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top: 15px;">
                        ${applyButton}
                        ${aiAnalyzeButton}
                    </div>
                </div>
            `;
        }

        // Trigger real-time client-side Gemini AI re-analysis using the key provided by the user
        async function triggerAiReanalysis(jobId) {
            const apiKey = apiKeyInput.value.trim();
            if (!apiKey) {
                alert("Vui lòng nhập Gemini API Key ở thanh bên trái!");
                return;
            }

            const job = jobs.find(j => j.id === jobId);
            if (!job) return;

            const recBox = document.getElementById('ai-rec-section');
            recBox.innerHTML = `
                <h3 class="details-section-title"><i class="fa-solid fa-spinner fa-spin text-accent"></i> Đang phân tích bằng Gemini AI...</h3>
                <div class="ai-box" style="opacity: 0.6;">
                    Đang gửi thông tin tuyển dụng & CV mới lên Gemini API để chấm điểm lại chi tiết...
                </div>
            `;

            const prompt = `So sánh CV ứng viên với tin tuyển dụng bên dưới.
Trả lời DUY NHẤT bằng JSON theo cấu trúc:
{
  "match_score": 0-100,
  "matched_skills": ["kỹ năng phù hợp 1", "kỹ năng 2"],
  "missing_skills": ["kỹ năng thiếu 1", "kỹ năng 2"],
  "recommendation": "nhận xét ngắn gọn, khuyên ứng viên có nên ứng tuyển hay không và lý do"
}

CV ứng viên:
---
${userCvText}
---

Thông tin tuyển dụng:
Công ty: ${job.company || "Không rõ"}
Vị trí: ${job.position || "Không rõ"}
Yêu cầu công việc: ${Array.isArray(job.requirements) ? job.requirements.join(", ") : job.requirements}
`;

            try {
                // Call Gemini 2.5 Flash direct via fetch
                const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        contents: [{ parts: [{ text: prompt }] }],
                        generationConfig: {
                            responseMimeType: "application/json",
                            temperature: 0.2
                        }
                    })
                });

                if (!response.ok) {
                    throw new Error(`Gemini API Error: Status ${response.status}`);
                }

                const data = await response.json();
                const resText = data.candidates[0].content.parts[0].text;
                const parsed = JSON.parse(resText);

                // Update job object in memory
                job.match_score = parsed.match_score;
                job.matched_skills = parsed.matched_skills;
                job.missing_skills = parsed.missing_skills;
                job.recommendation = parsed.recommendation;

                // Save back to local jobs state
                const jobIdx = jobs.findIndex(j => j.id === jobId);
                if (jobIdx !== -1) {
                    jobs[jobIdx] = { ...job, is_recalculated: true };
                }

                // Re-render UI details and list
                applyFilters();
                showJobDetails(job);
                alert("Đã phân tích đối khớp AI thành công!");

            } catch (e) {
                console.error("Lỗi phân tích AI:", e);
                alert("Lỗi phân tích AI: " + e.message);
                showJobDetails(job); // restore layout
            }
        }
    </script>
</body>
</html>
"""
        html_content = html_template.replace("__JOBS_JSON__", jobs_json).replace("__STATS_JSON__", stats_json)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Đã xuất báo cáo HTML: {filepath}")
        return filepath
