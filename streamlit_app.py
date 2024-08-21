import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
import time

DB_HOST = "tellmoredb.cd24ogmcy170.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASS = "2yYKKH8lUzaBvc92JUxW"
DB_PORT = "3306"
DB_NAME = "retail_panopticon"
CONVO_DB_NAME = "store_questions"

if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'display_df_and_nlr' not in st.session_state:
    st.session_state['display_df_and_nlr'] = False

if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

personas = [
    "Select a Persona",
    "INVENTORY OPS",
    "LOSS PREVENTION OPS",
    "MARKETING OPS",
    "STORE OPS",
    "MERCHANDISING OPS",
    "WAREHOUSE OPS"
]


def connect_to_db(db_name):
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASS,
        db=db_name
    )


def execute_query(query, connection):
    # try:
    with connection.cursor() as cursor:
        cursor.execute(query)
        getResult = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
    return pd.DataFrame(getResult, columns=columns)
    # finally:
    #     connection.close()


def store_question_in_db(question, sql_query):
    connection = connect_to_db(CONVO_DB_NAME)
    query = "INSERT INTO store_questions (question, sql_query) VALUES (%s, %s)"
    try:
        with connection.cursor() as cursor:
            # cursor.execute(query, (question, sql_query, response)) # issue no. 1
            cursor.execute(query, (question, sql_query))
        connection.commit()
    finally:
        connection.close()


def get_queries_from_db(persona):
    connection = connect_to_db(CONVO_DB_NAME)
    query = f"SELECT DISTINCT question, sql_query FROM {persona}_questions;"
    df = execute_query(query, connection)
    questions = {"Select a query": None}
    questions.update(dict(zip(df['question'], df['sql_query'])))
    return questions


def set_custom_css():
    custom_css = """
    <style>
        .st-emotion-cache-9aoz2h.e1vs0wn30 {
            display: flex;
            justify-content: center; /* Center-align the DataFrame */
        }
        .st-emotion-cache-9aoz2h.e1vs0wn30 table {
            margin: 0 auto; /* Center-align the table itself */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def corporate_app(persona, questions_dict):
    col = st.columns((2, 1, 1), gap='medium')

    with col[0]:
        st.markdown("""
        <style>
        div.stButton {
            display: flex;
            justify-content: flex-end; /* Align button to the right */
            margin-top: 10px;
        }
        """, unsafe_allow_html=True)
        save_button_pressed = st.button('SAVE', key='save_button')

        if save_button_pressed:
            if st.session_state.history:
                last_chat = st.session_state.history[-1]
                store_question_in_db(last_chat['question'], last_chat['sql'])
                st.success("Last conversation stored.")
                st.session_state['user_input'] = ""
                st.session_state['display_df_and_nlr'] = False
                st.session_state['last_result'] = None
                st.session_state['last_nlr'] = None
            else:
                st.warning("No conversation to store.")

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])

        for chat in st.session_state.history:
            st.write(f"**User:** {chat['question']}")
            st.write(f"**Natural Language Response:** {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state['user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])

    with col[1]:
        st.subheader("Visualizations")
        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "Give a daily breakdown UPT for all product categories for each store during May":
                pie_fig = px.pie(
                    st.session_state['last_result'],
                    values='UPT',
                    names='Product_Category',
                    title='Sum of UPT by Product Category'
                )
                st.plotly_chart(pie_fig)

                time.sleep(1)

                filtered_data = st.session_state['last_result'][st.session_state['last_result']['Product_Category'].isin(['Clothing', 'Toys'])]
                line_fig = px.line(
                    filtered_data,
                    x='Sale_Date',
                    y='UPT',
                    color='Product_Category',
                    title='Product Category Sales report'
                )
                line_fig.update_layout(
                    xaxis_title='Sale_Date',
                    yaxis_title='Sum of UPT',
                    legend_title='Product Category'
                )
                st.plotly_chart(line_fig)

            elif st.session_state['user_input'] == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                fig2 = px.bar(
                    df,
                    y='Category',
                    x='total_sales',
                    color='day_type',
                    title='Total Sales by Day Type for Each Product Category',
                    labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                    barmode='group',
                    orientation='h',
                    color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                )
                st.plotly_chart(fig2)

                fig3 = px.bar(
                    df,
                    x='Category',
                    y='avg_transaction_value',
                    color='day_type',
                    title='Average Transaction Value by Day Type for Each Product Category',
                    labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                    barmode='stack',
                    text_auto=True,
                    color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                )
                st.plotly_chart(fig3)

            elif st.session_state['user_input'] == "Give the total shipments delivered late and the reason for the delay for each product category":
                fig_pie = px.sunburst(
                    result,
                    path=['Category', 'Reason_Late_Shipment'],
                    values='Total_Late_Shipments',
                    title='Reasons for Late Shipments by Product Category',
                    color='Reason_Late_Shipment',
                    color_discrete_sequence=px.colors.qualitative.Set3  # Different colors for each reason
                )
                st.plotly_chart(fig_pie)

    with col[2]:
        st.write("")
        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "Give a daily breakdown UPT for all product categories for each store during May":
                bar_fig = px.bar(
                    st.session_state['last_result'],
                    x='UPT',
                    y='Store_ID',
                    orientation='h',  # Horizontal bar chart
                    title='Sum of UPT by Store_ID'
                )
                bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})  # Sort bars by UPT
                st.plotly_chart(bar_fig)

                time.sleep(1)

                pie_fig = px.pie(
                    st.session_state['last_result'],
                    values='UPT',
                    names='Product_Category',
                    title='Sum of UPT by Product Category'
                )
                st.plotly_chart(pie_fig)

            elif st.session_state['user_input'] == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                fig = px.bar(
                    df,
                    x='Category',
                    y='sales_percentage',
                    color='day_type',
                    title='Percentage of Total Sales by Day Type for Each Product Category',
                    labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                    text_auto=True,
                    barmode='stack'
                )
                st.plotly_chart(fig)

                fig1 = px.bar(
                    df,
                    y='Category',
                    x='total_transactions',
                    color='day_type',
                    title='Total Transactions by Day Type for Each Product Category',
                    labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                    barmode='group',
                    orientation='h',
                    color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                )
                st.plotly_chart(fig1)

            elif st.session_state['user_input'] == "Give the total shipments delivered late and the reason for the delay for each product category":
                total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                fig_bar = px.bar(
                    total_shipments_by_category,
                    y='Category',
                    x='Total_Late_Shipments',
                    title='Total Late Shipments by Product Category',
                    labels={'Total_Late_Shipments': 'Total Late Shipments'},
                    color='Category',
                    color_discrete_sequence=px.colors.qualitative.Pastel  # Different color scheme for categories
                )
                st.plotly_chart(fig_bar)


def management_app(persona, options):
    queries = get_queries_from_db(persona)
    col = st.columns((2, 1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }

    div.stButton > button:first-child {
        border-radius: 50%;
        background-color: #553D94; /* Button color */
        color: white;
        border: none;
        padding: 10px 15px; /* Adjust size as needed */
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
        unpin_button_pressed = st.button("DELETE", key='unpin_button')
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        drop_down = st.selectbox("Select", options)
        selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "Store ID":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE has a UPT of 5.38 as compared to the average of 5.48\n
                    Electronics:\tWATER TOWER PLACE does not sell Electronics items\n
                    Food:\t\tWATER TOWER PLACE has a UPT of 5.64 as compared to the average of 5.51\n
                    Furniture:\tWATER TOWER PLACE has a UPT of 5.55 as compared to the average of 5.5\n
                    Toys:\t\tWATER TOWER PLACE does not sell Toys items\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA does not sell Clothing items\n
                    Electronics:\tRIVERFRONT PLAZA does not sell Electronics items\n
                    Food:\t\tRIVERFRONT PLAZA does not sell Food items\n
                    Furniture:\tRIVERFRONT PLAZA has a UPT of 5.46 as compared to the average of 5.5\n
                    Toys:\t\tRIVERFRONT PLAZA has a UPT of 5.58 as compared to the average of 5.48\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON has a UPT of 5.5 as compared to the average of 5.49\n
                    Electronics:\tWESTFIELD WHEATON does not sell Electronics items\n
                    Food:\t\tWESTFIELD WHEATON has a UPT of 5.55 as compared to the average of 5.51\n
                    Furniture:\tWESTFIELD WHEATON has a UPT of 5.47 as compared to the average of 5.5\n
                    Toys:\t\tWESTFIELD WHEATON has a UPT of 5.45 as compared to the average of 5.48\n
                    """)

            elif selected_query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE saw a 288% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tWATER TOWER PLACE saw a 235% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tWATER TOWER PLACE saw a 236% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tWATER TOWER PLACE saw a 287% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tWATER TOWER PLACE saw a 272% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA saw a 230% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tRIVERFRONT PLAZA saw a 300% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tRIVERFRONT PLAZA saw a 256% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tRIVERFRONT PLAZA saw a 255% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tRIVERFRONT PLAZA saw a 255% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON saw a 242% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tWESTFIELD WHEATON saw a 332% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tWESTFIELD WHEATON saw a 275% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tWESTFIELD WHEATON saw a 231% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tWESTFIELD WHEATON saw a 298% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

            elif selected_query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Electronics:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Food:\t\tWATER TOWER PLACE has no Delayed Shipments\n
                    Furniture:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Toys:\t\tWATER TOWER PLACE has no Delayed Shipments\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Electronics:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Food:\t\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Furniture:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Toys:\t\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Electronics:\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Food:\t\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Furniture:\tWESTFIELD WHEATON had 7055 delayed shipments, mostly due to Weather Conditions. On average, there were 7472 shipments delayed due to Weather Conditions in the same time frame.\n
                    Toys:\t\tWESTFIELD WHEATON has no Delayed Shipments\n
                    """)

    with col[1]:
        st.subheader("Visualizations")
        if selected_query and drop_down:
            if selected_query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE01' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)

                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

                    time.sleep(1)

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )
                    st.plotly_chart(line_fig)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE28' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)
                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

                    time.sleep(1)

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )
                    st.plotly_chart(line_fig)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE49' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)
                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

                    time.sleep(1)

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )
                    st.plotly_chart(line_fig)

            elif selected_query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE01' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales by Day Type for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )
                    st.plotly_chart(fig2)

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value by Day Type for Each Product Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )
                    st.plotly_chart(fig3)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE28' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales by Day Type for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )
                    st.plotly_chart(fig2)

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value by Day Type for Each Product Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )
                    st.plotly_chart(fig3)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE49' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales by Day Type for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )
                    st.plotly_chart(fig2)

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value by Day Type for Each Product Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )
                    st.plotly_chart(fig3)
            elif selected_query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE01' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_pie)
                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE28' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_pie)
                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE49' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_pie)

    with col[2]:
        st.write("")
        if selected_query and drop_down:
            if selected_query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE01' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)

                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',  # Horizontal bar chart
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})  # Sort bars by UPT
                    st.plotly_chart(bar_fig)

                    time.sleep(1)

                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE28' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)
                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',  # Horizontal bar chart
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})  # Sort bars by UPT
                    st.plotly_chart(bar_fig)

                    time.sleep(1)

                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE49' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;", conn)
                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',  # Horizontal bar chart
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})  # Sort bars by UPT
                    st.plotly_chart(bar_fig)

                    time.sleep(1)

                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )
                    st.plotly_chart(pie_fig)

            elif selected_query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE01' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Percentage of Total Sales by Day Type for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )
                    st.plotly_chart(fig)

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions by Day Type for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    st.plotly_chart(fig1)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE28' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Percentage of Total Sales by Day Type for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )
                    st.plotly_chart(fig)

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions by Day Type for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    st.plotly_chart(fig1)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE49' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;", conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Percentage of Total Sales by Day Type for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )
                    st.plotly_chart(fig)

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions by Day Type for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    st.plotly_chart(fig1)

            elif selected_query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE01' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)

                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_bar)
                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE28' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)
                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_bar)
                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query("SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE49' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;", conn)
                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig_bar)


st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

set_custom_css()

# with open(r'tellmore_logo.svg', 'r') as image:
#     image_data = image.read()
# st.logo(image=image_data)

col1, col2 = st.columns([4, 1])

with col2:
    selected_option = st.selectbox("", personas, key='super_admin_selectbox')

if selected_option == "Select a Persona":
    st.title("SUPER ADMIN")
else:
    if selected_option == "INVENTORY OPS":
        st.title("INVENTORY OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["INVENTORY OPS", "INVENTORY MANAGEMENT"])

    elif selected_option == "LOSS PREVENTION OPS":
        st.title("LOSS PREVENTION OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["LOSS PREVENTION OPS", "LOSS PREVENTION MANAGEMENT"])

    elif selected_option == "MARKETING OPS":
        st.title("MARKETING OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["MARKETING OPS", "MARKETING MANAGEMENT"])

    elif selected_option == "STORE OPS":
        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["STORE OPS", "STORE MANAGEMENT"])
        if ops_selection == "STORE OPS":
            store_questions = {
                "Give a daily breakdown UPT for all product categories for each store during May":
                    {
                        "sql": "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        "nlr": "To provide a daily breakdown of Units Per Transaction (UPT) for all product categories for the month of May, we can group the data by the Sale_Date and calculate the average UPT for each day.\n\nHere is the daily breakdown of UPT for all product categories for the month of May:\n\nMay 1st: 5.83\nMay 2nd: 5.53\nMay 3rd: 5.69\nMay 4th: 5.60\nMay 5th: 5.64\nMay 6th: 4.94\nMay 7th: 5.15\nMay 8th: 5.64\nMay 9th: 5.08\nMay 10th: 5.51\nMay 11th: 5.58\nMay 12th: 5.47\nMay 13th: 5.07\nMay 14th: 5.21\nMay 15th: 5.48\nMay 16th: 5.24\nMay 17th: 5.50\nMay 18th: 5.39\nMay 19th: 5.33\nMay 20th: 5.29\n\nPlease note that the values provided are rounded to two decimal places.",
                    },
                "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                    {
                        "sql": "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        "nlr": "Weekdays saw higher total sales and transaction volumes across all product categories, indicating that promotional discounts drove more frequent and larger purchases during the week.\n\nHowever, weekends had a slightly higher average transaction value in categories like Furniture and Electronics, suggesting that while fewer purchases were made, they tended to be more significant.\n\nOverall, the promotions were more effective on weekdays, but the higher weekend transaction values hint at opportunities to target high-value weekend shoppers more effectively.",
                    },
                "Give the total shipments delivered late and the reason for the delay for each product category":
                    {
                        "sql": "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        "nlr": "The data table provides a detailed breakdown of the total late shipments and reasons for delays across different product categories. For each category, multiple reasons contribute to late deliveries, such as high demand, logistical issues, and customs delays.\n\nThe pie chart visualizes the distribution of reasons for late shipments within each product category. This chart highlights the proportion of each delay reason, providing insight into the most common causes for each category.\n\nThe horizontal bar chart shows the total number of late shipments per product category. This chart helps in understanding which categories experienced the highest volume of late deliveries, guiding efforts to address specific issues and improve shipping efficiency.",
                    },
            }
            st.title("STORE OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            corporate_app(selected_persona, store_questions)
        elif ops_selection == "STORE MANAGEMENT":
            stores = [
                "Store ID",
                "WATER TOWER PLACE",
                "RIVERFRONT PLAZA",
                "WESTFIELD WHEATON"
            ]
            st.title("STORE MANAGEMENT")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            management_app(selected_persona, stores)

    elif selected_option == "MERCHANDISING OPS":
        st.title("MERCHANDISING OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["MERCHANDISING OPS", "MERCHANDISING MANAGEMENT"])

    elif selected_option == "WAREHOUSE OPS":
        st.title("WAREHOUSE OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["WAREHOUSE OPS", "WAREHOUSE MANAGEMENT"])
