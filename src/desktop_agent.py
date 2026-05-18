# src/desktop_agent.py
import os
import re
import json
import base64
import time
import pyautogui
from dotenv import load_dotenv
from openai import OpenAI

# Load API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class DesktopAgent:
    def __init__(self, objective: str):
        self.objective = objective
        self.screen_width, self.screen_height = pyautogui.size()
        self.last_action = None  # 🧠 ADD THIS: Initialize memory
        print(f"🖥️ Initialized Desktop Agent on {self.screen_width}x{self.screen_height} screen.")

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_model_action(self, image_path: str):
        print(f"[Brain] Analyzing Desktop with gpt-4o-mini...")
        base64_image = self.encode_image(image_path)
        
        # The Desktop Vision Prompt
        SYSTEM_PROMPT = """You are an advanced Desktop AI Agent. You control the user's actual Windows computer.
        Look at the screenshot and decide the next action to achieve the user's objective.
        
        Rules:
        1. Respond ONLY with a single JSON object.
        2. Format for clicking: {"thought": "...", "action": "click", "x_percent": 50, "y_percent": 50}
        3. Format for typing: {"thought": "...", "action": "type", "text": "your text"}
        4. Format for pressing special keys: {"thought": "...", "action": "press", "key": "win"}
        5. CRITICAL: The Start Menu is NEVER open by default. If you need to search for an app, you MUST use the "press" action with the "win" key first.
        6. If the task is finished, use action "done".
        """

        full_prompt = f"{SYSTEM_PROMPT}\n\nUSER OBJECTIVE: {self.objective}"

        # 🧠 ADD THIS: Remind the AI what it just did so it doesn't loop!
        if self.last_action:
            full_prompt += f"\n\n[MEMORY] Your last action was: {json.dumps(self.last_action)}. DO NOT repeat the exact same action."

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": full_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]}
                ],
                max_tokens=300
            )
            
            raw_text = response.choices[0].message.content
            
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

    def execute_action(self, action_data):
        action = action_data.get("action")
        thought = action_data.get("thought", "")
        print(f"\n[Thought] {thought}")

        if action == "done":
            print("[System] Agent claims the task is complete!")
            return True

        if action == "click":
            x_pct = action_data.get("x_percent", 50)
            y_pct = action_data.get("y_percent", 50)
            
            # Convert percentage to actual pixels
            target_x = (x_pct / 100.0) * self.screen_width
            target_y = (y_pct / 100.0) * self.screen_height
            
            print(f"[Action] Moving mouse to ({target_x:.0f}, {target_y:.0f}) and clicking...")
            pyautogui.moveTo(target_x, target_y, duration=1.0)
            pyautogui.click()

        elif action == "type":
            text = action_data.get("text", "")
            print(f"[Action] Typing: '{text}'")
            
            # Type the text
            pyautogui.write(text, interval=0.05)
            
            # 🧠 ADD THIS PAUSE: Wait for Windows Search to find the app!
            time.sleep(2.0) 
            
            # Now it is safe to press Enter
            pyautogui.press('enter')
            
            # Wait for the app to fully open on the screen
            time.sleep(3.0)

        # Add this NEW block for pressing keys!
        elif action == "press":
            key = action_data.get("key", "enter")
            print(f"[Action] Pressing key: '{key}'")
            pyautogui.press(key)
            time.sleep(1.5) # Wait for the Start Menu to physically open before doing anything else

        return False

    def run(self):
        print(f"--- Starting Desktop Task: {self.objective} ---")
        print("⚠️  WARNING: Keep your hands off the mouse. Press CTRL+C in the terminal to abort!")
        time.sleep(3) # Give user time to minimize windows

        for step in range(5): # Limit to 5 steps for safety
            print(f"\n--- Step {step + 1} ---")
            screenshot_path = "desktop_state.png"
            pyautogui.screenshot().save(screenshot_path)
            
            action_data = self.get_model_action(screenshot_path)
            is_done = self.execute_action(action_data)
            
            # 🧠 ADD THIS: Save the action to memory for the next loop
            self.last_action = action_data 
            
            if is_done:
                break
            
            time.sleep(2) # Wait for the UI to react before taking the next screenshot

if __name__ == "__main__":
    import argparse
    
    # 🛑 THE KILLSWITCH: If the AI goes crazy, slam your physical mouse into 
    # any of the 4 corners of your monitor. This immediately crashes the program.
    pyautogui.FAILSAFE = True 

    # Set up the CLI
    parser = argparse.ArgumentParser(description="Run the Desktop AI Agent.")
    parser.add_argument(
        "--task", 
        type=str, 
        required=True, 
        help="The objective you want the desktop agent to achieve."
    )
    
    args = parser.parse_args()

    # Run the agent
    agent = DesktopAgent(objective=args.task)
    agent.run()
