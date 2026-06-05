import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    cookies_path = "/home/truongan/my_agent_project/fb_cookies.json"
    screenshot_path = "/home/truongan/my_agent_project/joined_groups.png"
    
    print("Launching browser...")
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
        
        print("Navigating to Groups page...")
        await page.goto("https://www.facebook.com/groups/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Let's list some links that point to groups
        group_links = await page.query_selector_all('a[href*="/groups/"]')
        print(f"Found {len(group_links)} links containing '/groups/'. Listing group URLs:")
        
        urls = set()
        for link in group_links:
            href = await link.get_attribute("href")
            if href:
                # Normalize URL
                if href.startswith("/"):
                    href = "https://www.facebook.com" + href
                # Exclude common non-group feed pages
                if "/groups/feed/" not in href and "/groups/discover/" not in href and "/groups/categories/" not in href and href != "https://www.facebook.com/groups/":
                    # Extract the group URL path
                    parts = href.split("/groups/")
                    if len(parts) > 1:
                        group_name = parts[1].split("/")[0].split("?")[0]
                        urls.add(f"https://www.facebook.com/groups/{group_name}")
        
        print("\nJoined or Visited Groups:")
        for url in urls:
            print(f"- {url}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
