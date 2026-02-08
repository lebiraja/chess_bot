"""
Browser Controller for Chess.com Automation

Manages the Playwright browser instance for interacting with chess.com.
"""
import asyncio
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserController:
    """
    Controls the browser for chess.com interaction.

    Uses Playwright to automate Chrome browser actions.
    """

    def __init__(self, headless: bool = False):
        """
        Initialize the browser controller.

        Args:
            headless: If True, run browser without visible window
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def initialize(self, url: str = "https://www.chess.com/play/online"):
        """
        Initialize the browser and navigate to chess.com.

        Args:
            url: The URL to navigate to
        """
        self.playwright = await async_playwright().start()

        # Launch Chrome with anti-detection flags
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Create page
        self.page = await self.context.new_page()

        # Remove webdriver flag
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        # Navigate to chess.com
        await self.page.goto(url, wait_until="networkidle")

        # Wait for the page to fully load
        await self.page.wait_for_load_state("domcontentloaded")

        print(f"Browser initialized and navigated to {url}")

    async def wait_for_board(self, timeout: float = 60000):
        """
        Wait for the chess board to appear on the page.

        Args:
            timeout: Maximum time to wait in milliseconds
        """
        # Try different selectors for the board
        selectors = [
            "chess-board",
            "wc-chess-board",
            ".board",
            "#board-single",
            '[class*="board"]',
        ]

        for selector in selectors:
            try:
                await self.page.wait_for_selector(selector, timeout=timeout / len(selectors))
                print(f"Found chess board with selector: {selector}")
                return
            except Exception:
                continue

        raise TimeoutError("Could not find chess board on page")

    async def get_page(self) -> Page:
        """Get the current page instance."""
        if self.page is None:
            raise RuntimeError("Browser not initialized. Call initialize() first.")
        return self.page

    async def screenshot(self, path: str = "screenshot.png"):
        """Take a screenshot of the current page."""
        if self.page:
            await self.page.screenshot(path=path)
            print(f"Screenshot saved to {path}")

    async def close(self):
        """Close the browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        print("Browser closed")

    async def refresh(self):
        """Refresh the current page."""
        if self.page:
            await self.page.reload(wait_until="networkidle")

    async def evaluate(self, expression: str):
        """
        Evaluate JavaScript expression on the page.

        Args:
            expression: JavaScript code to evaluate

        Returns:
            Result of the JavaScript evaluation
        """
        if self.page is None:
            raise RuntimeError("Browser not initialized")
        return await self.page.evaluate(expression)

    async def click(self, selector: str):
        """
        Click an element on the page.

        Args:
            selector: CSS selector for the element to click
        """
        if self.page is None:
            raise RuntimeError("Browser not initialized")
        await self.page.click(selector)

    async def query_selector(self, selector: str):
        """
        Find an element on the page.

        Args:
            selector: CSS selector

        Returns:
            Element handle or None
        """
        if self.page is None:
            raise RuntimeError("Browser not initialized")
        return await self.page.query_selector(selector)

    async def query_selector_all(self, selector: str):
        """
        Find all matching elements on the page.

        Args:
            selector: CSS selector

        Returns:
            List of element handles
        """
        if self.page is None:
            raise RuntimeError("Browser not initialized")
        return await self.page.query_selector_all(selector)
