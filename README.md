# Embodied AI Web Agent (GPT-4o-mini Powered)

An autonomous web agent that can navigate websites, search for information, and complete tasks using GPT-4o-mini's vision capabilities and Playwright.

## 🚀 Features
- **Vision-Driven Navigation:** Uses Set-of-Mark (SoM) to label UI elements for the AI.
- **Fast Execution:** Powered by OpenAI's gpt-4o-mini for near-instant decisions.
- **Robust Parsing:** Advanced JSON extraction to prevent agent crashes.
- **Secure Architecture:** Uses `.env` for API key management.

## 🛠️ Setup
1. Clone the repo.
2. Install dependencies: `pip install -r requirements.txt`
3. Setup Playwright: `playwright install chromium`
4. Create a `.env` file and add your key: `OPENAI_API_KEY=your_key_here`

## 🏃 Usage
```bash
python src/main.py --url "https://github.com" --task "Find the top trending repositories"
```
