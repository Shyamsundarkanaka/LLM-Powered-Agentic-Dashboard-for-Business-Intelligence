import streamlit as st
import pandas as pd
import multiprocessing
import time
import psutil

# Custom imports
from Agentic_Dashboard_v3 import gen_bi_worker
from dashboard_tool import run_dashboard

st.title("Sales Portfolio Insight Dashboard")

# Simulating file upload
# uploaded_file = True
uploaded_file = st.file_uploader("Upload your sales portfolio CSV file:", type=['csv'])

user_query = st.text_area("Enter your analytical question for the portfolio:")

def start_dash(df, all_plots):
    run_dashboard(df, all_plots)  # starts Dash server

# Submit button
if st.button("Submit"):
    if uploaded_file and user_query.strip() != "":
        df = pd.read_csv(uploaded_file)

        with st.spinner("Analyzing your portfolio and preparing insights..."):
            with open(r'C:\Users\shyam\OneDrive\Desktop\Sales Agentic AI\dashboard_ai\files\Guidelines of the dashboard tool.txt', 'r') as file:
                Tool_Guidelines = file.read()

            state = {
                "user_query": user_query,
                "data_frame": df,
                "tool_guidelines": Tool_Guidelines
            }

            start_time = time.time()    
            output = gen_bi_worker.invoke(state)    
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
            print(f"Processing Time: {processing_time} seconds")

            # **CHANGED: Check if query is irrelevant**
            if output.get('relevance_status') == 'NO':
                st.error("❌ Your query appears to be irrelevant to the available data. Please ask questions related to the sales portfolio data.")
                st.stop()
            
            graph_json = output['graph_json']

        st.subheader("Dashboard Visualizations & Insights")
        for i in graph_json:
            st.info(f"• {graph_json[i]['purpose_of_plot']}")

        df2 = output['data_frame']

        # Start Dash app process
        p = multiprocessing.Process(target=start_dash, args=(df2, graph_json))
        p.start()

        # Store process in session state
        st.session_state.dash_process = p
        st.session_state.dash_running = True

        time.sleep(2)
        dash_url = "http://localhost:8050"
        st.markdown(f"[Click here to open Dashboard in a new tab]({dash_url})", unsafe_allow_html=True)

    elif not uploaded_file:
        st.warning("Please upload your insurance portfolio CSV data before submitting.")
    elif user_query.strip() == "":
        st.warning("Please enter your analytical question before submitting.")
