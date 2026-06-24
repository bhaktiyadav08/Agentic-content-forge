import streamlit as st
import os
from crewai import Crew, Process, Task, LLM
# Import the exact working components you built in app.py
from app import data_analyst, tech_writer, TechnicalInsightSchema

# App canvas setup
st.set_page_config(page_title="AI Agentic Repurposer", page_icon="🛰️", layout="wide")

st.title("🛰️ Autonomous Technical Content Repurposer")
st.caption("Kaggle Vibe Coding Capstone Project - Concierge Track")
st.markdown("---")

# Visual browser input text bar for the judges
user_url = st.text_input(
    "Paste any live Kaggle, GitHub, or Tech documentation URL:",
    value="https://kaggle.com"
)

# Execution trigger switch
if st.button("Launch Autonomous Agents 🚀", type="primary"):
    with st.spinner("Playwright is launching a hidden browser. Agents are inspecting the page..."):
        
        # EXPLICIT GUARDRAIL: Safely fetch the API key and enforce authentication on primary agents
        api_key_str = os.environ.get("GEMINI_API_KEY")
        if not api_key_str:
            st.error("🔑 API Key Error: GEMINI_API_KEY environment variable not found in current terminal session memory.")
            st.stop()
            
        data_analyst.llm.api_key = api_key_str
        tech_writer.llm.api_key = api_key_str
        
        # 1. Dynamically wire the tasks to use the user's browser URL input string
        task_1 = Task(
            description=f"Visit this live URL: {user_url} and thoroughly extract all information about the dataset structure, features, and technical summary.",
            expected_output="An organized architectural breakdown of the dataset properties.",
            agent=data_analyst
        )

        task_2 = Task(
            description="Review the factual dataset breakdown. Generate a comprehensive technical markdown blog post and an engaging LinkedIn promotional announcement.",
            expected_output="Fully formatted assets mapping perfectly to the TechnicalInsightSchema JSON fields.",
            agent=tech_writer,
            output_json=TechnicalInsightSchema
        )

        # 2. Assemble the dynamic workspace crew
        crew = Crew(
            agents=[data_analyst, tech_writer],
            tasks=[task_1, task_2],
            process=Process.sequential
        )
        
        # 3. Process the pipeline with an integrated dynamic quota ceiling fallback loop
        try:
            raw_result = crew.kickoff()
        except Exception as e:
            # Catch BOTH quota exhaustion (429) AND Google server overload spikes (503)
            if any(marker in str(e) for marker in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                st.warning("⚠️ Primary model is busy or experiencing high demand. Seamlessly switching to backup free model tier...")
                
                # Explicitly initialize the backup brain variant
                backup_brain = LLM(
                    model="gemini/gemini-1.5-flash",
                    temperature=0.2,
                    api_key=api_key_str
                )
                
                # Re-assign agents to the backup brain configuration on the fly
                data_analyst.llm = backup_brain
                tech_writer.llm = backup_brain
                
                # Re-initialize the execution loop instantly
                crew_fallback = Crew(
                    agents=[data_analyst, tech_writer],
                    tasks=[task_1, task_2],
                    process=Process.sequential
                )
                raw_result = crew_fallback.kickoff()
            else:
                raise e
        
        # Extract the dictionary format directly from the crew's final output object
        result_data = raw_result.json_dict if hasattr(raw_result, 'json_dict') else raw_result.to_dict()
        
        st.success("🎯 Multi-Agent Content Generation Complete!")
        
        # 4. Render beautiful, professional UI tabs using our data keys
        tab1, tab2, tab3 = st.tabs(["📝 Technical Blog Post", "💼 LinkedIn Promotion", "📊 Raw Engine Data"])
        
        with tab1:
            st.header(result_data.get("dataset_title", "Technical Analysis"))
            st.markdown(result_data.get("technical_blog_post", "No blog content generated."))
            
        with tab2:
            st.info(f"🎯 **Target Audience Focus:** {result_data.get('target_audience', 'Developers')}")
            st.text_area("Copy/Paste Ready LinkedIn Output:", value=result_data.get("linkedin_promo_post", ""), height=350)
            
        with tab3:
            st.markdown("### Enforced Pydantic Telemetry Data Matrix")
            st.json(raw_result.raw)
