# src/main.py
from agent.embodied_agent import EmbodiedAgent

def main():
    objective = "Go to github and find the top trending repository."
    agent = EmbodiedAgent(objective=objective)
    
    # Start the agent on GitHub
    agent.run(start_url="https://github.com")

if __name__ == "__main__":
    main()
