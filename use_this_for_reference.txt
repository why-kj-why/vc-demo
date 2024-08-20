import streamlit as st
import requests
import pandas as pd
import pymysql
import time
import plotly.express as px

# Database Configuration
DB_HOST = "tellmoredb.cd24ogmcy170.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASS = "2yYKKH8lUzaBvc92JUxW"
DB_PORT = "3306"
DB_NAME = "claires_data"
CONVO_DB_NAME = "store_questions"

# Declaring Colors
CLAIRE_DEEP_PURPLE = '#553D94'
CLAIRE_MAUVE = '#D2BBFF'

# Initialize session state variables
if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'display_df_and_nlr' not in st.session_state:
    st.session_state['display_df_and_nlr'] = False

if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')


def connect_to_db(db_name):
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASS,
        db=db_name
    )


def send_message_to_api(message):
    api_url = "http://127.0.0.1:5000/response"
    payload = {"database": DB_NAME, "query": message}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            st.error("Error decoding JSON")
            return None
    else:
        st.error(f"Error: HTTP {response.status_code} - {response.text}")
        return None


def execute_query(query, connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            getResult = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
        return pd.DataFrame(getResult, columns=columns)
    finally:
        connection.close()


def store_question_in_db(question, sql_query):
    connection = connect_to_db(CONVO_DB_NAME)
    query = "INSERT INTO pinned_questions (question, sql_query) VALUES (%s, %s)"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (question, sql_query))
        connection.commit()
    finally:
        connection.close()


def get_queries_from_db():
    connection = connect_to_db(CONVO_DB_NAME)
    query = "SELECT DISTINCT question, sql_query FROM pinned_questions;"
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

        .button-container {
            display: flex;
            justify-content: flex-end; /* Align button to the right */
            margin-top: 10px;
        }

        .circular-button {
            border-radius: 50%;
            background-color: #553D94; /* Button color */
            color: white;
            border: none;
            padding: 10px 15px; /* Adjust size as needed */
            cursor: pointer;
        }

        .circular-button:hover {
            background-color: #452a7f; /* Slightly darker shade on hover */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def store_ops_app():
    # Load the logo
    with open(r'Claires_logo.svg', 'r') as image:
        image_data = image.read()
    st.logo(image=image_data)

    st.markdown(f"""
    <h4 style="background-color: {CLAIRE_DEEP_PURPLE}; color: white; padding: 10px;">
        Ask a Question
    </h4>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)

    # div.stButton > button:first-child {
    #     border-radius: 50%;
    #     background-color: #553D94; /* Button color */
    #     color: white;
    #     border: none;
    #     padding: 10px 15px; /* Adjust size as needed */
    #     cursor: pointer;
    # }
    # </style>
    # """, unsafe_allow_html=True)

    # Check if the SAVE button is pressed
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            # Clear the input and stop further execution without removing the chatbox
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

    # Only process new input if SAVE wasn't just pressed
    if st.session_state['user_input'] and not save_button_pressed:
        st.session_state.history.append({
            "question": st.session_state['user_input'],
            "nlr": """
The data table returned provides information on the sales performance of different stores for this year and the previous year. The table includes columns such as STORE_ID, STORE_NAME, SALES_TY (sales for this year), and SALES_LY (sales for the previous year).\n\n
Looking at the data, we can observe that the sales for most stores vary between this year and the previous year. Some stores have seen an increase in sales, while others have experienced a decrease.\n\n
For example, stores like BRISTOL SUPERSTORE, CWMBRAN, and CARDIFF have seen an increase in sales this year compared to the previous year. On the other hand, stores like NEWPORT, CRIBBS CAUSEWAY, and SWANSEA have shown a decrease in sales.\n\n
It is also interesting to note that some stores have had significant changes in sales performance. For instance, stores like West End New, Budapest Arena Plaza, and Arkad Budapest have experienced a significant increase in sales this year compared to the previous year. Conversely, stores like Budapest Vaci Utca and Gyor Arkad have seen a significant decrease in sales.\n\n
Overall, the data table provides a comparison of sales performance across all stores for this year against the previous year, highlighting the varying trends in sales for different stores.
""",
            "sql": "SELECT DISTINCT STORE_ID, STORE_NAME, SALES_TY, SALES_LY FROM claires_data.store_total;"
        })
        conn = connect_to_db(DB_NAME)
        result = execute_query("SELECT DISTINCT STORE_ID, STORE_NAME, SALES_TY, SALES_LY FROM claires_data.store_total;", conn)
        st.session_state['display_df_and_nlr'] = True
        st.session_state['last_result'] = result
        st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

    if st.session_state['display_df_and_nlr']:
        st.dataframe(st.session_state['last_result'], height=200)
        time.sleep(1)
        st.write(st.session_state['last_nlr'])


def store_manager_app():
    # Load the logo
    with open(r'Claires_logo.svg', 'r') as image:
        image_data = image.read()
    st.logo(image=image_data)

    # Load queries from the database
    if 'queries' not in st.session_state:
        # st.session_state['queries'] = {
        #     "Store ID": {"Select a query": None},
        #     "STORE023": get_queries_from_db(),
        #     "STORE095": get_queries_from_db(),
        #     "STORE246": get_queries_from_db()
        # }

        st.session_state["queries"] = {
            "Store ID": {"Select a query": None},
            "STORE023": {'Select a query': None, 'Compare the sales performance for BRISTOL SUPERSTORE for this year against the previous year': 'SELECT DISTINCT STORE_ID, STORE_NAME, SALES_TY, SALES_LY FROM claires_data.store_total;'},
            "STORE095": {'Select a query': None, 'Compare the sales performance for CWMBRAN for this year against the previous year': 'SELECT DISTINCT STORE_ID, STORE_NAME, SALES_TY, SALES_LY FROM claires_data.store_total;'},
            "STORE246": {'Select a query': None, 'Compare the sales performance for GLASGOW BRAEHEAD for this year against the previous year': 'SELECT DISTINCT STORE_ID, STORE_NAME, SALES_TY, SALES_LY FROM claires_data.store_total;'},
        }

    st.markdown(f"""
    <h4 style="background-color: {CLAIRE_DEEP_PURPLE}; color: white; padding: 10px;">
        Simulate a Store
    </h4>
    """, unsafe_allow_html=True)

    # Placeholder for the store name and ID, will be updated dynamically
    store_name_id_placeholder = st.markdown(f"""
    <h4 style="background-color: {CLAIRE_MAUVE}; color: black; padding: 10px;">
    </h4>
    """, unsafe_allow_html=True)

    # st.markdown("""
    # <style>
    # div.stButton {
    #     display: flex;
    #     justify-content: flex-end; /* Align button to the right */
    #     margin-top: 10px;
    # }

    # div.stButton > button:first-child {
    #     border-radius: 50%;
    #     background-color: #553D94; /* Button color */
    #     color: white;
    #     border: none;
    #     padding: 10px 15px; /* Adjust size as needed */
    #     cursor: pointer;
    # }
    # </style>
    # """, unsafe_allow_html=True)

    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)

    unpin_button_pressed = st.button("DELETE", key='unpin_button')

    selected_store = st.selectbox("Select a Store", ["Store ID", "STORE023", "STORE095", "STORE246"])

    # Update the mauve bar based on the selected store
    if selected_store != "Store ID":
        store_name = {
            "STORE023": "BRISTOL SUPERSTORE",
            "STORE095": "CWMBRAN",
            "STORE246": "GLASGOW BRAEHEAD"
        }.get(selected_store, "")

        store_name_id_placeholder.markdown(f"""
        <h4 style="background-color: {CLAIRE_MAUVE}; color: black; padding: 10px;">
            {store_name}, {selected_store}
        </h4>
        """, unsafe_allow_html=True)

    queries_for_store = st.session_state['queries'].get(selected_store, {})
    query_options = list(queries_for_store.keys())
    selected_query = st.selectbox("Select a query", query_options if query_options else ["Select a query"])

    if unpin_button_pressed:
        if selected_query != "Select a query":
            # Remove the query from the dictionary and update the session state
            queries_for_store.pop(selected_query, None)
            st.session_state['queries'][selected_store] = queries_for_store
            st.success(f"Query '{selected_query}' has been removed.")
        else:
            st.warning("Select a query to unpin.")

    # Prevent query execution when UNPIN is pressed
    if selected_store and selected_query and selected_query != "Select a query" and not unpin_button_pressed:
        if selected_store == "STORE023":
            time.sleep(1)
            st.markdown("""
            The data table returned reports on the sales performance of STORE023 - BRISTOL SUPERSTORE for this year and the previous year.\n\nThe BRISTOL SUPERSTORE branch has seen a 3.6% increase in annual sales this year.\n\nThe average increase in sales for all Claire's Accessories stores this year has been: -1.19%\n
            """)
        elif selected_store == "STORE095":
            time.sleep(1)
            st.markdown("""
            The data table returned reports on the sales performance of STORE095 - CWMBRAN for this year and the previous year.\n\nThe CWMBRAN branch has seen an 8.2% decrease in annual sales this year.\n\nThe average increase in sales for all Claire's Accessories stores this year has been: -1.19%\n
            """)
        elif selected_store == "STORE246":
            time.sleep(1)
            st.markdown("""
            The data table returned reports on the sales performance of STORE246 - GLASGOW BRAEHEAD for this year and the previous year.\n\nThe GLASGOW BRAEHEAD branch has seen an 8.8% decrease in annual sales this year.\n\nThe average increase in sales for all Claire's Accessories stores this year has been: -1.19%\n
            """)


# Main Application
set_custom_css()

# Sidebar for toggling between personas
persona = st.sidebar.radio("", ("Ask a Question", "Simulate a Store"))

# Load the corresponding persona app
if persona == "Ask a Question":
    store_ops_app()

elif persona == "Simulate a Store":
    store_manager_app()
