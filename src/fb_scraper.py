"""
Facebook Group Scraper sử dụng Playwright + Stealth.

Module này điều khiển Chrome thật để:
1. Đăng nhập Facebook bằng cookies đã lưu
2. Vào từng nhóm, cuộn trang
3. Trích xuất nội dung text của các bài viết
"""
import asyncio
import hashlib
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth

from fb_config import (
    COOKIES_PATH,
    SCROLL_DELAY_MIN,
    SCROLL_DELAY_MAX,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
    MAX_SCROLLS_PER_GROUP,
    POSTS_PER_GROUP_LIMIT,
    MAX_POST_AGE_DAYS,
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    USER_AGENT,
    JOB_KEYWORDS,
)

logger = logging.getLogger(__name__)


# ============================================================
# Dataclass-like dict cho mỗi bài viết đã scrape
# ============================================================
def make_post(
    text: str,
    author: str = "",
    timestamp: str = "",
    group_url: str = "",
    post_url: str = "",
) -> dict:
    """Tạo dict chuẩn cho 1 bài viết đã trích xuất."""
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    return {
        "text": text,
        "author": author,
        "timestamp": timestamp,
        "group_url": group_url,
        "post_url": post_url,
        "content_hash": content_hash,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============================================================
# Helpers
# ============================================================
async def random_delay(min_sec: float, max_sec: float):
    """Sleep random giữa min và max giây (giả lập hành vi người thật)."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def human_scroll(page: Page):
    """Cuộn trang giống người thật: cuộn từng đoạn ngẫu nhiên."""
    scroll_amount = random.randint(300, 700)
    await page.mouse.wheel(0, scroll_amount)
    await random_delay(SCROLL_DELAY_MIN, SCROLL_DELAY_MAX)


def has_keywords(text: str) -> bool:
    """Kiểm tra bài viết có chứa từ khóa tuyển dụng VÀ từ khóa kỹ năng phù hợp (nguyên từ)."""
    text_lower = text.lower()
    
    # Từ khóa chỉ định đây là bài tuyển dụng/tìm việc
    action_kws = ["tuyển dụng", "tuyển", "recruiting", "hiring", "looking for", "intern", "thực tập", "fresher", "junior", "cv", "jd"]
    # Từ khóa chỉ định kỹ năng của ứng viên (dùng regex để khớp nguyên từ)
    skill_kws = ["python", "ai", "machine learning", "deep learning", "ml", "fastapi", "flask", "django", "pytorch", "tensorflow", "react"]
    
    has_action = any(kw in text_lower for kw in action_kws)
    
    has_skill = False
    for kw in skill_kws:
        if " " in kw:
            if kw in text_lower:
                has_skill = True
                break
        else:
            # Khớp nguyên từ bằng regex (ví dụ \bai\b tránh khớp tai, cai, v.v.)
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                has_skill = True
                break
                
    return has_action and has_skill


def parse_facebook_date(date_str: str) -> Optional[datetime]:
    """Parse chuỗi ngày tháng của Facebook thành đối tượng datetime."""
    if not date_str:
        return None
    
    now = datetime.now()
    date_str = date_str.lower().strip()
    
    # 1. Các định dạng tương đối ngắn/đơn giản
    if "vừa xong" in date_str or "just now" in date_str or "vừa mới" in date_str:
        return now
        
    # X phút / X mins
    match = re.search(r"(\d+)\s*(phút|min)", date_str)
    if match:
        return now - timedelta(minutes=int(match.group(1)))
        
    # X giờ / X hrs / Xh
    match = re.search(r"(\d+)\s*(giờ|hr|h\b)", date_str)
    if match:
        return now - timedelta(hours=int(match.group(1)))
        
    # X ngày / X days / Xd
    match = re.search(r"(\d+)\s*(ngày|day|d\b)", date_str)
    if match:
        return now - timedelta(days=int(match.group(1)))
        
    # X tuần / X weeks / Xw
    match = re.search(r"(\d+)\s*(tuần|week|w\b)", date_str)
    if match:
        return now - timedelta(weeks=int(match.group(1)))

    # X tháng / X months
    match = re.search(r"(\d+)\s*(tháng|month)", date_str)
    if match and "lúc" not in date_str and "at" not in date_str:
        return now - timedelta(days=int(match.group(1)) * 30)

    # 2. Hôm qua lúc H:M / Yesterday at H:M
    if "hôm qua" in date_str or "yesterday" in date_str:
        time_match = re.search(r"(\d{1,2})[:h](\d{2})", date_str)
        hour = int(time_match.group(1)) if time_match else 12
        minute = int(time_match.group(2)) if time_match else 0
        yesterday = now - timedelta(days=1)
        return datetime(yesterday.year, yesterday.month, yesterday.day, hour, minute)

    # 3. Ngày cụ thể: X tháng Y [năm Z] [lúc H:M] / Month X[, Year] [at H:M]
    month_map = {
        "tháng 1": 1, "tháng 2": 2, "tháng 3": 3, "tháng 4": 4, "tháng 5": 5, "tháng 6": 6,
        "tháng 7": 7, "tháng 8": 8, "tháng 9": 9, "tháng 10": 10, "tháng 11": 11, "tháng 12": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    # Định dạng tiếng Việt: <ngày> tháng <tháng>[, <năm>] [lúc <giờ>:<phút>]
    match_vi = re.search(r"(\d{1,2})\s+tháng\s+(\d{1,2})(?:,\s+(\d{4}))?", date_str)
    if match_vi:
        day = int(match_vi.group(1))
        month = int(match_vi.group(2))
        year = int(match_vi.group(3)) if match_vi.group(3) else now.year
        
        time_match = re.search(r"lúc\s+(\d{1,2})[:h](\d{2})", date_str)
        hour = int(time_match.group(1)) if time_match else 12
        minute = int(time_match.group(2)) if time_match else 0
        
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            pass

    # Định dạng tiếng Anh: <tên tháng> <ngày>[th|st|nd|rd][, <năm>] [at <giờ>:<phút>]
    for m_name, m_val in month_map.items():
        if m_name in date_str:
            match_en = re.search(r"\b" + re.escape(m_name) + r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s+(\d{4}))?", date_str)
            if match_en:
                day = int(match_en.group(1))
                month = m_val
                year = int(match_en.group(2)) if match_en.group(2) else now.year
                
                time_match = re.search(r"(?:at|lúc)\s+(\d{1,2})[:h](\d{2})", date_str)
                hour = int(time_match.group(1)) if time_match else 12
                minute = int(time_match.group(2)) if time_match else 0
                
                try:
                    return datetime(year, month, day, hour, minute)
                except ValueError:
                    pass

    return None


# ============================================================
# Cookie Management
# ============================================================
def load_cookies_from_file(path: str) -> list[dict]:
    """
    Đọc cookies Facebook từ file JSON.
    
    Hỗ trợ 2 format:
    1. Format từ extension "EditThisCookie" / "Cookie Editor":
       [{"name": "...", "value": "...", "domain": ".facebook.com", ...}]
    2. Format Playwright native:
       [{"name": "...", "value": "...", "domain": ".facebook.com",
         "path": "/", "expires": ..., "httpOnly": true, "secure": true, "sameSite": "None"}]
    """
    with open(path, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    # Chuẩn hóa cookies cho Playwright
    normalized = []
    for c in cookies:
        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".facebook.com"),
            "path": c.get("path", "/"),
        }
        # Playwright yêu cầu sameSite phải là enum chuẩn
        same_site = c.get("sameSite", "None")
        if isinstance(same_site, str) and same_site.lower() in ("lax", "strict", "none"):
            cookie["sameSite"] = same_site.capitalize()
            if cookie["sameSite"] == "None":  # Playwright dùng "None" string
                cookie["sameSite"] = "None"
        else:
            cookie["sameSite"] = "None"

        if "expires" in c and c["expires"]:
            # Một số extension export epoch float, Playwright cần float
            try:
                cookie["expires"] = float(c["expires"])
            except (ValueError, TypeError):
                pass  # Bỏ qua nếu không parse được

        if "httpOnly" in c:
            cookie["httpOnly"] = bool(c["httpOnly"])
        if "secure" in c:
            cookie["secure"] = bool(c["secure"])

        normalized.append(cookie)

    return normalized


# ============================================================
# Core Scraper
# ============================================================
class FacebookGroupScraper:
    """
    Scraper đọc bài viết từ nhóm Facebook.
    
    Sử dụng:
        async with FacebookGroupScraper() as scraper:
            posts = await scraper.scrape_group("https://facebook.com/groups/xxx")
    """

    def __init__(self, headless: bool = False):
        """
        Args:
            headless: True = chạy ngầm (dễ bị phát hiện).
                      False = mở Chrome thật trên màn hình (an toàn hơn).
        """
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        await self._setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._teardown()

    async def _setup(self):
        """Khởi tạo Playwright + Chrome với stealth."""
        logger.info("Đang khởi tạo trình duyệt Chrome (stealth mode)...")

        # Stealth wrapper — tự inject các patch chống detection
        self._stealth = Stealth()
        self._playwright_cm = self._stealth.use_async(async_playwright())
        self._playwright = await self._playwright_cm.__aenter__()

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--lang=vi-VN,vi",
            ],
        )

        # Tạo context với viewport và user-agent giả lập
        self._context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )

        # Load cookies Facebook
        cookies = load_cookies_from_file(COOKIES_PATH)
        await self._context.add_cookies(cookies)
        logger.info(f"Đã load {len(cookies)} cookies Facebook.")

        self._page = await self._context.new_page()

    async def _teardown(self):
        """Đóng trình duyệt."""
        if self._browser:
            await self._browser.close()
        if self._playwright_cm:
            await self._playwright_cm.__aexit__(None, None, None)
        logger.info("Đã đóng trình duyệt.")

    async def _check_login(self) -> bool:
        """Kiểm tra cookies có hợp lệ (đã đăng nhập) không."""
        try:
            await self._page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Nếu thấy form login → cookies hết hạn
            login_form = await self._page.query_selector('form[action*="login"]')
            if login_form:
                logger.error("Cookies đã hết hạn! Cần export lại cookies mới.")
                return False

            logger.info("Đăng nhập Facebook thành công bằng cookies.")
            return True
        except Exception as e:
            logger.error(f"Lỗi kiểm tra đăng nhập: {e}")
            return False

    async def _expand_all_posts(self):
        """Tìm và click tất cả các nút 'Xem thêm' để hiển thị đầy đủ nội dung bài viết."""
        try:
            buttons = await self._page.query_selector_all('div[role="button"]')
            clicked_count = 0
            for btn in buttons:
                try:
                    txt = await btn.inner_text()
                    if txt.strip() in ("Xem thêm", "See more"):
                        if await btn.is_visible():
                            await btn.click()
                            clicked_count += 1
                            # Delay nhỏ tránh click dồn dập
                            await asyncio.sleep(0.5)
                except Exception:
                    pass
            if clicked_count > 0:
                logger.info(f"  Đã tự động mở rộng {clicked_count} bài viết ('Xem thêm').")
        except Exception as e:
            logger.warning(f"  Lỗi khi tự động mở rộng bài viết: {e}")

    async def _extract_posts_from_page(self, group_url: str) -> list[dict]:
        """
        Trích xuất nội dung bài viết từ trang hiện tại.
        
        Chiến lược: Dùng ARIA role="article" (ổn định hơn CSS class)
        và tìm các container text bên trong.
        """
        posts = []
        
        # Tự động mở rộng các bài viết rút gọn trên màn hình
        await self._expand_all_posts()

        # Facebook dùng div[role="feed"] chứa các div[role="article"]
        # Đây là selector ổn định nhất vì dùng ARIA attributes
        articles = await self._page.query_selector_all('div[role="article"]')

        if not articles:
            # Thử cho trang tìm kiếm (search results cards)
            articles = await self._page.query_selector_all('div.x1jx94hy')

        if not articles:
            # Fallback: thử selector khác cho mobile/mbasic layout
            articles = await self._page.query_selector_all('div[data-ad-preview="message"]')

        logger.info(f"Tìm thấy {len(articles)} bài viết trên trang.")

        for article in articles[:POSTS_PER_GROUP_LIMIT]:
            try:
                # Lấy text nội dung chính
                text = await article.inner_text()
                text = text.strip()

                # Làm sạch text nếu có các từ khóa dư thừa từ search result template (như chữ Facebook lặp đi lặp lại)
                lines = [line.strip() for line in text.split("\n")]
                cleaned_lines = [line for line in lines if line.lower() != "facebook" and line]
                text = "\n".join(cleaned_lines)

                # Bỏ bài quá ngắn (spam, reaction, etc.)
                if len(text) < 50:
                    continue

                # Lấy tên tác giả (thường là heading hoặc link đầu tiên)
                author = ""
                author_el = await article.query_selector('strong > a, h2 a, h3 a, a[role="link"]')
                if author_el:
                    author = (await author_el.inner_text()).strip()

                # Lấy link bài viết (nếu có)
                post_url = ""
                time_link = None
                
                # Tìm tất cả anchor trong thẻ bài viết
                anchors = await article.query_selector_all('a')
                
                # Ưu tiên 1: Link chứa /posts/ hoặc /permalink/ — đây là permalink bài viết thật
                for a in anchors:
                    href = await a.get_attribute("href") or ""
                    if "/posts/" in href or "/permalink/" in href or "story_fbid=" in href:
                        time_link = a
                        post_url = href if href.startswith("http") else "https://www.facebook.com" + href
                        break
                
                # Ưu tiên 2: Link chứa __cft__ nhưng KHÔNG phải homepage nhóm (phải có /posts/ hoặc #?)
                if not post_url:
                    for a in anchors:
                        href = await a.get_attribute("href") or ""
                        if "__cft__[0]" in href:
                            # Loại bỏ link homepage nhóm (dạng /groups/ID/?__cft__)
                            # Giữ lại link có path cụ thể hơn
                            if "/posts/" in href or "/permalink/" in href:
                                time_link = a
                                post_url = href if href.startswith("http") else "https://www.facebook.com" + href
                                break
                
                # Ưu tiên 3: Nếu vẫn không tìm được, lấy link __cft__ bất kỳ (kể cả link nhóm) làm fallback
                if not post_url:
                    for a in anchors:
                        href = await a.get_attribute("href") or ""
                        if "__cft__[0]" in href and href not in (group_url,):
                            time_link = a
                            post_url = href if href.startswith("http") else "https://www.facebook.com" + href
                            break

                # Nếu link bắt đầu bằng ? (relative query parameter)
                if post_url and post_url.startswith("?"):
                    # Trích xuất Group ID/Name nếu có link nhóm trong bài viết
                    group_id = ""
                    for a in anchors:
                        g_href = await a.get_attribute("href") or ""
                        match_g = re.search(r"/groups/([^/?]+)", g_href)
                        if match_g:
                            group_id = match_g.group(1)
                            break
                    
                    if group_id:
                        post_url = f"https://www.facebook.com/groups/{group_id}/" + post_url
                    elif "/groups/" in group_url:
                        # Dùng group_url hiện tại làm fallback
                        match_g = re.search(r"/groups/([^/?]+)", group_url)
                        if match_g:
                            post_url = f"https://www.facebook.com/groups/{match_g.group(1)}/" + post_url
                        else:
                            post_url = "https://www.facebook.com" + href
                    else:
                        post_url = href
                        if post_url and not post_url.startswith("http"):
                            post_url = "https://www.facebook.com" + post_url

                # Lấy timestamp
                timestamp = ""
                if time_link:
                    # Chạy đoạn script giải mã ngày tháng
                    js_deobfuscate = """(el) => {
                        let spans = Array.from(el.querySelectorAll('span')).filter(s => s.querySelectorAll('span').length === 0);
                        let visibleSpans = [];
                        for (let s of spans) {
                            let style = window.getComputedStyle(s);
                            if (style.position === 'relative') {
                                visibleSpans.push({
                                    text: s.textContent,
                                    order: parseInt(style.order || 0, 10)
                                });
                            }
                        }
                        visibleSpans.sort((a, b) => a.order - b.order);
                        return visibleSpans.map(x => x.text).join('').trim();
                    }"""
                    try:
                        timestamp = await time_link.evaluate(js_deobfuscate)
                    except Exception as e:
                        logger.warning(f"Lỗi giải mã JS timestamp: {e}")
                        
                # Fallback lấy timestamp cũ nếu de-obfuscation bị trống
                if not timestamp:
                    time_el = await article.query_selector('span[id] > a > span, abbr[data-utime]')
                    if time_el:
                        timestamp = (await time_el.inner_text()).strip()

                # Chỉ bỏ qua bài quá ngắn (đã lọc ở trên) hoặc không có nội dung gì để xử lý
                # Không bắt buộc phải có post_url — group_url là fallback đủ để user biết nguồn
                post = make_post(
                    text=text,
                    author=author,
                    timestamp=timestamp,
                    group_url=group_url,
                    post_url=post_url,
                )
                posts.append(post)

            except Exception as e:
                logger.warning(f"Lỗi trích xuất bài viết: {e}")
                continue

        return posts

    async def scrape_group(self, group_url: str) -> list[dict]:
        """
        Scrape bài viết từ 1 nhóm Facebook.
        
        Args:
            group_url: URL nhóm (vd: https://www.facebook.com/groups/xxx)
            
        Returns:
            Danh sách dict bài viết đã trích xuất.
        """
        logger.info(f"Đang vào nhóm: {group_url}")

        try:
            await self._page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            logger.error(f"Không thể truy cập nhóm {group_url}: {e}")
            return []

        # Đợi trang load xong
        await random_delay(3, 5)

        # Đóng popup/modal nếu có (Facebook hay hiện dialog)
        await self._close_popups()

        # Cuộn trang để load thêm bài viết
        all_posts = []
        seen_hashes = set()

        for scroll_num in range(MAX_SCROLLS_PER_GROUP):
            logger.info(f"  Cuộn trang lần {scroll_num + 1}/{MAX_SCROLLS_PER_GROUP}...")

            new_posts = await self._extract_posts_from_page(group_url)

            # Chỉ giữ bài mới chưa thấy và còn hạn tuyển dụng
            has_old_post = False
            for post in new_posts:
                if post["content_hash"] not in seen_hashes:
                    seen_hashes.add(post["content_hash"])
                    
                    # Kiểm tra ngày đăng
                    dt = parse_facebook_date(post["timestamp"])
                    if dt:
                        age = datetime.now() - dt
                        if age.days > MAX_POST_AGE_DAYS:
                            logger.info(f"  Bỏ qua bài viết cũ ({age.days} ngày): {post['text'][:50]}...")
                            has_old_post = True
                            continue
                    
                    all_posts.append(post)

            # Nếu phát hiện bài viết cũ (để tránh dừng do bài ghim, chỉ dừng khi đã có một số bài viết)
            if has_old_post and len(all_posts) > 2:
                logger.info(f"  Đã phát hiện bài viết cũ hơn {MAX_POST_AGE_DAYS} ngày. Dừng cuộn nhóm sớm.")
                break

            # Cuộn xuống để load thêm
            await human_scroll(self._page)

            # Nếu đã đủ bài thì dừng
            if len(all_posts) >= POSTS_PER_GROUP_LIMIT:
                break

        logger.info(f"Đã scrape {len(all_posts)} bài viết từ nhóm.")
        return all_posts

    async def _close_popups(self):
        """Đóng các popup/modal phiền phức của Facebook."""
        popup_selectors = [
            'div[aria-label="Đóng"]',
            'div[aria-label="Close"]',
            'div[role="dialog"] div[aria-label="Đóng"]',
            'div[role="dialog"] div[aria-label="Close"]',
        ]
        for selector in popup_selectors:
            try:
                btn = await self._page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await random_delay(ACTION_DELAY_MIN, ACTION_DELAY_MAX)
                    logger.info(f"Đã đóng popup: {selector}")
            except Exception:
                pass

    async def scrape_all_groups(self, group_urls: list[str]) -> list[dict]:
        """
        Scrape tất cả các nhóm trong danh sách.
        
        Args:
            group_urls: Danh sách URL nhóm Facebook.
            
        Returns:
            Tất cả bài viết từ tất cả nhóm.
        """
        # Kiểm tra đăng nhập trước
        if not await self._check_login():
            logger.error("Không thể đăng nhập Facebook. Dừng lại.")
            return []

        all_posts = []
        for i, url in enumerate(group_urls):
            logger.info(f"\n{'='*50}")
            logger.info(f"Nhóm {i+1}/{len(group_urls)}: {url}")
            logger.info(f"{'='*50}")

            posts = await self.scrape_group(url)
            all_posts.extend(posts)

            # Nghỉ giữa các nhóm (giảm nguy cơ bị phát hiện)
            if i < len(group_urls) - 1:
                wait = random.uniform(5, 15)
                logger.info(f"Nghỉ {wait:.1f}s trước khi vào nhóm tiếp...")
                await asyncio.sleep(wait)

        return all_posts

    def filter_potential_jobs(self, posts: list[dict]) -> list[dict]:
        """Lọc sơ bộ bài viết có khả năng là tin tuyển dụng dựa trên keywords."""
        potential = [p for p in posts if has_keywords(p["text"])]
        logger.info(
            f"Lọc keyword: {len(potential)}/{len(posts)} bài có chứa từ khóa tuyển dụng."
        )
        return potential
