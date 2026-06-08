import asyncio
import json
import os
import sys
import urllib.parse
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from fb_config import BASE_DIR, COOKIES_PATH

async def main():
    cookies_path = COOKIES_PATH
    query = os.getenv("FB_SEARCH_QUERY", "tuyển dụng python")
    encoded_query = urllib.parse.quote_plus(query)
    search_url = f"https://www.facebook.com/search/posts/?q={encoded_query}"
    debug_dir = os.path.join(BASE_DIR, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    screenshot_path = os.path.join(debug_dir, "search_debug.png")
    
    print(f"Searching for: '{query}' at URL: {search_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--lang=vi-VN,vi",
            ]
        )
        
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )
        
        if os.path.exists(cookies_path):
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            for c in cookies:
                if "sameSite" in c and c["sameSite"] not in ("Strict", "Lax", "None"):
                    c["sameSite"] = "None"
            await context.add_cookies(cookies)
            print("Cookies loaded.")
        else:
            print("No cookies found!")
            await browser.close()
            return

        stealth = Stealth()
        page = await context.new_page()
        
        print("Navigating to Search page...")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Extract posts
        articles = await page.query_selector_all('div[role="article"]')
        print(f"Number of div[role='article']: {len(articles)}")
        
        for i, article in enumerate(articles[:5]):
            try:
                text = await article.inner_text()
                text = text.strip()
                print(f"\n--- Post {i+1} (length: {len(text)}) ---")
                print(text[:200] + "...")
            except Exception as e:
                print(f"Error reading article {i+1}: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
