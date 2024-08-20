import streamlit as st
import pandas as pd
import pymysql
# import plotly.express as px
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
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            getResult = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
        return pd.DataFrame(getResult, columns=columns)
    finally:
        connection.close()


def store_question_in_db(question, sql_query, response, persona):
    connection = connect_to_db(CONVO_DB_NAME)
    query = f"INSERT INTO {persona}_questions (question, sql_query) VALUES (%s, %s)"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (question, sql_query, response))
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
            store_question_in_db(last_chat['question'], last_chat['sql'], last_chat['nlr'], persona)
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    for chat in st.session_state.history:
        st.write(f"**User:** {chat['question']}")
        st.write(f"**Natural Language Response:** {chat['nlr']}")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])

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
                time.sleep(1)
                st.write(st.session_state['last_nlr'])


def management_app():
    return


st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

set_custom_css()

# with open(r'tellmore_logo.svg', 'r') as image:
#     image_data = image.read()
# st.logo(image=image_data)

selected_option = st.selectbox("SUPER ADMIN", personas)

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
        ops_selection = st.sidebar.radio("Toggle View", ["STORE OPS", "STORE MANAGEMENT"])
        if ops_selection == "STORE OPS":
            selected_persona = "store"
            store_questions = {
                "Give a daily breakdown UPT for all product categories for each store during May":
                    {
                        "sql": "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        "nlr": "To provide a daily breakdown of Units Per Transaction (UPT) for all product categories for the month of May, we can group the data by the Sale_Date and calculate the average UPT for each day.\n\nHere is the daily breakdown of UPT for all product categories for the month of May:\n\nMay 1st: 5.83\nMay 2nd: 5.53\nMay 3rd: 5.69\nMay 4th: 5.60\nMay 5th: 5.64\nMay 6th: 4.94\nMay 7th: 5.15\nMay 8th: 5.64\nMay 9th: 5.08\nMay 10th: 5.51\nMay 11th: 5.58\nMay 12th: 5.47\nMay 13th: 5.07\nMay 14th: 5.21\nMay 15th: 5.48\nMay 16th: 5.24\nMay 17th: 5.50\nMay 18th: 5.39\nMay 19th: 5.33\nMay 20th: 5.29\n\nPlease note that the values provided are rounded to two decimal places.",
                    }
            }
            st.title("STORE OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            corporate_app(selected_persona, store_questions)
        elif ops_selection == "STORE MANAGEMENT":
            st.title("STORE MANAGEMENT")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            management_app()

    elif selected_option == "MERCHANDISING OPS":
        st.title("MERCHANDISING OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["MERCHANDISING OPS", "MERCHANDISING MANAGEMENT"])

    elif selected_option == "WAREHOUSE OPS":
        st.title("WAREHOUSE OPS")
        ops_selection = st.sidebar.radio("Toggle View", ["WAREHOUSE OPS", "WAREHOUSE MANAGEMENT"])
