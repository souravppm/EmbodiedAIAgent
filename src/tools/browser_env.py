# src/tools/browser_env.py
from playwright.sync_api import sync_playwright

class BrowserEnvironment:
    def __init__(self, headless=False):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 720})
        self.page = self.context.new_page()
        self.elements_mapping = {} # Stores ID -> (x, y)

    def navigate_and_capture(self, url: str, output_image: str = "state.png"):
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

    def capture_current_state(self, output_image: str = "state.png"):
        """Call this after an action to get the fresh screen with new boxes."""
        self.page.wait_for_timeout(2500)
        self.inject_set_of_mark()
        self.page.screenshot(path=output_image)
        
    def inject_set_of_mark(self):
        """Injects JS to draw numbered boxes on clickable elements and returns their coordinates."""
        print("[System] Injecting Set-of-Mark bounding boxes...")
        
        # This JavaScript finds all buttons/links/inputs and draws a numbered box over them
        js_code = """
        () => {
            document.querySelectorAll('.som-box').forEach(e => e.remove());
            let idCounter = 1;
            let elementsMap = {};
            
            // Prioritize inputs, textareas, and main buttons over generic links
            let elements = document.querySelectorAll('input, textarea, button, [role="button"], a');
            
            elements.forEach(el => {
                let rect = el.getBoundingClientRect();
                
                // STRICT FILTER: Only label it if it's actually big enough to matter (removes tiny useless links)
                let isInput = el.tagName.toLowerCase() === 'input';
                let isLargeEnough = rect.width > 25 && rect.height > 20; 
                let isVisible = rect.top >= 0 && rect.left >= 0 && el.style.visibility !== 'hidden';

                if (isVisible && (isInput || isLargeEnough)) { 
                    let div = document.createElement('div');
                    div.className = 'som-box';
                    div.style.position = 'fixed';
                    div.style.top = rect.top + 'px';
                    div.style.left = rect.left + 'px';
                    div.style.border = '2px solid red';
                    div.style.backgroundColor = 'rgba(255, 255, 0, 0.9)';
                    div.style.color = 'black';
                    div.style.fontWeight = 'bold';
                    div.style.fontSize = '14px'; // Made text slightly bigger for the AI
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

    def close(self):
        self.browser.close()
        self.playwright.stop()
