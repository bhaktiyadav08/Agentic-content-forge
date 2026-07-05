# 🛰️ AI Agentic Technical Content Repurposer

## Overview
AI Agentic Technical Content Repurposer is a multi-agent application that automatically converts technical datasets and documentation into platform-specific content.

Users simply provide a Kaggle, GitHub, or documentation URL, and the AI agents analyze the content and generate:

- 📝 Technical Blog
- 💼 LinkedIn Post
- 🐦 X/Twitter Thread
- 📁 GitHub README Summary
- 🎬 YouTube Script Outline
- 🔍 Competitor Intelligence
- ⚙️ Raw Structured Output

---

## Features

- Multi-Agent Workflow using CrewAI
- Automatic webpage scraping with Playwright
- Structured outputs using Pydantic
- Interactive Streamlit dashboard
- Platform-specific content generation
- Competitor content gap analysis

---

## Tech Stack

- Python
- Streamlit
- CrewAI
- OpenRouter (Gemini)
- Playwright
- BeautifulSoup
- Pydantic
- Python-dotenv

---

## Project Structure

```
app.py
dashboard.py
visualizations.py
requirements.txt
README.md
```

---

## Installation

Clone the repository

```bash
git clone <repository-url>
cd kaggle-agent-repurposer
```

Create virtual environment

```bash
python -m venv venv
```

Activate environment

Windows

```bash
venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file

```
OPENROUTER_API_KEY=your_api_key
```

Run the application

```bash
streamlit run dashboard.py
```

---

## Workflow

1. Enter a Kaggle/GitHub/Documentation URL.
2. AI agents scrape and analyze the webpage.
3. Content is generated for multiple platforms.
4. Results are displayed in an interactive dashboard.

---

## Sample Output

- Technical Blog
- LinkedIn Post
- Twitter Thread
- GitHub Summary
- YouTube Script
- Competitor Intelligence

---

## Developed For

AI Agents: Intensive Vibe Coding Capstone Project (Kaggle)
