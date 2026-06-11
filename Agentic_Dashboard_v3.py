import pandas as pd
import numpy as np
import json

from typing import Annotated, List
import operator
from typing_extensions import Literal
from pydantic import BaseModel,Field
from langchain_core.messages import HumanMessage,SystemMessage
from typing_extensions import TypedDict


from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt.tool_node import ToolNode
from langchain_core.messages import HumanMessage,SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from dashboard_tool import run_dashboard

import os
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()



#### Read Data
df = pd.read_csv(fr'C:\Users\shyam\OneDrive\Desktop\Sales Agentic AI\dashboard_ai\files\train.csv')

user_query = "Compare order volume across Customer Segments."

with open(fr'C:\Users\shyam\OneDrive\Desktop\Sales Agentic AI\dashboard_ai\files\Guidelines of the dashboard tool.txt', 'r') as file:
    Tool_Guidelines = file.read()




########################################################################################################################
gemini_api_key_2 = os.getenv("gemini_api_key_2")

client = OpenAI(
    api_key=gemini_api_key_2,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def get_response(system_prompt, prompt):

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content
########################################################################################################################

# deepseek_api_key = os.getenv("deepseek_api_key")
# client = OpenAI(
#                 base_url="https://openrouter.ai/api/v1",
#                 api_key= deepseek_api_key,
#             )

# def get_response(system_prompt , prompt):
#     response = client.chat.completions.create(
            
#     model="deepseek/deepseek-r1",
#     messages=[
#                     {"role": "system", "content":system_prompt},  # System Role
#                     {"role": "user", "content": prompt}  # User Message
#                 ]
#             )
        
#     response_str = response.choices[0].message.content 
#     return response_str

########################################################################################################################



# Graph state
class State(TypedDict):
    user_query: str
    data_frame: pd.DataFrame
    tool_guidelines: str
    graph_json: str
    correctness: str
    retries: int
    relevance_status: str  # ADD THIS LINE

def relevance_checker(state: State):
    """
    Checks if the user query is relevant to the data available.
    Returns 'YES' if relevant, 'NO' if completely irrelevant.
    Has high acceptance tendency - only rejects queries that are totally out of context.
    """
    print("relevance_checker Node")
    
    user_query = state["user_query"]
    data_frame_df = state["data_frame"]
    
    prompt = f"""You are a Business Intelligence Assistant analyzing user queries for relevance.

Your task is to determine if a user query can be answered or visualized using the available data.

**Important Guidelines:**
- Be LENIENT in accepting queries
- Reject queries that are COMPLETELY IRRELEVANT to the data
- If there's ANY possibility the query relates to the data columns or business context, accept it
- Accept queries even if they're vague, informal, or need refinement
- Accept queries that ask about trends, comparisons, distributions, or any analytical question
- Reject ONLY if the query is about totally different domains (e.g., asking about weather when data is about sales)
- Do not accept queries that seem stupid or irrelavant to the data

**Available Data Information:**
{data_frame_df.head(10).to_string()}

**Column Names:**
{list(data_frame_df.columns)}

**User Query:**
{user_query}

---

**Your Response:**
Respond with ONLY one word: 'YES' or 'NO'
- YES: if the query has ANY relation to the data or can potentially be answered
- NO: if the query is COMPLETELY irrelevant and impossible to answer with this data

**Output (YES or NO):**
"""
    
    system_prompt = "You are a lenient Business Intelligence Assistant with high acceptance tendency for user queries."
    
    relevance_response = get_response(system_prompt, prompt).strip().upper()
    
    # Ensure response is either YES or NO
    if "YES" in relevance_response:
        relevance_status = "YES"
    elif "NO" in relevance_response:
        relevance_status = "NO"
    else:
        # Default to YES if unclear (lenient approach)
        relevance_status = "YES"
    
    print(f"Relevance Status: {relevance_status}")
    print(f"User Query: {user_query}")
    
    return {"relevance_status": relevance_status, "graph_json": {}}


def route_relevance(state: State):
    """Route based on relevance check - continue or end with irrelevant message"""
    print("route_relevance Node")
    
    if state.get("relevance_status") == "NO":
        return "Irrelevant"
    else:
        return "Relevant"


def query_enhancer(state: State):
    """
    Enhances the raw user query into a precise, dashboard-compatible question suitable for data visualization and business analysis.
    It maintains the original intent but rephrases it with better clarity, structure, and alignment to what a BI dashboard can represent.
    """

    print("query_enhancer Node")
    raw_query = state["user_query"]
    data_frame_df = state["data_frame"]


    prompt = f"""
You are a highly skilled **Sales & Business Intelligence Analyst** working on designing smart, interactive dashboards for business users.
Your goal is to take informal or loosely worded user queries and **rewrite them** into clear, specific, and visualization-ready questions.

You are NOT answering the query. You are refining it for downstream processing by an automated dashboard builder.

---

 **Your task:**
Rewrite the user query to make it:
1. Specific and actionable
2. Suitable for graphical representation (bar chart, scatter plot, box plot, pie chart, etc.)
3. Easy for the dashboard engine to parse and convert into filters or plot instructions

---

**Guidelines:**
- Maintain the original **business intent** of the user query
- DO NOT add new assumptions or business logic unless absolutely obvious
- Convert vague phrases (like "good", "better", "recent", "doing well") into something measurable 
- Output should be 1 or 2 lines. Do not explain or format it like JSON or markdown.
- Make the output is simple and easily usable by an automated dashboard engine
- If type of chart is mentioned, it should be limited to 'bar', 'scatter', 'box', 'histogram', 'pie' and no other type of plot should be mentioned.
- Output should contain just the Modifed Query and nothing else

---

**User Query:**
{raw_query}

---

**Data Information:**
{data_frame_df.describe(include='all')} 

---

📝 **Rewritten Query (Optimized for Dashboard Use):**
"""

    system_prompt = "You are a top-tier Sales & Business Intelligence Analyst skilled in translating business questions into dashboard-friendly queries."

    enhanced_query = get_response(system_prompt, prompt)
    print("Enhanced Query:", enhanced_query)
    print("Original Query:", raw_query)


    return {"enhanced_query": enhanced_query, "retries":0}


def data_preprocesser_node(state:State):
    """
    Cleans and preprocesses the input DataFrame.

    Steps:
    1. Strips whitespace and handles missing values.
    2. Converts numeric strings to proper numeric types.
    3. Detects and decomposes date columns (year, month, weekday).
    4. Caps outliers in numeric columns using the IQR method.
    5. Removes rows and columns with all missing values.
    """
    print("data_preprocesser_node Node")
    df_clean = state['data_frame'].copy()

    # 1. GENERAL DATA CLEANING: Strip whitespace from column names and string values
    df_clean.columns = df_clean.columns.str.strip()
    for col in df_clean.select_dtypes(include='object'):
        df_clean[col] = df_clean[col].astype(str).str.strip().replace({'': np.nan})

    # 2. TYPE CONVERSION: Convert object columns to numeric if possible
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            try:
                df_clean[col] = pd.to_numeric(df_clean[col])
            except:
                pass

    # 3. DATE DETECTION AND DECOMPOSITION
    date_cols = []
    for col in df_clean.columns:
        if np.issubdtype(df_clean[col].dtype, np.datetime64):
            date_cols.append(col)

        elif df_clean[col].dtype == 'object' and any(
            keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated']):
            
            sample_vals = df_clean[col].dropna()
            if sample_vals.shape[0] > 0:
                sample_vals = sample_vals.sample(min(10, sample_vals.shape[0]))

                common_formats = [
                    "%Y-%m-%d",        # 2023-08-01
                    "%d-%m-%Y",        # 01-08-2023
                    "%m/%d/%Y",        # 08/01/2023
                    "%d/%m/%Y",        # 01/08/2023
                    "%b %d, %Y",       # Aug 01, 2023
                    "%d %b %Y",        # 01 Aug 2023
                    "%Y/%m/%d",        # 2023/08/01
                ]

                detected_format = None
                for fmt in common_formats:
                    try:
                        parsed = pd.to_datetime(sample_vals, format=fmt, errors='raise')
                        detected_format = fmt
                        break
                    except:
                        continue

                if detected_format:
                    df_clean[col] = pd.to_datetime(df_clean[col], format=detected_format, errors='coerce')
                    date_cols.append(col)

    for col in date_cols:
        if df_clean[col].notna().sum() > 0:
            df_clean[f'{col}_year'] = df_clean[col].dt.year.astype(str)
            df_clean[f'{col}_month'] = df_clean[col].dt.strftime('%B')
            df_clean[f'{col}_dayofweek'] = df_clean[col].dt.day_name()
            
            df_clean = df_clean.drop(columns=[col])

    # 4. OUTLIER CAPPING (IQR method)
    num_cols = df_clean.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        Q1 = df_clean[col].quantile(0.25)
        Q3 = df_clean[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df_clean[col] = np.where(df_clean[col] < lower_bound, lower_bound,
                          np.where(df_clean[col] > upper_bound, upper_bound, df_clean[col]))

    # 5. REMOVE ROWS AND COLUMNS WITH ALL MISSING VALUES
    df_clean = df_clean.dropna(axis=0, how='all')  # drop rows with all NaNs
    df_clean = df_clean.dropna(axis=1, how='all')  # drop columns with all NaNs

    return {"data_frame": df_clean} 



def plot_selector(state:State):
    """The Analyser agent that understand the data and the user query and also the limitations of the graphs that can be built on the tool and generates the list of graphs along with paramters 
    required to be build the grapgh and also generates the question that be answered by plotting that graph

    Returns:
        json with List of graphs along with paramters equired to be build the grapgh and also generates the question that be answered by plotting that graph
    """

    print("plot_selector Node")
    prompt =  f"""You are an Senior Analyst in Sales. 
    You need understand the data using the data information provided and also understand the
    user query, based on the data provided and the user questions you need to come up with the 
    list of plots that is required to be built on a dashboard tool. However there are some 
    rules and limitations in the tool which are specified below. You need to understand and
    come up with the plot information in the specified format that is required to be used
    in the dashboard tool. 

    Guidelines of the dashboard tool : $$$ {state['tool_guidelines']} $$$

    Data Information : $$$ {state['data_frame'].describe(include='all')} $$$

    User Query : $$$ {state['user_query']}  $$$

    CRITICAL INSTRUCTIONS:
    - DO NOT GIVE A PYTHON CODE. PROVIDE ONLY THE JSON.
    - DO NOT INCLUDE `````` or any markdown formatting
    - DO NOT INCLUDE ANY OTHER INFORMATION OR EXPLANATORY TEXT
    - OUTPUT MUST START WITH {{ and END WITH }}
    - THE OUTPUT PROVIDED WILL BE DIRECTLY PASSED TO THE TOOL SO MAKE SURE THE OUTPUT IS A JSON IN CORRECT FORMAT
    - WITH THE KEYS 'one' , 'two' and so on and the values are JSONS with the keys ['type', 'x_axis', 'y_axis', 'category_filter_column', 'numerical_filter_column', 'filter_type', 'cat_filter_value', 'num_filter_min', 'num_filter_max', 'purpose_of_plot']
    
    RESPOND WITH ONLY RAW JSON - NO MARKDOWN CODE BLOCKS.
    """

    # Generate queries
    system_prompt = f'''Senior Analyst in Sales. You must output ONLY raw JSON without any markdown formatting, code blocks, or explanatory text. Start directly with {{ and end with }}.'''
    
    report = get_response(system_prompt , prompt)

    # Clean the response - remove markdown code blocks if present
    output_string = report.strip()
    
    # Remove `````` markers if present
    if output_string.startswith('```'):
        # Find the first newline after ```json or ```
        first_newline = output_string.find('\n')
        if first_newline != -1:
            output_string = output_string[first_newline+1:]
        else:
            # If no newline, remove first 3 chars (```)
            output_string = output_string[3:]
    
    # Remove trailing ```
    if output_string.endswith('```'):
        output_string = output_string[:-3].strip()
    
    # Remove "json" word if it appears at the start
    if output_string.startswith('json'):
        output_string = output_string[4:].strip()
    
    # Replace null with None for Python eval
    output_string = output_string.replace('null', 'None')
    
    print("Cleaned output_string:", output_string[:200] + "..." if len(output_string) > 200 else output_string)
    
    try:
        output_json = eval(output_string)
        print("Successfully parsed JSON")
    except SyntaxError as e:
        print(f"SyntaxError while parsing: {e}")
        print(f"Full output_string: {output_string}")
        # Fallback: try using json.loads instead
        try:
            import json
            output_string_for_json = output_string.replace('None', 'null')
            output_json = json.loads(output_string_for_json)
            print("Successfully parsed using json.loads")
        except Exception as e2:
            print(f"json.loads also failed: {e2}")
            # Return empty structure as fallback to avoid crashing
            output_json = {}
    except Exception as e:
        print(f"Unexpected error while parsing: {e}")
        output_json = {}
    
    return {"graph_json": output_json}


def output_checker(state:State):

    """output_checker agent that checks if the output from the previous agent meets the guidelines of the tool to which the ouyput will be passed to """

    print("output_checker Node")
    correctness = 'YES'
    graph_info= state['graph_json']
    expected_keys = {'one', 'two', 'three', 'four', 'five', 'six'}

    # Check if all required keys are just the expected ones
    if not expected_keys.issuperset(graph_info.keys()):
        correctness = 'NO'

    expected_sub_keys = {'type', 'x_axis', 'y_axis', 'category_filter_column', 'numerical_filter_column', 'filter_type', 'cat_filter_value', 'num_filter_min', 'num_filter_max', 'purpose_of_plot'}
    for i in graph_info.keys():
        if not expected_sub_keys.issuperset(graph_info[i].keys()):
            correctness = 'NO'

    print("Checker output",correctness)
    return {"correctness": correctness}




# Conditional edge function to route back to generator or end based upon feedback from the evaluator
def route_plot_selection(state: State):
    """Route back to plot generator or end based upon feedback from the evaluator"""

    print("route_plot_selection Node")

    if state["retries"] == 3:

        return "Accepted"

    if state["correctness"] == "YES":
        return "Accepted"
    else:
        state["retries"] +=1
        return "Rejected"
    
# Conditional edge function to route back to generator or end based upon feedback from the evaluator
def call_tool(state: State):
    """Passes the output to the Dashboard tool"""
    
    run_dashboard(state['data_frame'] , state['graph_json'])



from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display

gen_bi_graph = StateGraph(State)

# Add the nodes
gen_bi_graph.add_node("relevance_checker", relevance_checker)
gen_bi_graph.add_node("query_enhancer", query_enhancer)
gen_bi_graph.add_node("data_preprocesser_node", data_preprocesser_node)
gen_bi_graph.add_node("plot_selector", plot_selector)
gen_bi_graph.add_node("output_checker", output_checker)

# Add edges to connect nodes
gen_bi_graph.add_edge(START, "relevance_checker")

# Conditional edge from relevance_checker
gen_bi_graph.add_conditional_edges(
    "relevance_checker",
    route_relevance,
    {
        "Relevant": "query_enhancer",
        "Irrelevant": END
    }
)

gen_bi_graph.add_edge("query_enhancer", "data_preprocesser_node")
gen_bi_graph.add_edge("data_preprocesser_node", "plot_selector")
gen_bi_graph.add_edge("plot_selector", "output_checker")
gen_bi_graph.add_conditional_edges(
    "output_checker",
    route_plot_selection,
    {
        "Accepted": END,
        "Rejected": "plot_selector",
    }
)

# Compile the workflow
gen_bi_worker = gen_bi_graph.compile()

       