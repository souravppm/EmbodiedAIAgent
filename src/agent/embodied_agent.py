# src/agent/embodied_agent.py
import json
from tools.browser_env import BrowserEnvironment
from core.prompts import SYSTEM_PROMPT

class EmbodiedAgent:
    def __init__(self, objective: str):
        self.objective = objective
        self.env = BrowserEnvironment(headless=False)
        self.current_step = 0
        self.max_steps = 10 # Safety limit so it doesn't loop forever
        
    def get_model_action(self, image_path: str) -> dict:
        """
        TODO: This is where we will connect HY-Embodied-0.5 or Ollama.
        For now, this is a placeholder that mocks an action.
        """
        print("[Brain] Analyzing the screen...")
        # Placeholder: Mocking a decision to click somewhere
        mock_response = {
            "thought": "I see the page loaded. I will click the main button.",
            "action": "click",
            "x": 500,
            "y": 300
        }
        return mock_response

    def execute_action(self, action_data: dict):
        """Translates model JSON into Playwright browser commands."""
        action = action_data.get("action")
        
        if action == "click":
            print(f"[Action] Clicking at ({action_data['x']}, {action_data['y']})")
            self.env.page.mouse.click(action_data['x'], action_data['y'])
            
        elif action == "type":
            print(f"[Action] Clicking and typing '{action_data['text']}'")
            self.env.page.mouse.click(action_data['x'], action_data['y'])
            self.env.page.keyboard.type(action_data['text'])
            
        elif action == "scroll":
            print(f"[Action] Scrolling {action_data['direction']}")
            delta = 500 if action_data['direction'] == "down" else -500
            self.env.page.mouse.wheel(0, delta)
            
        elif action == "done":
            print("[System] Agent claims the task is complete!")
            
        self.env.page.wait_for_timeout(2000) # Wait for page to react

    def run(self, start_url: str):
        """The main Observe -> Think -> Act loop."""
        print(f"--- Starting Task: {self.objective} ---")
        self.env.navigate_and_capture(start_url, "state.png")
        
        while self.current_step < self.max_steps:
            self.current_step += 1
            print(f"\n--- Step {self.current_step} ---")
            
            # 1. Observe (Already done initially, or at the end of last loop)
            # 2. Think (Send screenshot to VLM)
            action_data = self.get_model_action("state.png")
            print(f"[Thought] {action_data['thought']}")
            
            # 3. Act (Execute in browser)
            if action_data["action"] == "done":
                break
                
            self.execute_action(action_data)
            
            # Re-observe for the next loop
            self.env.page.screenshot(path="state.png")
            
        print("--- Task Finished or Max Steps Reached ---")
        self.env.close()
