import asyncio
import random
import math
from playwright.async_api import async_playwright, Page
from models import Lead
from config import BARK_EMAIL, BARK_PASSWORD
import logging

logger = logging.getLogger(__name__)


async def human_delay(min_ms: int = 500, max_ms: int = 2500):
    """Random delay to mimic human reading/thinking time."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def move_mouse_humanly(page: Page, target_x: int, target_y: int):
    """
    Simulate a bezier-curved mouse path instead of teleporting.
    Real humans never move in straight lines.
    """
    current = await page.evaluate("() => ({x: window.mouseX || 100, y: window.mouseY || 100})")
    cx, cy = current.get("x", 100), current.get("y", 100)

    # Bezier control points for natural arc
    cp1x = cx + random.randint(-100, 100)
    cp1y = cy + random.randint(-80, 80)
    cp2x = target_x + random.randint(-50, 50)
    cp2y = target_y + random.randint(-50, 50)

    steps = random.randint(20, 40)
    for i in range(steps + 1):
        t = i / steps
        # Cubic bezier formula
        x = (1-t)**3 * cx + 3*(1-t)**2*t * cp1x + 3*(1-t)*t**2 * cp2x + t**3 * target_x
        y = (1-t)**3 * cy + 3*(1-t)**2*t * cp1y + 3*(1-t)*t**2 * cp2y + t**3 * target_y
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.02))


async def human_type(page: Page, selector: str, text: str):
    """Type with variable speed between keystrokes like a real person."""
    await page.click(selector)
    await human_delay(300, 800)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.25))
        # Occasionally pause longer (thinking)
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.3, 0.8))


class BarkScraper:
    def __init__(self):
        self.browser = None
        self.page = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Set True in prod; False helps debug
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        # Use a realistic viewport and user agent
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-GB",
            timezone_id="Europe/London",
        )
        # Remove webdriver property that bots check for
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, *args):
        await self.browser.close()
        await self.playwright.stop()

    async def login(self):
        logger.info("Navigating to Bark login...")
        await self.page.goto("https://www.bark.com/en/gb/login/", wait_until="networkidle")
        await human_delay(1000, 2000)

        # Scroll slightly first (humans don't immediately click)
        await self.page.evaluate("window.scrollBy(0, 100)")
        await human_delay(500, 1000)

        await human_type(self.page, 'input[name="email"]', BARK_EMAIL)
        await human_delay(400, 900)
        await human_type(self.page, 'input[name="password"]', BARK_PASSWORD)
        await human_delay(600, 1200)

        # Move mouse to button before clicking
        btn = await self.page.query_selector('button[type="submit"]')
        bbox = await btn.bounding_box()
        await move_mouse_humanly(self.page, int(bbox["x"] + bbox["width"]/2), int(bbox["y"] + bbox["height"]/2))
        await human_delay(200, 500)
        await btn.click()

        await self.page.wait_for_load_state("networkidle")
        logger.info("Login complete.")

    async def get_leads(self, max_leads: int = 20) -> list[Lead]:
        """Navigate to buyer requests and extract lead data."""
        await self.page.goto("https://www.bark.com/en/gb/pro/leads/", wait_until="networkidle")
        await human_delay(1500, 3000)

        # Scroll to trigger dynamic content loading
        for _ in range(3):
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await human_delay(800, 1500)

        leads = []
        # NOTE: Selectors below are illustrative — update to match current Bark DOM
        lead_cards = await self.page.query_selector_all(".lead-card, [data-testid='lead-item']")

        for card in lead_cards[:max_leads]:
            try:
                title = await card.query_selector(".lead-title, h3")
                description = await card.query_selector(".lead-description, .description")
                budget = await card.query_selector(".lead-budget, .budget")
                location = await card.query_selector(".lead-location, .location")

                lead = Lead(
                    title=await title.inner_text() if title else "N/A",
                    description=await description.inner_text() if description else "N/A",
                    budget=await budget.inner_text() if budget else "N/A",
                    location=await location.inner_text() if location else "N/A",
                    url=self.page.url,
                )
                leads.append(lead)

                # Random delay between reading each card
                await human_delay(200, 600)
            except Exception as e:
                logger.warning(f"Failed to parse lead card: {e}")

        logger.info(f"Extracted {len(leads)} leads.")
        return leads