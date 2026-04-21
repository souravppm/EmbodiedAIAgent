# src/agent/embodied_agent.py
import json
import re
import ollama
from tools.browser_env import BrowserEnvironment
from core.prompts import SYSTEM_PROMPT

class EmbodiedAgent:
    def __init__(self, objective: str, vision_model: str = "llama3.2-vision", headless: bool = False):
        self.objective = objective
        self.vision_model = vision_model
        
        # Pass the headless flag to our browser environment
        self.env = BrowserEnvironment(headless=headless)
        
        self.current_step = 0
        self.max_steps = 15 # Give it enough steps to complete longer tasks
        self.last_action = None
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
            json_str = ""
            # Find the very first '{' and the very last '}' in the entire text
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                
            # THE ULTIMATE MULTI-JSON FIX
            if json_str and "}\n{" in json_str.replace(" ", ""):
                json_str = json_str.split("}")[0] + "}"
                
            # 3. Safely parse the extracted string
            if json_str:
                action_data = json.loads(json_str)
                # Removed: self.last_action = action_data (Moved to run() loop)
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
                
                # Type like a human
                self.env.page.keyboard.type(text_to_type, delay=100) 
                
                # CRITICAL: Force the submission
                self.env.page.wait_for_timeout(1000) 
                self.env.page.keyboard.press("Enter")
                self.env.page.wait_for_timeout(1000) # Wait for React UI
                self.env.page.keyboard.press("Enter") # Double tap to force search
                
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
                
            # --- FAANG LEVEL GUARDRAIL: Anti-Loop Protection ---
            if hasattr(self, 'last_action') and self.last_action:
                last_id = self.last_action.get("element_id")
                current_id = action_data.get("element_id")
                action_type = action_data.get("action")
                
                if action_type == "click" and last_id == current_id:
                    print(f"[System Guardrail] Loop detected on Box [{current_id}]. Pressing ESCAPE to clear modals.")
                    # Instead of scrolling down to marketing garbage, we press Escape to close broken dropdowns
                    action_data = {"action": "type", "element_id": current_id, "text": ""} # Dummy action
                    self.env.page.keyboard.press("Escape")
                    self.env.page.wait_for_timeout(1000)
            # ---------------------------------------------------
                
            self.execute_action(action_data)
            
            # NEW: Save the memory HERE, after everything is done!
            self.last_action = action_data 
            
            self.env.capture_current_state("state.png") 
            
        print("--- Task Finished ---")
