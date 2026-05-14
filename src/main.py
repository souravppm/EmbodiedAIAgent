# src/main.py
import argparse
from agent.embodied_agent import EmbodiedAgent

def main():
    # Set up the CLI argument parser
    parser = argparse.ArgumentParser(description="Run the Embodied AI Web Agent.")
    
    # Define the arguments the user can pass
    parser.add_argument(
        "--url", 
        type=str, 
        required=True, 
        help="The starting URL for the agent (e.g., https://github.com)"
    )
    
    parser.add_argument(
        "--task", 
        type=str, 
        required=True, 
        help="The objective you want the agent to achieve."
    )
    
    parser.add_argument(
        "--headless", 
        action="store_true", 
        help="Run the browser in the background without a UI."
    )

    # Parse the arguments from the terminal
    args = parser.parse_args()

    print(f"\n🚀 Booting up Embodied Agent...")
    print(f"🌍 Target URL: {args.url}")
    print(f"🎯 Objective: {args.task}\n")

    # Initialize and run the agent with the user's inputs
    agent = EmbodiedAgent(
        objective=args.task,
        headless=args.headless
    )
    
    try:
        agent.run(start_url=args.url)
    except KeyboardInterrupt:
        print("\n[System] Agent stopped by user.")
    finally:
        agent.env.close()

if __name__ == "__main__":
    main()
