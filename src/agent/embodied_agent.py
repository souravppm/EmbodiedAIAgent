import os
import re
import json
import base64
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from openai import OpenAI

from tools.browser_env import BrowserEnvironment

load_dotenv()

class EmbodiedAgent:
    def __init__(self, objective: str, headless: bool = False) -> None:
        self.objective: str = objective
        self.env: BrowserEnvironment = BrowserEnvironment(headless=headless)
        self.current_step: int = 0
        self.max_steps: int = 15 
        self.last_action: Optional[Dict[str, Any]] = None
        self.run_history: List[Dict[str, Any]] = []

    def encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_model_action(self, image_path: str) -> Dict[str, Any]:
        print("[Brain] Sending visual data to gpt-4o-mini...")
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        base64_image = self.encode_image(image_path)
        
        system_prompt = (
            "You are an advanced Embodied AI Web Agent. "
            "Your goal is to navigate the web to solve the user's task.\n"
            "Rules:\n"
            "1. Respond ONLY with a single JSON object.\n"
            "2. Format: {\"thought\": \"your reasoning\", \"action\": \"click/type/scroll/done\", \"element_id\": number, \"text\": \"optional\"}\n"
            "3. Prioritize input boxes for searching.\n"
            "4. If the task is finished, use action \"done\"."
        )

        full_prompt = f"{system_prompt}\n\nUSER OBJECTIVE: {self.objective}"
        
        if self.last_action:
            full_prompt += f"\n\n[MEMORY] Your last action was: {json.dumps(self.last_action)}."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": full_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ],
                    }
                ],
                max_tokens=300
            )
            
            raw_text = response.choices[0].message.content or ""
            
            # Robust JSON parsing
            json_str = ""
            json_match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            
            if json_str:
                return json.loads(json_str)
            return {"thought": "Failed to parse JSON", "action": "done"}
            
        except Exception as e:
            print(f"[Error] AI request failed: {e}")
            return {"thought": "Error occurred", "action": "done"}

    def execute_action(self, action_data: Dict[str, Any]) -> None:
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

    def run(self, start_url: str) -> None:
        """The main Observe -> Think -> Act loop."""
        print(f"--- Starting Task: {self.objective} ---")
        self.env.navigate_and_capture(start_url, "state.png")
        
        while self.current_step < self.max_steps:
            self.current_step += 1
            print(f"\n--- Step {self.current_step} ---")
            
            # 1. Observe (Already done initially, or at the end of last loop)
            # 2. Think (Send screenshot to VLM)
            action_data = self.get_model_action("state.png")
            thought = action_data.get('thought', 'No thought provided')
            print(f"[Thought] {thought}")
            
            # Save to history
            self.run_history.append({
                "step": self.current_step,
                "thought": thought,
                "action": action_data
            })
            
            # 3. Act (Execute in browser)
            if action_data.get("action") == "done":
                print("[System] Agent claims the task is complete!")
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
        self.env.close()
        
        # NEW: Generate the final report
        self.save_report()

    def save_report(self) -> None:
        """Generates a clean markdown report of the AI's actions."""
        print("\n[System] Generating Run Report...")
        with open("run_report.md", "w", encoding="utf-8") as f:
            f.write(f"# Embodied AI Run Report\n\n")
            f.write(f"**Objective:** {self.objective}\n\n")
            for item in self.run_history:
                f.write(f"### Step {item['step']}\n")
                f.write(f"**Thought:** {item['thought']}\n")
                f.write(f"**Action Executed:** `{item['action']}`\n\n")
        print("[System] Report saved to run_report.md! 🚀")
