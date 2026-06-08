import asyncio
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from fb_config import BASE_DIR, COOKIES_PATH

async def main():
    email = os.getenv("FB_EMAIL", "")
    password = os.getenv("FB_PASSWORD", "")
    cookies_path = COOKIES_PATH
    debug_dir = os.path.join(BASE_DIR, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    screenshot_path = os.path.join(debug_dir, "login_progress.png")

    print("Starting browser in headed mode to login to Facebook...")
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
        
        stealth = Stealth()
        page = await context.new_page()
        
        print("Navigating to Facebook...")
        await page.goto("https://www.facebook.com/")
        await page.wait_for_timeout(5000)
        
        url = page.url
        title = await page.title()
        print(f"Current URL: {url}")
        print(f"Current Title: {title}")
        
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Check if email input exists
        email_input = await page.query_selector('input[name="email"], input[id="email"]')
        if email_input:
            if email and password:
                print("Email input found! Filling credentials from environment...")
                await email_input.fill(email)
                await asyncio.sleep(1)
                
                pass_input = await page.query_selector('input[name="pass"], input[id="pass"]')
                if pass_input:
                    await pass_input.fill(password)
                    await asyncio.sleep(1)
                    print("Pressing Enter to login...")
                    await pass_input.press("Enter")
                else:
                    print("Password input not found!")
            else:
                print("Email input found. Set FB_EMAIL and FB_PASSWORD, or log in manually in the browser window.")
        else:
            print("Email input not found. You might be already logged in or there is a cookie banner / redirect.")

        print("\n=======================================================================")
        print("Waiting for login to complete...")
        print("Please solve the Captcha/Security Check/2FA on the Chrome window now.")
        print("The script will automatically detect when you reach the home feed.")
        print("=======================================================================\n")
        
        logged_in = False
        # Loop for up to 5 minutes (60 iterations * 5 seconds = 300 seconds)
        for i in range(60):
            await asyncio.sleep(5)
            url = page.url
            title = await page.title()
            print(f"[{i*5}s] URL: {url} | Title: {title}")
            
            await page.screenshot(path=screenshot_path)
            
            # Check for logged in elements:
            # 1. Look for search input
            search_input = await page.query_selector('input[placeholder*="Tìm kiếm"], input[placeholder*="Search"]')
            # 2. Look for role="feed" or post box
            feed = await page.query_selector('div[role="feed"]')
            post_box = await page.query_selector('text="bạn đang nghĩ gì thế", text="What\'s on your mind"')
            # 3. Look for profile link
            profile = await page.query_selector('a[href*="/me/"], a[aria-label*="Trang cá nhân"]')
            
            # If we detect any logged in elements, and we aren't on checkpoints/verification pages
            is_checkpoint = "checkpoint" in url or "two_step_verification" in url or "challenge" in url
            if (search_input or feed or post_box or profile) and not is_checkpoint:
                print("\n🎉 Logged in successfully!")
                logged_in = True
                break
        
        if logged_in:
            print("Waiting 5 seconds for session cookies to settle...")
            await asyncio.sleep(5)
            
            cookies = await context.cookies()
            os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
            with open(cookies_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            print(f"Cookies saved successfully to {cookies_path}")
        else:
            print("Login timed out or failed. Please check login_progress.png to see what's on screen.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
