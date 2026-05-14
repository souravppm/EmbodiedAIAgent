# src/tools/browser_env.py
from typing import Dict, Any
from playwright.sync_api import sync_playwright

class BrowserEnvironment:
    def __init__(self, headless: bool = False) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 720})
        self.page = self.context.new_page()
        self.elements_mapping: Dict[str, Any] = {} # Stores ID -> (x, y)

    def navigate_and_capture(self, url: str, output_image: str = "state.png") -> None:
        print(f"[System] Navigating to {url}...")
        try:
            self.page.goto(url, wait_until="load", timeout=60000)
            self.page.wait_for_timeout(2000) # Give it 2 extra seconds for animations to settle
        except Exception as e:
            print(f"[Warning] Page load timeout or error, but continuing: {e}")
        
        # Inject Set-of-Mark before taking the screenshot
        self.page.wait_for_timeout(2500)
        self.inject_set_of_mark()
        
        self.page.screenshot(path=output_image)
        print(f"[System] Vision state with SOM captured and saved to {output_image}")

    def capture_current_state(self, output_image: str = "state.png") -> None:
        """Call this after an action to get the fresh screen with new boxes."""
        self.page.wait_for_timeout(2500)
        self.inject_set_of_mark()
        self.page.screenshot(path=output_image)
        
    def inject_set_of_mark(self) -> None:
        """Injects JS to draw numbered boxes on clickable elements and returns their coordinates."""
        print("[System] Injecting Set-of-Mark bounding boxes...")
        
        # This JavaScript finds all buttons/links/inputs and draws a numbered box over them
        js_code = """
        () => {
            document.querySelectorAll('.som-box').forEach(e => e.remove());
            let idCounter = 1;
            let elementsMap = {};
            
            let elements = document.querySelectorAll('input, textarea, button, [role="button"], a');
            
            elements.forEach(el => {
                // THE HARD CAP: Never draw more than 60 boxes to save AI context and VRAM
                if (idCounter > 60) return; 

                let rect = el.getBoundingClientRect();
                
                // Only label standard inputs or reasonably sized links
                let isInput = el.tagName.toLowerCase() === 'input';
                let isLargeEnough = rect.width > 20 && rect.height > 15; 
                let isVisible = el.style.visibility !== 'hidden' && el.style.display !== 'none';

                // THE CULLING: Only tag elements that are physically inside the current screen view!
                let inViewport = (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );

                if (isVisible && inViewport && (isInput || isLargeEnough)) { 
                    let div = document.createElement('div');
                    div.className = 'som-box';
                    div.style.position = 'fixed';
                    div.style.top = rect.top + 'px';
                    div.style.left = rect.left + 'px';
                    div.style.border = '2px solid red';
                    div.style.backgroundColor = 'rgba(255, 255, 0, 0.9)';
                    div.style.color = 'black';
                    div.style.fontWeight = 'bold';
                    div.style.fontSize = '14px';
                    div.style.padding = '2px';
                    div.style.zIndex = 9999;
                    div.innerText = idCounter;
                    document.body.appendChild(div);

                    elementsMap[idCounter] = {
                        x: rect.left + (rect.width / 2),
                        y: rect.top + (rect.height / 2)
                    };
                    idCounter++;
                }
            });
            return elementsMap;
        }
        """
        # Execute JS and save the mapping so our Python code knows where ID 5 is
        self.elements_mapping = self.page.evaluate(js_code)

    def close(self) -> None:
        """Safely shuts down the Playwright browser."""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
        except Exception as e:
            # If the event loop is already closed, we just silently ignore it.
            if "Event loop is closed" not in str(e):
                print(f"[Warning] Error during browser shutdown: {e}")
        print("[System] Browser environment closed safely.")
