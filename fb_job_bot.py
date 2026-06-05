#!/usr/bin/env python3
"""
Facebook Job Scraper Bot — Script chạy chính.

Flow:
1. Load cookies Facebook → kiểm tra đăng nhập
2. Scrape bài viết từ các nhóm FB đã cấu hình
3. Lọc sơ bộ bằng keywords
4. Phân tích bằng AI → phân loại + trích xuất + matching CV
5. Lưu database + xuất báo cáo

Cách chạy:
    python fb_job_bot.py                  # Quét tất cả nhóm
    python fb_job_bot.py --report         # Chỉ xuất báo cáo (không quét)
    python fb_job_bot.py --headless       # Chạy ngầm (rủi ro bị phát hiện cao)
    python fb_job_bot.py --min-score 50   # Chỉ hiện job match >= 50%
"""
import argparse
import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from fb_config import FACEBOOK_GROUPS, COOKIES_PATH, CV_PATH
from fb_scraper import FacebookGroupScraper
from job_analyzer import analyze_post
from job_storage import JobDatabase

# ============================================================
# Logging
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# Banner
# ============================================================
BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          🔍 FACEBOOK JOB SCRAPER BOT v1.0                  ║
║          Tự động tìm việc từ nhóm Facebook                  ║
╚══════════════════════════════════════════════════════════════╝
"""


# ============================================================
# Pre-flight checks
# ============================================================
def preflight_checks() -> bool:
    """Kiểm tra điều kiện cần thiết trước khi chạy."""
    ok = True

    # 1. Kiểm tra cookies
    if not os.path.exists(COOKIES_PATH):
        logger.error(f"❌ Không tìm thấy file cookies: {COOKIES_PATH}")
        logger.error("   Xem hướng dẫn trong file export_cookies.md")
        ok = False

    # 2. Kiểm tra API key
    if not os.environ.get("GEMINI_API_KEY"):
        logger.error("❌ Chưa cấu hình GEMINI_API_KEY trong file .env")
        ok = False

    # 3. Kiểm tra CV
    if not os.path.exists(CV_PATH):
        logger.warning(f"⚠️  Không tìm thấy CV: {CV_PATH} — sẽ bỏ qua bước matching")

    # 4. Kiểm tra danh sách nhóm
    if not FACEBOOK_GROUPS:
        logger.error("❌ Chưa cấu hình nhóm Facebook trong fb_config.py")
        ok = False

    return ok


# ============================================================
# Main pipeline
# ============================================================
async def run_scrape_pipeline(headless: bool = False, min_score: int = 0):
    """Pipeline chính: scrape → analyze → store → report."""

    start_time = time.time()

    # Load CV
    cv_text = ""
    if os.path.exists(CV_PATH):
        with open(CV_PATH, "r", encoding="utf-8") as f:
            cv_text = f.read()

    # === PHASE 1: SCRAPE ===
    logger.info("=" * 60)
    logger.info("📡 PHASE 1: Scrape bài viết từ nhóm Facebook")
    logger.info("=" * 60)

    async with FacebookGroupScraper(headless=headless) as scraper:
        all_posts = await scraper.scrape_all_groups(FACEBOOK_GROUPS)

        # Lọc sơ bộ bằng keywords
        potential_posts = scraper.filter_potential_jobs(all_posts)

    # === PHASE 2: STORE RAW POSTS ===
    logger.info("")
    logger.info("=" * 60)
    logger.info("💾 PHASE 2: Lưu bài viết vào database")
    logger.info("=" * 60)

    with JobDatabase() as db:
        new_count = db.save_posts_batch(all_posts)
        logger.info(f"Bài viết mới: {new_count}/{len(all_posts)} (bỏ qua {len(all_posts) - new_count} bài đã có)")

        # === PHASE 3: AI ANALYSIS ===
        logger.info("")
        logger.info("=" * 60)
        logger.info("🤖 PHASE 3: Phân tích bài viết bằng AI")
        logger.info("=" * 60)

        # Chỉ phân tích bài mới chưa analyzed
        unanalyzed = db.get_unanalyzed_posts()
        
        # Chỉ lọc những bài mới có chứa keywords để gửi AI phân tích
        keyword_hashes = {p["content_hash"] for p in potential_posts}
        to_analyze = [p for p in unanalyzed if p["content_hash"] in keyword_hashes]
        
        # Những bài không có keywords sẽ tự động đánh dấu là không phải job để tránh tốn API quota
        skipped_count = 0
        for post in unanalyzed:
            if post["content_hash"] not in keyword_hashes:
                db.mark_post_analyzed(post["content_hash"], is_job=False)
                skipped_count += 1
                
        if skipped_count > 0:
            logger.info(f"Đã tự động lọc và bỏ qua {skipped_count} bài viết không chứa từ khóa tuyển dụng phù hợp.")
            
        logger.info(f"Số bài cần phân tích bằng AI: {len(to_analyze)}")

        jobs_found = 0
        for i, post in enumerate(to_analyze):
            logger.info(f"\n[{i+1}/{len(to_analyze)}] Phân tích bài viết...")
            logger.info(f"  Preview: {post['text'][:100]}...")

            try:
                result = await analyze_post(post["text"], cv_text)

                if result:
                    # Là tin tuyển dụng!
                    jobs_found += 1
                    db.mark_post_analyzed(post["content_hash"], is_job=True)
                    db.save_job(
                        post_hash=post["content_hash"],
                        analysis=result,
                        group_url=post.get("group_url", ""),
                        post_url=post.get("post_url", ""),
                    )

                    job_info = result.get("job_info", {})
                    cv_match = result.get("cv_match", {})
                    score = cv_match.get("match_score", 0)

                    logger.info(f"  ✅ TIN TUYỂN DỤNG!")
                    logger.info(f"     🏢 {job_info.get('company', 'N/A')} — {job_info.get('position', 'N/A')}")
                    logger.info(f"     💰 {job_info.get('salary', 'N/A')}")
                    logger.info(f"     📊 Match score: {score}%")
                else:
                    db.mark_post_analyzed(post["content_hash"], is_job=False)
                    logger.info(f"  ❌ Không phải tin tuyển dụng.")

            except Exception as e:
                logger.error(f"  Lỗi phân tích: {e}")
                continue

            # Delay giữa các lần phân tích (tránh rate limit Gemini)
            if i < len(to_analyze) - 1:
                await asyncio.sleep(2)

        # === PHASE 4: REPORT ===
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 PHASE 4: Xuất báo cáo")
        logger.info("=" * 60)

        stats = db.get_stats()
        logger.info(f"Tổng bài đã quét: {stats['total_posts_scraped']}")
        logger.info(f"Bài đã phân tích: {stats['posts_analyzed']}")
        logger.info(f"Tin tuyển dụng: {stats['job_posts_found']}")
        logger.info(f"Lần quét này tìm thấy: {jobs_found} tin mới")
        logger.info(f"Match score trung bình: {stats['average_match_score']}%")

        # Xuất báo cáo
        csv_path = db.export_csv(min_score=min_score)
        md_path = db.export_markdown(min_score=min_score)
        html_path = db.export_html(min_score=min_score)
        logger.info(f"📁 Báo cáo CSV: {csv_path}")
        logger.info(f"📁 Báo cáo Markdown: {md_path}")
        logger.info(f"📁 Báo cáo HTML: {html_path}")

        # In top jobs ra terminal
        top_jobs = db.get_jobs(min_score=min_score, limit=10)
        if top_jobs:
            logger.info("")
            logger.info("🏆 TOP JOBS PHÙ HỢP NHẤT:")
            logger.info("-" * 50)
            for j in top_jobs:
                score = j.get("match_score", 0)
                emoji = "🟢" if score >= 70 else ("🟡" if score >= 40 else "🔴")
                company = j.get("company") or "N/A"
                position = j.get("position") or "N/A"
                logger.info(
                    f"  {emoji} {company:20s} | "
                    f"{position:30s} | "
                    f"Score: {score}%"
                )

    elapsed = time.time() - start_time
    logger.info(f"\n⏱  Tổng thời gian: {elapsed:.0f}s ({elapsed/60:.1f} phút)")


# ============================================================
# Report-only mode
# ============================================================
def generate_report_only(min_score: int = 0):
    """Chỉ xuất báo cáo từ database có sẵn, không scrape."""
    logger.info("📊 Chế độ báo cáo — chỉ xuất từ database...")

    with JobDatabase() as db:
        stats = db.get_stats()
        logger.info(f"Database hiện có:")
        logger.info(f"  Bài viết: {stats['total_posts_scraped']}")
        logger.info(f"  Tin tuyển dụng: {stats['job_posts_found']}")
        logger.info(f"  Match score TB: {stats['average_match_score']}%")

        csv_path = db.export_csv(min_score=min_score)
        md_path = db.export_markdown(min_score=min_score)
        html_path = db.export_html(min_score=min_score)
        logger.info(f"📁 CSV: {csv_path}")
        logger.info(f"📁 Markdown: {md_path}")
        logger.info(f"📁 HTML: {html_path}")

        # In top jobs ra terminal
        top_jobs = db.get_jobs(min_score=min_score, limit=10)
        if top_jobs:
            logger.info("")
            logger.info("🏆 TOP JOBS PHÙ HỢP NHẤT:")
            logger.info("-" * 50)
            for j in top_jobs:
                score = j.get("match_score", 0)
                emoji = "🟢" if score >= 70 else ("🟡" if score >= 40 else "🔴")
                company = j.get("company") or "N/A"
                position = j.get("position") or "N/A"
                logger.info(
                    f"  {emoji} {company:20s} | "
                    f"{position:30s} | "
                    f"Score: {score}%"
                )


# ============================================================
# CLI Entry point
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Facebook Job Scraper Bot — Tự động tìm việc từ nhóm FB"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Chỉ xuất báo cáo từ DB, không scrape"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Chạy Chrome ở chế độ ẩn (rủi ro bị phát hiện cao hơn)"
    )
    parser.add_argument(
        "--min-score", type=int, default=0,
        help="Chỉ hiển thị job có match score >= N%% (mặc định: 0)"
    )
    args = parser.parse_args()

    print(BANNER)

    if args.report:
        generate_report_only(min_score=args.min_score)
        return

    # Pre-flight checks
    if not preflight_checks():
        logger.error("")
        logger.error("Vui lòng sửa các lỗi trên trước khi chạy bot.")
        sys.exit(1)

    logger.info(f"Số nhóm Facebook: {len(FACEBOOK_GROUPS)}")
    logger.info(f"Chế độ: {'headless (ẩn)' if args.headless else 'headed (hiện Chrome)'}")
    logger.info(f"Min match score: {args.min_score}%")
    logger.info("")

    asyncio.run(run_scrape_pipeline(
        headless=args.headless,
        min_score=args.min_score,
    ))


if __name__ == "__main__":
    main()
