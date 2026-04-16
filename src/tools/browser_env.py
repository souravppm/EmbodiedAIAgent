# src/tools/browser_env.py
from playwright.sync_api import sync_playwright

class BrowserEnvironment:
    def __init__(self, headless=False):
        """
        Initializes the browser environment.
        headless=False lets us actually watch the AI move the mouse and click!
        """
        self.playwright = sync_playwright().start()
        # Launch Chromium. We keep it visible for debugging.
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self.page = self.context.new_page()

    def navigate_and_capture(self, url: str, output_image: str = "state.png"):
        """Navigates to a URL and takes a snapshot of the current state."""
        print(f"[System] Navigating to {url}...")
        self.page.goto(url, wait_until="networkidle")
        
        # Take a screenshot - this is the "Eye" input for our AI model later
        self.page.screenshot(path=output_image)
        print(f"[System] Vision state captured and saved to {output_image}")

    def close(self):
        self.browser.close()
        self.playwright.stop()
