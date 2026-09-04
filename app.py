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
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(5)
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
        
        return final_clean_text[:12000]
    except Exception as e:
        return f"Failed to scrape: {str(e)}"

# ============================================================
# 4. AGENTS
# ============================================================

data_analyst = Agent(
    role="Principal Data & Schema Architect",
    goal="Ingest raw webpage text of technical datasets, identify core features, columns, targets, dataset type, and summarize the underlying technical problem.",
    backstory=(
        "You are an expert data engineer and machine learning analyst. "
        "You carefully inspect scraped technical dataset information, identify "
        "important columns, classes, targets, dataset characteristics, and "
        "machine learning relevance. Never invent dataset-specific facts that "
        "are not present in the supplied webpage content."
    ),
    tools=[scrape_technical_url],
    verbose=False,
    llm=gemini_brain
)

tech_writer = Agent(
    role="Lead Developer Relations Engineer",
    goal="Transform the factual dataset analysis into useful, platform-specific technical content.",
    backstory=(
        "You are an experienced technical writer and developer advocate. "
        "You turn technical dataset information into clear, accurate and "
        "engaging content for developers and data scientists. "
        "Use the actual dataset information provided by the analyst."
    ),
    verbose=False,
    llm=gemini_brain
)
# ============================================================
# 5. SINGLE TASK (ALL OUTPUTS IN ONE CALL)
# ============================================================
def create_crew(target_url: str):
    """Creates and returns the crew for a given URL."""

    task_analyze = Task(
        description=(
            f"Visit this live URL: {target_url} and thoroughly extract all available "
            "information about the dataset. Identify its title, dataset type, "
            "features or classes, target variables, important statistics, structure, "
            "and machine learning relevance. Use only factual information available "
            "from the scraped page."
        ),
        expected_output=(
            "A highly organized factual breakdown of the dataset, including its "
            "name, type, structure, features/classes, target information, and "
            "technical context."
        ),
        agent=data_analyst
    )

    task_generate_content = Task(
        description=(
            "Review the factual dataset analysis provided by the analyst and generate "
            "ALL of the following outputs.\n\n"

            "1. TECHNICAL BLOG POST: Write a detailed technical article of at least "
            "400 words. Include dataset overview, important characteristics, "
            "technical insights, machine learning use cases, and conclusion.\n\n"

            "2. LINKEDIN PROMOTION: Create an engaging LinkedIn post with a strong "
            "opening hook, 3-4 useful technical insights, a clear CTA, and relevant "
            "hashtags.\n\n"

            "3. TWITTER/X THREAD: Create a 5-tweet thread. Tweet 1 should be a hook, "
            "tweets 2-4 should contain concrete dataset insights, and tweet 5 should "
            "contain a CTA. Keep each tweet under 280 characters.\n\n"

            "4. GITHUB README SUMMARY: Create a concise copy-paste-ready Markdown "
            "summary containing the dataset description, important characteristics, "
            "key statistics where available, feature/class information, and "
            "suggested machine learning approaches.\n\n"

            "5. YOUTUBE SCRIPT OUTLINE: Create a 5-minute technical tutorial outline "
            "with timestamps, including introduction, dataset overview, exploration, "
            "ML approach, and results/use cases. Include visual cues.\n\n"

            "6. CONTENT GAP ANALYSIS: Explain what existing generic content about "
            "this dataset may miss and suggest a unique technical angle for the "
            "generated content.\n\n"

            "IMPORTANT: Use actual information from the dataset analysis. Do not "
            "replace missing dataset information with generic statements about "
            "Kaggle datasets. If a specific fact is unavailable, clearly state "
            "that it was not available."
        ),
        expected_output=(
            "Fully formatted, factual, ready-to-publish content mapped to every "
            "field in TechnicalInsightSchema."
        ),
        agent=tech_writer,
        output_json=TechnicalInsightSchema
    )

    return Crew(
        agents=[data_analyst, tech_writer],
        tasks=[task_analyze, task_generate_content],
        process=Process.sequential
    )
# For direct testing
if __name__ == "__main__":
    target_url = "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud"
    print("🛰️ Starting single-agent content generation...\n")
    crew = create_crew(target_url)
    final_output = crew.kickoff()
    print("\n🏆 OUTPUT:\n")
    print(final_output.raw)