from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from playwright.async_api import async_playwright

app = FastAPI(title="Dynamic HTML Renderer")
app.add_middleware(GZipMiddleware, minimum_size=500)

BLOCKED_RESOURCE_TYPES = [
    "image", "font", "media", "track", "manifest", "serviceworker",
    "ping", "beacon"
]

BLOCKED_DOMAINS = [
    "googletagmanager.com", "google-analytics.com", "doubleclick.net",
    "adservice.google.com", "ads.yahoo.com", "facebook.net",
    "scorecardresearch.com", "quantserve.com", "zedo.com"
]

@app.get("/render", response_class=PlainTextResponse)
async def render_page(url: str = Query(..., description="Full URL to render")):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def intercept(route):
            req = route.request
            if req.resource_type in BLOCKED_RESOURCE_TYPES or any(d in req.url for d in BLOCKED_DOMAINS):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", intercept)

        try:
            await page.goto(url, wait_until="networkidle", timeout=25000)
            html = await page.content()
        except Exception as e:
            html = f"Error: {str(e)}"
        finally:
            await browser.close()

        return html

@app.get("/")
async def root():
    return {"status": "ok", "message": "Use /render?url=https://example.com"}
