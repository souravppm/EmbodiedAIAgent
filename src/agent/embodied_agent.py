# src/agent/embodied_agent.py
import json
import re
import ollama
from tools.browser_env import BrowserEnvironment
from core.prompts import SYSTEM_PROMPT

class EmbodiedAgent:
    def __init__(self, objective: str):
        self.objective = objective
        self.env = BrowserEnvironment(headless=False)
        self.current_step = 0
        self.max_steps = 10
        self.vision_model = "llama3.2-vision" # Our local engine
        
    def get_model_action(self, image_path: str) -> dict:
        print(f"[Brain] Sending visual data to {self.vision_model}...")
        
        # Build the prompt with history
        full_prompt = f"{SYSTEM_PROMPT}\n\nUSER OBJECTIVE: {self.objective}"
        
        # Add memory of the last action to prevent loops
        if hasattr(self, 'last_action'):
            full_prompt += f"\n\nYOUR PREVIOUS ACTION WAS: {json.dumps(self.last_action)}. If the screen looks exactly the same, you MUST try clicking somewhere else or scrolling."

        try:
            # Calling local Ollama
            response = ollama.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': full_prompt,
                    'images': [image_path]
                }]
            )
            
            raw_text = response['message']['content']
            json_str = ""
            
            # --- FAANG-Level Robust JSON Extraction ---
            # 1. Try to extract from Markdown code blocks first
            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                # Sometimes models just use ``` without the 'json' tag
                json_str = raw_text.split("```")[1].split("```")[0].strip()
            else:
                # 2. Fallback to a non-greedy regex (.*? instead of .*)
                json_match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
            
            # 3. Safely parse the extracted string
            if json_str:
                action_data = json.loads(json_str)
                self.last_action = action_data # Save memory
                return action_data
            else:
                print(f"[Error] Could not locate JSON structure. Raw output:\n{raw_text}")
                return {"action": "done", "thought": "Failed to extract JSON, stopping."}
                
        except json.JSONDecodeError as e:
            print(f"[Parse Error] The model output invalid JSON: {e}\nRaw output: {raw_text}")
            return {"action": "done", "thought": "Invalid JSON format, stopping."}
            
        except Exception as e:
            print(f"[System Error] {e}")
            return {"action": "done", "thought": "System error, stopping."}

    def execute_action(self, action_data: dict):
        action = action_data.get("action")
        
        if action == "click":
            print(f"[Action] Clicking at ({action_data.get('x')}, {action_data.get('y')})")
            self.env.page.mouse.click(action_data['x'], action_data['y'])
            
        elif action == "type":
            print(f"[Action] Clicking and typing '{action_data.get('text')}'")
            self.env.page.mouse.click(action_data['x'], action_data['y'])
            self.env.page.keyboard.type(action_data['text'])
            
        elif action == "scroll":
            print(f"[Action] Scrolling {action_data.get('direction')}")
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
            print(f"[Thought] {action_data.get('thought', 'No thought provided')}")
            
            # 3. Act (Execute in browser)
            if action_data.get("action") == "done":
                break
                
            self.execute_action(action_data)
            
            # Re-observe for the next loop
            self.env.page.screenshot(path="state.png")
            
        print("--- Task Finished or Max Steps Reached ---")
        self.env.close()
