import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import os
import sys

import pandas as pd
import json  # Needed for JSON in insights

import os
from dotenv import load_dotenv

load_dotenv()

perplexity_api = os.getenv("PERPLEXITY_API_KEY")

client = OpenAI(
api_key=perplexity_api,
base_url="https://api.perplexity.ai"
)

def get_response(system_prompt , prompt):
        
    response = client.chat.completions.create(
    model="sonar",
    messages=[
                        {"role": "system", "content":system_prompt},  # System Role
                        {"role": "user", "content": prompt}  # User Message
                    ]
                )
        
    response_str = response.choices[0].message.content 
    return response_str

# api_key = ""
# client = OpenAI(
#                     base_url="https://openrouter.ai/api/v1",
#                     api_key= api_key,
#                 )

# def get_response(system_prompt , prompt):
#     response = client.chat.completions.create(
                
#     model="deepseek/deepseek-r1:free",
#     messages=[
#                         {"role": "system", "content":system_prompt},  # System Role
#                         {"role": "user", "content": prompt}  # User Message
#                     ]
#                 )
            
#     response_str = response.choices[0].message.content 
#     return response_str

def run_dashboard(df, all_plots):
    
    """
    Launches a Dash web application that provides interactive data visualizations and insights based on the given DataFrame.

    This function sets up a Dash dashboard with multiple tabs, each representing a different plot. Users can apply filters to the data, which will dynamically update the visualizations and provide insights generated based on the filtered data.

    Parameters:
    ----------
    df : pandas.DataFrame
        A DataFrame containing the data to be analyzed and visualized in the dashboard. This DataFrame should include all necessary columns corresponding to the plots defined in the all_plots parameter.

    all_plots : dict
        A dictionary containing the specifications for each plot. Each key corresponds to a unique identifier for a plot, and the value is another dictionary containing parameters like:
        - 'x_axis': The column name for the x-axis.
        - 'y_axis': The column name for the y-axis (if applicable).
        - 'type': The type of plot (e.g., 'bar', 'scatter', 'line', etc.).
        - 'filter_type': Type of filters available (categorical or numerical).
        - 'category_filter_column': The column used for categorical filtering (if applicable).
        - 'numerical_filter_column': The column used for numerical filtering (if applicable).
        - 'purpose_of_plot': A brief description of the intended analysis or question the plot addresses.

    Returns:
    -------
    None:
        The function runs a Dash application that does not return any value. The application is accessible via a web browser and provides an interactive interface to explore the data visualizations and insights.

    Behavior:
    --------
    - Initializes the GptApi object for generating insights from the plots.
    - Constructs a layout for the dashboard with a header and tabs for each plot.
    - Handles filtering through dropdowns and input fields, updating plots and insights accordingly.
    - Generates insights for each plot based on the user-selected filters using GPT.
    - Starts the Dash server for users to access the dashboard in their web browsers.
    """

    ## Bug fix (can be enhanced)
    for i in all_plots:
        for j in (all_plots[i]):
            if  j == 'num_filter_min' or j == 'num_filter_max':
                all_plots[i][j] = None

            if j == 'cat_filter_value':
                all_plots[i][j] = []
    


    def get_gpt_response(data_info, graph_info, filter_column=None, filters_values = None, purpose_of_plot = None):
        filter_info = {'No filter applied' if filter_column==None else f'Filter was applied on the columnn {filter_column} with the values {filters_values}' }
        prompt = f''' You are an expert data analyst agent. Your task is to understand the information from the graph/plots given and generate insights. 
        You will be given the information that was derived from the plots, and in some cases the information on the filters used while building the plots will also be given whic you must consider while 
        generating insights.
        You will also be provided with the information of the data used while building the dashboard.
        Additional you need to understand the purpose of the Graph and come with the insight or answer for the purpose first and then come up with graph insights.

        Each input is enclosed within $$ $$
        Information from the Graph : $$ {graph_info} $$
        Filter Info : $$ { filter_info} $$
        data_info : $$ {data_info} $$ 
        purpose of plot/question to be answered : $$ {purpose_of_plot} $$

        First come with the insight or answer for the purpose of the plot in bold in 1 line. Leave this section bank if there is not purpose or question.Once done,
        The insights generated should be short and consise in bullet in points, not more than 200 words. Insights should talk about the numbers from the graph_info but not in detail and should include actionable steps. 
            
        THINK DEEPLY AND GIVE ONLY THE INSIGHTS THAT CAN BE DERVIVED FROM THE GRAPH INFO. DO NOT INLCUDE ANY OTHER INFORMATION
    '''
        try:
            system_prompt = "You are an expert data analyst agent. Your task is to understand the information from the graph/plots given and generate insights"
            response = get_response(system_prompt, prompt)
            return response
        except Exception as e:
            return f'Dynamic Insights - {e}'
        
   


    app = dash.Dash(__name__, suppress_callback_exceptions=True)


    children_info = []
    for i in all_plots:
        children_info.append(dcc.Tab(
            label=f"{all_plots[i]['x_axis']} { ' ' if  all_plots[i]['y_axis'] is None else all_plots[i]['y_axis']} {all_plots[i]['type']} Chart",
            value=i  # Ensure the tab matches the keys 'one' to 'seven'
        ))

    app.layout = html.Div([
        html.H1("Gen Bi Dashboard", style={'text-align': 'center'}),
        dcc.Tabs(id='tabs', value='one', children=children_info, style={'display': 'flex', 'justify-content': 'center'}),
        html.Div(id='tabs-content'),
        html.Button("Stop Dashboard", id="stop-button", n_clicks=0,
                    style={'background-color': 'red', 'color': 'white', 'margin': '10px', 'padding': '10px', 'float': 'right'})
    ])

    def render_content_sub_function(tab_num):
        if all_plots[f'{tab_num}']['filter_type'] == 'categorical':
            return html.Div([
                dcc.Markdown(
                f"### **{all_plots[f'{tab_num}']['category_filter_column']}**",
                style={'text-align': 'center', 'margin': '10px auto', 'font-size': '16px'}
                ),
                dcc.Dropdown(
                    id=f'{tab_num}-cat-filter',
                    options=[{'label': i, 'value': i} for i in df[all_plots[f'{tab_num}']['category_filter_column']].unique() if pd.notna(i)],
                    # value=all_plots[f'{tab_num}']['cat_filter_value'],
                    multi=True,  # Enable multi-selection
                    placeholder='Select Status',
                    style={'width': '50%', 'margin': '10px auto', }
                ),
                dcc.Input(
                    id=f'{tab_num}-num-filter-min',
                    type='number',
                    value=-999999,
                    style={'display': 'none'}
                ),
                dcc.Input(
                    id=f'{tab_num}-num-filter-max',
                    type='number',
                    value=999999,
                    style={'display': 'none'}
                ),
                dcc.Graph(id=f'{tab_num}-chart'),
                dcc.Markdown(
                    id=f'{tab_num}-insights',  # Use Markdown for insights
                    style={'text-align': 'left', 'width': '100%', 'height': '300px', 'margin-top': '12px'}
                )
            ])

        if all_plots[f'{tab_num}']['filter_type'] == 'numerical':
            return html.Div([
                html.Div([
                    dcc.Markdown(
                    f"###  **{all_plots[f'{tab_num}']['numerical_filter_column']}**",
                    style={'text-align': 'center', 'margin': '10px auto', 'font-size': '16px'}
                    ),
                    dcc.Input(
                        id=f'{tab_num}-num-filter-min',
                        type='number',
                        placeholder='Minimum',
                        style={'width': '45%', 'margin': '10px auto'}
                    ),
                    dcc.Input(
                        id=f'{tab_num}-num-filter-max',
                        type='number',
                        placeholder='Maximum',
                        style={'width': '45%', 'margin': '10px auto'}
                    ),
                    dcc.Dropdown(
                        id=f'{tab_num}-cat-filter',
                        options=[{'label': 'Blank', 'value': 'Blank'}],
                        value='Blank',
                        multi=True,  # Enable multi-selection
                        style={'display': 'none'}
                    )
                ], style={'display': 'flex', 'justify-content': 'space-between'}),
                dcc.Graph(id=f'{tab_num}-chart'),
                dcc.Markdown(
                    id=f'{tab_num}-insights',  # Use Markdown for insights
                    style={'text-align': 'left', 'width': '100%', 'height': '300px', 'margin-top': '12px'}
                )
            ])

    @app.callback(
        Output('tabs-content', 'children'),
        Input('tabs', 'value')
    )
    def render_content(tab):
        for tab_num in all_plots.keys():
            if tab == tab_num:
                content = render_content_sub_function(tab_num)
                return content

    def update_chart_sub_func(tab, category, num_min, num_max, tab_num):
        try:
            type_chart = all_plots[tab_num]['type']

            # Apply filters
            filtered_df = df
            # filtered_df = df.dropna(subset=[all_plots[tab_num]['x_axis'],all_plots[tab_num]['y_axis']])

            # Apply categorical filter
            if all_plots[tab_num]['category_filter_column'] is not None:
                if category and 'Blank' not in category:  # Ensure no blank is selected
                    filter_column = all_plots[tab_num]['category_filter_column']
                    filtered_df = filtered_df[[value in category for value in filtered_df[filter_column]]]

        
            # Apply numerical filters
            if all_plots[tab_num]['numerical_filter_column'] is not None and all_plots[tab_num]['filter_type'] =='numerical':
                if num_min is not None and num_min != -999999:
                    filtered_df = filtered_df[filtered_df[all_plots[tab_num]['numerical_filter_column']] >= num_min]
                if num_max is not None and num_max != 999999:
                    filtered_df = filtered_df[filtered_df[all_plots[tab_num]['numerical_filter_column']] <= num_max]

            # Check if the filtered DataFrame is empty
            if filtered_df.empty:
                return {
                    'data': [],
                    'layout': {
                        'title': 'No Data Available',
                        'xaxis': {'title': all_plots[tab_num]['x_axis']},
                        'yaxis': {'title': all_plots[tab_num]['y_axis']},
                        'annotations': [{
                            'text': 'No data matches the selected filters.',
                            'xref': 'paper',
                            'yref': 'paper',
                            'x': 0.5,
                            'y': 0.5,
                            'showarrow': False,
                            'font': {'size': 16}
                        }]
                    }
                }
            
            # Sort logic for time-based categories
            x_axis = all_plots[tab_num]['x_axis']
            if x_axis.lower().endswith('_month'):
                month_order = ["January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"]
                filtered_df[x_axis] = filtered_df[x_axis].str.strip()  # remove spaces
                filtered_df[x_axis] = pd.Categorical(filtered_df[x_axis], categories=month_order, ordered=True)
                filtered_df = filtered_df.sort_values(by=x_axis)

            elif x_axis.lower().endswith('_dayofweek'):
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                filtered_df[x_axis] = filtered_df[x_axis].str.strip()
                filtered_df[x_axis] = pd.Categorical(filtered_df[x_axis], categories=day_order, ordered=True)
                filtered_df = filtered_df.sort_values(by=x_axis)

            elif x_axis.lower().endswith('_year'):
                filtered_df[x_axis] = pd.Categorical(filtered_df[x_axis], ordered=True)
                filtered_df = filtered_df.sort_values(by=x_axis)

            # Generate figures if data is available   ## CHANGED FOR ADDED GRAPH

            if type_chart == 'bar':
                fig = px.bar(filtered_df, x=all_plots[tab_num]['x_axis'], y=all_plots[tab_num]['y_axis']
                            ,color=all_plots[tab_num]['x_axis'], color_discrete_sequence=px.colors.qualitative.Bold)
            

            elif type_chart == 'scatter':
                fig = px.scatter(filtered_df, x=all_plots[tab_num]['x_axis'], y=all_plots[tab_num]['y_axis'],
                                 color=all_plots[tab_num]['x_axis'],  color_discrete_sequence=px.colors.qualitative.Bold)
                
                
            elif type_chart == 'line':  # New chart type handling ## CHANGED FOR ADDED GRAPH
                fig = px.line(filtered_df, x=all_plots[tab_num]['x_axis'], y=all_plots[tab_num]['y_axis'])
                

            elif type_chart == 'box':  # New chart type handling ## CHANGED FOR ADDED GRAPH
                fig = px.box(filtered_df, x=all_plots[tab_num]['x_axis'], y=all_plots[tab_num]['y_axis']
                            ,color=all_plots[tab_num]['x_axis'], color_discrete_sequence=px.colors.qualitative.Bold)
                

            elif type_chart == 'histogram':  # New chart type handling ## CHANGED FOR ADDED GRAPH
                fig = px.histogram(filtered_df, x=all_plots[tab_num]['x_axis'])
                

            elif type_chart == 'pie':  # New chart type handling ## CHANGED FOR ADDED GRAPH
                fig = px.pie(filtered_df, names=all_plots[tab_num]['x_axis'], values=all_plots[tab_num]['y_axis'],
                             color=all_plots[tab_num]['x_axis'], color_discrete_sequence=px.colors.qualitative.Bold)
                    
            if type_chart != 'pie': fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',showlegend=False)


            return fig


        except Exception as e:
            print(e)
            # Create an empty figure with a message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error in plotting graph",
                showarrow=False,
                font=dict(size=8),
                xref="paper", yref="paper",
                x=0.5, y=0.5
            )
            return fig


    def update_insights_sub_func(tab, category, num_min, num_max, tab_num):
        try:
            type_chart = all_plots[tab_num]['type']
            purpose_of_plot = all_plots[tab_num]['purpose_of_plot']

            # Apply filters
            filtered_df = df
            filter_column = None
            filters_values = None

            # Apply categorical filter
            if all_plots[tab_num]['filter_type'] == 'categorical':
                if category and 'Blank' not in category:  # Ensure no blank is selected
                    filter_column = all_plots[tab_num]['category_filter_column']
                    filters_values = category
                    filtered_df = filtered_df[[value in category for value in filtered_df[filter_column]]]

            # Apply numerical filters
            if all_plots[tab_num]['filter_type'] == 'numerical':
                if num_min is not None and num_min != -999999:
                    filtered_df = filtered_df[filtered_df[all_plots[tab_num]['numerical_filter_column']] >= num_min]
                    filters_values = [f'Minimum Value is {num_min}']
                if num_max is not None and num_max != 999999:
                    filtered_df = filtered_df[filtered_df[all_plots[tab_num]['numerical_filter_column']] <= num_max]
                    if filters_values is None:
                        filters_values = [f'Maximum Value is {num_max}']
                    elif isinstance(filters_values, list):
                        filters_values.append(f'Maximum Value is {num_max}')

            # Check if the filtered DataFrame is empty
            if filtered_df.empty:
                return " No insights"

            # Generate figures if data is available
            if type_chart == 'bar':
                grouped_df = filtered_df.groupby(all_plots[tab_num]['x_axis'])[all_plots[tab_num]['y_axis']].sum().reset_index()
                filtered_df = filtered_df[[all_plots[tab_num]['x_axis'], all_plots[tab_num]['y_axis']]]
                chart_data = grouped_df.to_dict(orient='records')
                json_chart_data = json.dumps(chart_data)
                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            json_chart_data,
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights

            if type_chart == 'scatter':
                x = filtered_df[all_plots[tab_num]['x_axis']]
                y = filtered_df[all_plots[tab_num]['y_axis']]
                filtered_df = filtered_df[[all_plots[tab_num]['x_axis'], all_plots[tab_num]['y_axis']]]
                correlation = x.corr(y)
                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            f"The columns {all_plots[tab_num]['x_axis']} and {all_plots[tab_num]['y_axis']} have a correlation value of {correlation}",
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights

            if type_chart == 'line' :  # New handling for line and area charts ## CHANGED FOR ADDED GRAPH
                # Generate a text version of the data used in the line chart
                x_column = all_plots[tab_num]['x_axis']
                y_column = all_plots[tab_num]['y_axis']

                # Summarize the data for the line chart
                text_summary = filtered_df.groupby(x_column)[y_column].agg(['mean', 'min', 'max', 'std', 'count']).reset_index()
                
                # Rename the columns for clarity
                text_summary.columns = [x_column, 'Mean', 'Min', 'Max', 'Standard Deviation', 'Count']

                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            text_summary,
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights

            if type_chart == 'box':  # New handling for box charts ## CHANGED FOR ADDED GRAPH
                # Generate a text version of the box plot data
                x_column = all_plots[tab_num]['x_axis']
                y_column = all_plots[tab_num]['y_axis']

                # Create a summary DataFrame with descriptive statistics
                summary_stats = filtered_df.groupby(x_column)[y_column].describe().reset_index()

                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            summary_stats,
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights

            if type_chart == 'histogram':  # New handling for histogram charts ## CHANGED FOR ADDED GRAPH
                x_column = all_plots[tab_num]['x_axis']
                text_summary = filtered_df[x_column].value_counts().reset_index()
                text_summary.columns = [x_column, 'Count']
                if len(text_summary) >200: text_summary = text_summary.head(200)

                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            text_summary,
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights

            if type_chart == 'pie':  # New handling for pie charts ## CHANGED FOR ADDED GRAPH
                # Generate a text version of the data used in the pie chart
                x_column = all_plots[tab_num]['x_axis']
                y_column = all_plots[tab_num]['y_axis']
                
                # Summarize the data for the pie chart
                text_summary = filtered_df.groupby(x_column)[y_column].sum().reset_index()
                text_summary.columns = [x_column, 'Total']
                # Calculate the total sum of the 'Total' column for percentage calculation
                total_sum = text_summary['Total'].sum()
                # Calculate percentage
                text_summary['Percentage'] = (text_summary['Total'] / total_sum) * 100
                
                insights = get_gpt_response(filtered_df.describe(include='all'),
                                            text_summary,
                                            filter_column,
                                            filters_values,
                                            purpose_of_plot)
                return insights
        except:
            insights = "No Insights Available"
            return insights

    if 'one' in all_plots.keys():
        @app.callback(
            Output('one-chart', 'figure'),
            Output('one-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('one-cat-filter', 'value'),
            Input('one-num-filter-min', 'value'),
            Input('one-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'one')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'one')
            return fig, insights

    if 'two' in all_plots.keys():
        @app.callback(
            Output('two-chart', 'figure'),
            Output('two-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('two-cat-filter', 'value'),
            Input('two-num-filter-min', 'value'),
            Input('two-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'two')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'two')
            return fig, insights

    if 'three' in all_plots.keys():
        @app.callback(
            Output('three-chart', 'figure'),
            Output('three-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('three-cat-filter', 'value'),
            Input('three-num-filter-min', 'value'),
            Input('three-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'three')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'three')
            return fig, insights

    if 'four' in all_plots.keys():
        @app.callback(
            Output('four-chart', 'figure'),
            Output('four-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('four-cat-filter', 'value'),
            Input('four-num-filter-min', 'value'),
            Input('four-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'four')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'four')
            return fig, insights

    if 'five' in all_plots.keys():
        @app.callback(
            Output('five-chart', 'figure'),
            Output('five-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('five-cat-filter', 'value'),
            Input('five-num-filter-min', 'value'),
            Input('five-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'five')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'five')
            return fig, insights

    if 'six' in all_plots.keys():
        @app.callback(
            Output('six-chart', 'figure'),
            Output('six-insights', 'children'),  # Add output for insights
            Input('tabs', 'value'),
            Input('six-cat-filter', 'value'),
            Input('six-num-filter-min', 'value'),
            Input('six-num-filter-max', 'value')
        )
        def update_chart(tab, category, num_min, num_max):
            fig = update_chart_sub_func(tab, category, num_min, num_max, 'six')
            insights = update_insights_sub_func(tab, category, num_min, num_max, 'six')
            return fig, insights



    # Stop button callback — kills the process
    @app.callback(
        Output("stop-button", "children"),
        Input("stop-button", "n_clicks"),
        prevent_initial_call=True
    )
    def stop_app(n_clicks):
        if n_clicks > 0:
            # Gracefully exit
            os._exit(0)  # force kill the process
    
    print("Starting DashBoard")
    app.run(debug=False)