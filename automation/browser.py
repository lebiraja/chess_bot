"""
Browser Controller for Chess.com Automation

Manages the Playwright browser instance for interacting with chess.com.
Uses persistent context to save login sessions.
"""
import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserController:
    """
    Controls the browser for chess.com interaction.

    Uses Playwright to automate Chrome browser actions.
    Uses persistent context to save cookies/login between sessions.
    """

    def __init__(self, headless: bool = False, user_data_dir: Optional[Path] = None):
        """
        Initialize the browser controller.

        Args:
            headless: If True, run browser without visible window
            user_data_dir: Directory to store browser data (cookies, cache, etc.)
                          If None, uses ~/.chess-bot/browser-data
        """
        self.headless = headless
        self.user_data_dir = user_data_dir or Path.home() / ".chess-bot" / "browser-data"
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def initialize(self, url: str = "https://www.chess.com/play/online"):
        """
        Initialize the browser and navigate to chess.com.

        Uses persistent context to remember login sessions.

        Args:
            url: The URL to navigate to
        """
        # Ensure user data directory exists
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        self.playwright = await async_playwright().start()

        # Use launch_persistent_context to save cookies/session between runs
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Get or create the first page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        # Remove webdriver flag
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        # Navigate to chess.com with longer timeout and simpler wait
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Initial navigation warning (may be ok): {e}")

        # Give page time to settle after any redirects
        await asyncio.sleep(2)

        # Wait for page to be ready
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass  # May already be loaded

        print(f"Browser initialized and navigated to {url}")
        print(f"Session data saved to: {self.user_data_dir}")
        print("(Your login will be remembered for next time)")

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
                await self.page.wait_for_selector(
                    selector, timeout=timeout / len(selectors)
                )
                print(f"Found chess board with selector: {selector}")
                return
            except Exception:
                continue

        raise TimeoutError("Could not find chess board on page")

    async def wait_for_stable_page(self, timeout: float = 10.0):
        """
        Wait for the page to stop navigating/loading.

        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Check if page is still navigating
                await self.page.wait_for_load_state("domcontentloaded", timeout=1000)
                return
            except Exception:
                await asyncio.sleep(0.5)

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
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass  # May already be closed

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        print("Browser closed")

    async def refresh(self):
        """Refresh the current page."""
        if self.page:
            try:
                await self.page.reload(wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"Refresh warning: {e}")

    async def safe_query_selector(self, selector: str):
        """
        Safely find an element, handling navigation errors.

        Args:
            selector: CSS selector

        Returns:
            Element handle or None
        """
        if self.page is None:
            return None
        try:
            return await self.page.query_selector(selector)
        except Exception:
            # Page may have navigated, wait and retry
            await asyncio.sleep(0.5)
            try:
                return await self.page.query_selector(selector)
            except Exception:
                return None

    async def safe_query_selector_all(self, selector: str):
        """
        Safely find all matching elements, handling navigation errors.

        Args:
            selector: CSS selector

        Returns:
            List of element handles or empty list
        """
        if self.page is None:
            return []
        try:
            return await self.page.query_selector_all(selector)
        except Exception:
            await asyncio.sleep(0.5)
            try:
                return await self.page.query_selector_all(selector)
            except Exception:
                return []

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
