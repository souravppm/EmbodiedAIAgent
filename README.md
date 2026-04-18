# Embodied AI Agent

An open-source, locally-hosted multimodal AI agent designed to navigate and interact with web environments autonomously. 

## 🚀 The Vision
Standard LLMs can chat, but they cannot act. This project builds an "Embodied" agent equipped with **vision** (to perceive the screen) and **action** frameworks (to click, type, and navigate) to solve real-world workflows entirely locally, ensuring privacy and zero API costs.

## 🧠 System Architecture
We follow a modular `Input -> Processing -> Output` pipeline:
- **Perception (Brain):** Local Vision-Language Models (currently `llama3.2-vision` via Ollama) running efficiently on consumer GPUs (e.g., RTX 4060).
- **Action (Body):** Playwright for robust web automation and DOM manipulation.
- **Design Pattern:** Observe ➔ Think ➔ Act cycle with robust JSON-parsing and error recovery.

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed on your system.

### 2. Install the Vision Model
Pull the lightweight vision model using Ollama:
```bash
ollama run llama3.2-vision
```

### 3. Install Dependencies
Clone the repository and set up your environment:

```bash
python -m venv venv
# Activate the environment (Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate)

pip install -r requirements.txt
playwright install chromium
```

### 4. Run the Agent
```bash
python src/main.py
```

## 🚧 Current Roadmap & Engineering Challenges
- [x] Phase 1: Core framework setup (Playwright + Local VLM loop).
- [x] Phase 2: Robust JSON instruction parsing and memory state.
- [ ] Phase 3 (Current): Standard VLMs struggle with pixel-perfect coordinate generation. Implementing "Set-of-Mark" (SoM) prompting via JavaScript injection to map UI elements to ID numbers, eliminating spatial hallucination.
