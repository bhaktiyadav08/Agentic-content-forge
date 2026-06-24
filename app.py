import os
from typing import List
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv
load_dotenv()
# 1. Connect CrewAI to our verified Gemini Brain
# CrewAI natively looks for the 'GEMINI_API_KEY' environment variable we just verified.
gemini_brain = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.2,
    max_retries=5  # Forces the agent to automatically pause and retry if it hits a rate limit
)
# 2. Define the Pydantic Data Contract
# This acts as a strict structure that the final agent MUST fill out before finishing.
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
from crewai.tools import tool
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import multiprocessing
def _isolated_playwright_worker(url, return_dict):
    """An isolated background process worker that handles Playwright completely outside Streamlit's event loop."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=25000)
            time.sleep(3) # Wait for JavaScript data matrices to fully render
            return_dict['html'] = page.content()
            browser.close()
    except Exception as e:
        return_dict['error'] = str(e)

@tool("Universal Tech Webpage Scraper")
def scrape_technical_url(url: str) -> str:
    """Launches a headless browser in a safe, isolated system process to extract raw metadata text from technical web links."""
    try:
        # Rate limit safety pacing delay for Google Gemini Free Tier
        time.sleep(5)
        
        # Use a multiprocessing Manager to share string data safely across isolated system tasks
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        
        # Spawn the isolated background browser worker thread
        process = multiprocessing.Process(target=_isolated_playwright_worker, args=(url, return_dict))
        process.start()
        process.join() # Wait for the background browser tasks to cleanly finish execution
        
        if 'error' in return_dict:
            return f"Scraping thread ran into an unexpected interruption: {return_dict['error']}"
            
        if 'html' not in return_dict:
            return "Failed to secure data: Web browser execution context closed prematurely."
            
        # Pass the cleanly gathered HTML to BeautifulSoup for processing
        soup = BeautifulSoup(return_dict['html'], 'html.parser')
        
        # Eliminate structural noise and advertising trackers to save token bandwidth
        for element in soup(["script", "style", "footer", "nav", "header", "aside", "svg"]):
            element.extract()
            
        text_content = soup.get_text(separator=' ')
        clean_lines = (line.strip() for line in text_content.splitlines())
        non_empty_chunks = (phrase.strip() for line in clean_lines for phrase in line.split("  "))
        final_clean_text = '\n'.join(chunk for chunk in non_empty_chunks if chunk)
        
        return final_clean_text[:12000]
        
    except Exception as e:
        return f"Failed to gather data from the dynamic site due to error: {str(e)}"
# 4. Constructing the Expert AI Personnel

# Agent 1: The Data Specialist
data_analyst = Agent(
    role="Principal Data & Schema Architect",
    goal="Ingest raw webpage text of technical datasets, identify core features/columns, targets, and summarize the underlying technical problem.",
    backstory=(
        "You are an elite data engineer. You instantly spot data distributions, column configurations, "
        "and metadata meanings out of messy, unstructured webpage scrapes. You ignore website menus "
        "and focus purely on hard technical specifications."
    ),
    tools=[scrape_technical_url],  # Giving this agent the web scraping tool we built
    verbose=True,                  # Logs the agent's internal "thinking process" to the terminal live
    llm=gemini_brain
)

# Agent 2: The Content Creator
tech_writer = Agent(
    role="Lead Developer Relations Engineer",
    goal="Translate raw column metadata and database schemas into highly engaging, educational technical blog posts and promotional social content.",
    backstory=(
        "You are a veteran Developer Relations (DevRel) writer. You have a knack for taking dense, "
        "boring documentation schemas and turning them into fascinating, readable guides for developers on LinkedIn and Medium. "
        "You know exactly how to structure hooks, line breaks, and clear technical summaries."
    ),
    verbose=True,                  # Logs this agent's thoughts too
    llm=gemini_brain               # This agent doesn't need the web scraper tool; it just processes the analyst's output
)
# 5. Define the Target URL (The live link we want to analyze)
# For this test, we use a classic data science asset: The Iris Dataset documentation.
target_tech_link = "https://www.kaggle.com/datasets/yasserh/housing-prices-dataset"

# 6. Mission Definitions

task_analyze_schema = Task(
    description=(
        f"Visit this live URL: {target_tech_link} and thoroughly extract all information about the "
        "dataset structure, its features, target columns, classification attributes, and documentation summary."
    ),
    expected_output=(
        "A highly organized raw architectural breakdown of the dataset properties, feature rows, "
        "and technical context stripped of webpage clutter."
    ),
    agent=data_analyst  # Linked directly to our Principal Data Architect agent
)

task_generate_content = Task(
    description=(
        "Review the factual dataset breakdown provided by the analyst. Using that structured insight, "
        "generate a comprehensive technical blog post and an engaging LinkedIn promotional announcement."
    ),
    expected_output=(
        "Fully formatted, ready-to-publish educational marketing materials mapping perfectly "
        "to the required TechnicalInsightSchema JSON fields."
    ),
    agent=tech_writer,               # Linked directly to our DevRel writer agent
    output_json=TechnicalInsightSchema  # Forces the output to comply exactly with our Pydantic Data Contract!
)
# 7. Assemble the AI Team and Fire Ignition

content_crew = Crew(
    agents=[data_analyst, tech_writer],
    tasks=[task_analyze_schema, task_generate_content],
    process=Process.sequential  # Ensures Task 1 completely finishes and hands its data to Task 2
)

if __name__ == "__main__":
    print("🛰️ Ingesting live data target via Agentic Loop...\n")
    
    # Kickoff starts the entire autonomous pipeline!
    final_output = content_crew.kickoff()
    
    print("\n🏆 CRITICAL STRUCTURAL OUTPUT SECURED (JSON) 🏆\n")
    print(final_output.raw)
