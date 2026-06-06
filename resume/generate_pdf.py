import asyncio
import os
from playwright.async_api import async_playwright

async def generate_pdf(html_path, pdf_path):
    print(f"Generating PDF for {html_path} -> {pdf_path}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # Open the local HTML file using absolute file:// URI
        abs_html_path = os.path.abspath(html_path)
        await page.goto(f"file://{abs_html_path}")
        # Wait a bit for font loading/layout
        await page.wait_for_timeout(1000)
        # Print to PDF with default print media and options matching resume style
        await page.pdf(
            path=pdf_path,
            format="letter",
            print_background=True,
            display_header_footer=False,
            margin={"top": "0in", "bottom": "0in", "left": "0in", "right": "0in"} # Margins are handled by CSS @page
        )
        await browser.close()
    print(f"Successfully generated {pdf_path}")

async def main():
    resume_dir = os.path.dirname(os.path.abspath(__file__))
    cv_en_html = os.path.join(resume_dir, "cv.html")
    cv_en_pdf = os.path.join(resume_dir, "cv.pdf")
    cv_vi_html = os.path.join(resume_dir, "cv_vi.html")
    cv_vi_pdf = os.path.join(resume_dir, "cv_vi.pdf")
    
    await generate_pdf(cv_en_html, cv_en_pdf)
    await generate_pdf(cv_vi_html, cv_vi_pdf)

if __name__ == "__main__":
    asyncio.run(main())
