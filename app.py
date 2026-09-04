import os
from typing import List
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 1. GEMINI BRAIN (BACK TO GEMINI - QUOTA RESETS TOMORROW)
# ============================================================
gemini_brain = LLM(
    model="openrouter/google/gemini-2.5-flash",
    temperature=0.2,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    max_retries=2,
    max_tokens=4000
)

# ============================================================
# 2. PYDANTIC SCHEMA
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
        description="The primary demographic who benefits from this data."
    )
    twitter_thread: str = Field(
        description="A 5-tweet X/Twitter thread with hooks, key insights with numbers, and a CTA. Each tweet under 280 chars."
    )
    github_readme_summary: str = Field(
        description="A concise GitHub README-style markdown summary with emoji headers, dataset description, key stats table, feature list, and suggested models."
    )
    youtube_script_outline: str = Field(
        description="A 5-minute YouTube tutorial script outline with timestamps and visual cues."
    )
    content_gap_analysis: str = Field(
        description="Analysis of what existing articles on this dataset miss and the unique angle to stand out."
    )

# ============================================================
# 3. TOOLS
# ============================================================
from crewai.tools import tool
from bs4 import BeautifulSoup
import time
import multiprocessing

def _isolated_playwright_worker(url, return_dict):
    """An isolated background process worker that handles Playwright."""
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
    """Launches a headless browser to extract raw metadata text from technical web links."""
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
        
        return final_clean_text[:3000]
    except Exception as e:
        return f"Failed to scrape: {str(e)}"

# ============================================================
# 4. SINGLE AGENT (REDUCES API CALLS FROM ~10 TO ~3)
# ============================================================
# Agent 1: Data Analyst
data_analyst = Agent(
    role="Principal Data & Schema Architect",
    goal="Scrape and analyze dataset",
    backstory="Expert data engineer",
    tools=[scrape_technical_url],
    verbose=False,
    llm=gemini_brain,
    max_iter=1,
    max_rpm=1,
)

# Agent 2: Tech Writer  
tech_writer = Agent(
    role="Lead Developer Relations Engineer",
    goal="Write all content formats",
    backstory="Expert DevRel writer",
    verbose=False,
    llm=gemini_brain,
    max_iter=1,
    max_rpm=1,
)
# ============================================================
# 5. SINGLE TASK (ALL OUTPUTS IN ONE CALL)
# ============================================================
def create_crew(target_url: str):
    task_analyze = Task(
        description=f"Scrape {target_url} and summarize dataset structure",
        expected_output="Structured dataset summary",
        agent=data_analyst,
    )
    time.sleep(12)
    task_write = Task(
        description="Generate all 6 outputs in TechnicalInsightSchema format",
        expected_output="JSON matching TechnicalInsightSchema",
        agent=tech_writer,
        output_json=TechnicalInsightSchema,
    )
    
    return Crew(
        agents=[data_analyst, tech_writer],
        tasks=[task_analyze, task_write],
        process=Process.sequential,
    )

# For direct testing
if __name__ == "__main__":
    target_url = "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud"
    print("🛰️ Starting single-agent content generation...\n")
    crew = create_crew(target_url)
    final_output = crew.kickoff()
    print("\n🏆 OUTPUT:\n")
    print(final_output.raw)