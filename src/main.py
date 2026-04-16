# src/main.py
from tools.browser_env import BrowserEnvironment

def main():
    print("--- Booting Embodied AI Agent ---")
    
    # Initialize the body
    env = BrowserEnvironment(headless=False)
    
    try:
        # Let's test its eyes on a simple website first
        env.navigate_and_capture("https://github.com", "github_state.png")
        print("Success! Check your folder for 'github_state.png'")
        
    finally:
        # Always clean up
        env.close()

if __name__ == "__main__":
    main()
