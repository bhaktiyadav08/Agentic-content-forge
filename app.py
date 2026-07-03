import os
from typing import List
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 1. GEMINI BRAIN
# ============================================================
gemini_brain = LLM(
    model="gemini/gemini-2.0-flash",
    temperature=0.2,
    max_retries=5
)

# ============================================================
# 2. PYDANTIC SCHEMA (8 FIELDS)
# ============================================================
class TechnicalInsightSchema(BaseModel):
    dataset_title: str = Field(
        description="The clean, formal name or primary focus of the analyzed technical source."
    )
    technical_blog_post: str = Field(
        description="A 400-word comprehensive markdown blog post explaining what this dataset is, why it matters, key insights, and potential ML use cases."
    )
    linkedin_promo_post: str = Field(
        description="A high-engagement LinkedIn post featuring a hook, bullet points of findings, and relevant hashtags."
    )
    target_audience: str = Field(
        description="The primary demographic who benefits from this data (e.g., Computer Vision Engineers, Financial Analysts)."
    )
    twitter_thread: str = Field(
        description="A 5-tweet X/Twitter thread with hooks, key insights with numbers, and a CTA. Each tweet under 280 chars with line breaks."
    )
    github_readme_summary: str = Field(
        description="A concise GitHub README-style markdown summary with emoji headers, dataset description, key stats table, feature list, and suggested models."
    )
    youtube_script_outline: str = Field(
        description="A 5-minute YouTube tutorial script outline with timestamps (0:00 Intro, 0:30 Dataset, 1:30 EDA, 3:00 Model, 4:30 Results) and visual cues."
    )
    content_gap_analysis: str = Field(
        description="Analysis of what existing articles on this dataset miss and the unique angle our content takes to stand out."
    )

# ============================================================
# 3. TOOLS
# ============================================================
from crewai.tools import tool
from bs4 import BeautifulSoup
import time
import multiprocessing

def _isolated_playwright_worker(url, return_dict):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=25000)
            time.sleep(3)
            return_dict['html'] = page.content()
            browser.close()
    except Exception as e:
        return_dict['error'] = str(e)

@tool("Universal Tech Webpage Scraper")
def scrape_technical_url(url: str) -> str:
    """Launches a headless browser in a safe, isolated system process to extract raw metadata text from technical web links."""
    try:
        time.sleep(5)
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        process = multiprocessing.Process(target=_isolated_playwright_worker, args=(url, return_dict))
        process.start()
        process.join()
        
        if 'error' in return_dict:
            return f"Scraping error: {return_dict['error']}"
        if 'html' not in return_dict:
            return "Failed to retrieve page content."
            
        soup = BeautifulSoup(return_dict['html'], 'html.parser')
        for element in soup(["script", "style", "footer", "nav", "header", "aside", "svg"]):
            element.extract()
            
        text_content = soup.get_text(separator=' ')
        clean_lines = (line.strip() for line in text_content.splitlines())
        non_empty_chunks = (phrase.strip() for line in clean_lines for phrase in line.split("  "))
        final_clean_text = '\n'.join(chunk for chunk in non_empty_chunks if chunk)
        
        return final_clean_text[:12000]
    except Exception as e:
        return f"Failed to scrape: {str(e)}"

# ============================================================
# 4. AGENTS
# ============================================================
data_analyst = Agent(
    role="Principal Data & Schema Architect",
    goal="Ingest raw webpage text of technical datasets, identify core features/columns, targets, and summarize the underlying technical problem.",
    backstory=(
        "You are an elite data engineer. You instantly spot data distributions, column configurations, "
        "and metadata meanings out of messy, unstructured webpage scrapes. You ignore website menus "
        "and focus purely on hard technical specifications."
    ),
    tools=[scrape_technical_url],
    verbose=True,
    llm=gemini_brain
)

tech_writer = Agent(
    role="Lead Developer Relations Engineer",
    goal="Translate raw column metadata and database schemas into highly engaging, educational technical blog posts and promotional social content.",
    backstory=(
        "You are a veteran Developer Relations (DevRel) writer. You have a knack for taking dense, "
        "boring documentation schemas and turning them into fascinating, readable guides for developers on LinkedIn and Medium. "
        "You know exactly how to structure hooks, line breaks, and clear technical summaries."
    ),
    verbose=True,
    llm=gemini_brain
)

# ============================================================
# 5. CREW BUILDER FUNCTION (for dashboard.py to use)
# ============================================================
def create_crew(target_url: str):
    """Creates and returns the crew for a given URL."""
    
    task_analyze_schema = Task(
        description=(
            f"Visit this live URL: {target_url} and thoroughly extract all information about the "
            "dataset structure, its features, target columns, classification attributes, and documentation summary."
        ),
        expected_output=(
            "A highly organized raw architectural breakdown of the dataset properties, feature rows, "
            "and technical context stripped of webpage clutter."
        ),
        agent=data_analyst
    )

    task_generate_content = Task(
        description=(
            "Review the factual dataset breakdown provided by the analyst. Generate ALL of the following outputs:\n\n"
            "1. TECHNICAL BLOG POST (400+ words): Comprehensive markdown with dataset overview, key insights, ML use cases, and conclusions.\n"
            "2. LINKEDIN PROMOTION: Hook in first 2 lines, 3-4 bullet points of key findings, CTA, and relevant hashtags. Conversational but authoritative.\n"
            "3. TWITTER/X THREAD (5 tweets): Tweet 1 = Hook, Tweet 2-4 = Key insights with specific numbers, Tweet 5 = CTA + link. Each under 280 chars. Use line breaks.\n"
            "4. GITHUB README SUMMARY: Clean markdown with emoji headers, dataset description, key stats table, feature list, and suggested models. Copy-paste ready.\n"
            "5. YOUTUBE SCRIPT OUTLINE: 5-minute tutorial with timestamps (0:00 Intro, 0:30 Dataset Overview, 1:30 EDA Walkthrough, 3:00 Model Building, 4:30 Results). Include visual cues.\n"
            "6. CONTENT GAP ANALYSIS: What do existing articles on this dataset miss? What unique angle should we take to stand out and go viral?"
        ),
        expected_output=(
            "Fully formatted, ready-to-publish educational marketing materials mapping perfectly "
            "to the required TechnicalInsightSchema JSON fields."
        ),
        agent=tech_writer,
        output_json=TechnicalInsightSchema
    )
    
    return Crew(
        agents=[data_analyst, tech_writer],
        tasks=[task_analyze_schema, task_generate_content],
        process=Process.sequential
    )

# For direct testing
if __name__ == "__main__":
    target_url = "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud"
    print("🛰️ Ingesting live data target via Agentic Loop...\n")
    crew = create_crew(target_url)
    final_output = crew.kickoff()
    print("\n🏆 CRITICAL STRUCTURAL OUTPUT SECURED (JSON) 🏆\n")
    print(final_output.raw)