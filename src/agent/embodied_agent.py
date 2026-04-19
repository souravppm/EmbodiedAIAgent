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
        
        # Build the prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\nUSER OBJECTIVE: {self.objective}"
        
        # Smart Memory Injection (No Panicking)
        if hasattr(self, 'last_action') and self.last_action:
            full_prompt += f"\n\n[MEMORY] Your last action was: {json.dumps(self.last_action)}.\nEvaluate the new screenshot carefully. If your last action opened a new menu or changed the screen, continue your plan. ONLY pick a different action if you are completely stuck in a loop."

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
            
            # --- FAANG-Level Bulletproof JSON Extraction ---
            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_str = raw_text.split("```")[1].split("```")[0].strip()
            else:
                json_match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
            
            # --- THE ULTIMATE MULTI-JSON FIX ---
            # If the model gives us two JSONs, we chop off everything after the very first '}'
            if json_str and "}" in json_str:
                json_str = json_str.split("}")[0] + "}"
                
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
        
        # 1. Extract the Set-of-Mark Element ID
        element_id = action_data.get("element_id")
        x, y = None, None
        
        if element_id is not None:
            # Playwright evaluates JS objects with string keys, so we convert the ID to a string
            coords = self.env.elements_mapping.get(str(element_id))
            if coords:
                x = coords['x']
                y = coords['y']
            else:
                print(f"[Warning] Model hallucinated an invalid ID: {element_id}. Skipping click.")
                return # Skip to the next loop so it doesn't crash
                
        # 2. Execute the Playwright Commands
        if action == "click":
            print(f"[Action] Clicking Box [{element_id}] at exactly ({x}, {y})")
            if x and y:
                self.env.page.mouse.click(x, y)
                
        elif action == "type":
            text_to_type = action_data.get('text', '')
            print(f"[Action] Clicking Box [{element_id}] and typing '{text_to_type}'")
            if x and y:
                self.env.page.mouse.click(x, y)
                self.env.page.keyboard.press("Control+A")
                self.env.page.keyboard.press("Backspace")
                
                # NEW: Type with a 100ms delay between keys, like a human
                self.env.page.keyboard.type(text_to_type, delay=100) 
                
                # NEW: Wait half a second before hitting enter, so the UI catches up
                self.env.page.wait_for_timeout(500) 
                self.env.page.keyboard.press("Enter")
                
        elif action == "scroll":
            print(f"[Action] Scrolling {action_data.get('direction')}")
            delta = 500 if action_data.get('direction') == "down" else -500
            self.env.page.mouse.wheel(0, delta)
            
        elif action == "done":
            print("[System] Agent claims the task is complete!")
            
        # Give the browser time to process the click/typing/network load
        self.env.page.wait_for_timeout(4000) # Increased to 4 seconds

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
            
            # Re-observe for the next loop (CRITICAL)
            self.env.capture_current_state("state.png") 
            
        print("--- Task Finished or Max Steps Reached ---")
        self.env.close()
