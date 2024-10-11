import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import webbrowser

# Set app title and icon
st.set_page_config(page_title="FocusTrack", page_icon="static/icon.png")

# Load environment variables
load_dotenv()

# App Version
APP_VERSION = '1.45'  # Incremented version number

# File paths
USER_DATA_FILE = 'user_data.csv'
TASKS_DATA_FILE = 'tasks_data.csv'
COMPLETED_TASKS_FILE = 'completed_tasks.csv'
TIMER_HTML_FILE = 'timer.html'
ICON_FILE_PATH = 'static/icon.png'  # Local file path for the icon

# Initialize session state
def initialize_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'tasks' not in st.session_state:
        st.session_state['tasks'] = []
    if 'current_task' not in st.session_state:
        st.session_state['current_task'] = None
    if 'timer_end' not in st.session_state:
        st.session_state['timer_end'] = None
    if 'edit_mode' not in st.session_state:
        st.session_state['edit_mode'] = -1  # Use -1 to indicate no edit mode active
    if 'show_completed' not in st.session_state:
        st.session_state['show_completed'] = False
    if 'choice' not in st.session_state:
        st.session_state['choice'] = 'Login'  # Default choice

initialize_session_state()

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Functions to handle user data
def load_user_data():
    if os.path.exists(USER_DATA_FILE) and os.path.getsize(USER_DATA_FILE) > 0:
        return pd.read_csv(USER_DATA_FILE)
    else:
        return pd.DataFrame(columns=['username', 'password', 'email'])

def save_user_data(username, password, email):
    user_data = load_user_data()
    hashed_password = hash_password(password)
    new_user = pd.DataFrame({'username': [username], 'password': [hashed_password], 'email': [email]})
    user_data = pd.concat([user_data, new_user], ignore_index=True)
    user_data.to_csv(USER_DATA_FILE, index=False)

def authenticate_user(username, password):
    user_data = load_user_data()
    hashed_password = hash_password(password)
    user = user_data[(user_data['username'] == username) & (user_data['password'] == hashed_password)]
    return not user.empty

# Functions to handle task data
def load_tasks_data():
    if os.path.exists(TASKS_DATA_FILE) and os.path.getsize(TASKS_DATA_FILE) > 0:
        try:
            tasks_df = pd.read_csv(TASKS_DATA_FILE)
            required_columns = ['username', 'task_name', 'duration', 'completed']
            for column in required_columns:
                if column not in tasks_df.columns:
                    tasks_df[column] = '' if column != 'duration' else 0
            return tasks_df
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=['username', 'task_name', 'duration', 'completed'])
    else:
        return pd.DataFrame(columns=['username', 'task_name', 'duration', 'completed'])

def save_tasks_data(tasks_list):
    tasks_df = pd.DataFrame(tasks_list, columns=['username', 'task_name', 'duration', 'completed'])
    tasks_df.to_csv(TASKS_DATA_FILE, index=False)

def load_completed_tasks():
    if os.path.exists(COMPLETED_TASKS_FILE) and os.path.getsize(COMPLETED_TASKS_FILE) > 0:
        try:
            return pd.read_csv(COMPLETED_TASKS_FILE)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=['username', 'task_name', 'completion_date'])
    else:
        return pd.DataFrame(columns=['username', 'task_name', 'completion_date'])

def save_completed_task(username, task_name):
    completed_tasks_df = load_completed_tasks()
    new_entry = pd.DataFrame({
        'username': [username],
        'task_name': [task_name],
        'completion_date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    })
    completed_tasks_df = pd.concat([completed_tasks_df, new_entry], ignore_index=True)
    completed_tasks_df.to_csv(COMPLETED_TASKS_FILE, index=False)

def get_user_tasks(username):
    tasks_df = load_tasks_data()
    return tasks_df[tasks_df['username'] == username].to_dict('records')

def add_task_to_csv(username, task_name, duration):
    tasks_df = load_tasks_data()
    new_task = pd.DataFrame({
        'username': [username],
        'task_name': [task_name],
        'duration': [duration],
        'completed': [False]
    })
    tasks_df = pd.concat([tasks_df, new_task], ignore_index=True)
    save_tasks_data(tasks_df.to_dict('records'))

def complete_task(task_index):
    task = st.session_state['tasks'][task_index]
    save_completed_task(st.session_state['username'], task['task_name'])
    st.session_state['tasks'].pop(task_index)
    save_tasks_data(st.session_state['tasks'])

# Function to start the Pomodoro timer and generate timer.html
def start_timer(task_index):
    task = st.session_state['tasks'][task_index]
    st.session_state['current_task'] = task
    st.session_state['timer_end'] = datetime.now() + timedelta(minutes=task['duration'])

    end_time = st.session_state['timer_end'].strftime('%Y-%m-%d %H:%M:%S')
    task_name = task['task_name']

    countdown_html = f"""
    <html>
    <head>
        <title>Pomodoro Timer</title>
        <link rel="icon" href="static/icon.png" type="image/png">
    </head>
    <body style="text-align: center; font-family: Arial, sans-serif;">
        <h1>Countdown Timer</h1>
        <h2 id="taskName" style="color: blue;">Task: {task_name}</h2>
        <p id="countdown" style="font-size: 48px; color: red;"></p>
        <button id="breakButton" style="display: none;" onclick="startBreak()">Start Break</button>
        <script>
            var endTime = new Date("{end_time}").getTime();
            var timerInterval = setInterval(function() {{
                var now = new Date().getTime();
                var distance = endTime - now;

                if (distance > 0) {{
                    var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    document.getElementById("countdown").innerHTML = minutes + "m " + seconds + "s ";
                }} else {{
                    document.getElementById("countdown").innerHTML = "Time's up!";
                    document.getElementById("breakButton").style.display = "block";
                    clearInterval(timerInterval);
                }}
            }}, 1000);

            function startBreak() {{
                var breakDuration = {5 if task['duration'] < 52 else 20};
                var breakEndTime = new Date(new Date().getTime() + breakDuration * 60 * 1000).getTime();
                document.getElementById("breakButton").style.display = "none";

                var breakInterval = setInterval(function() {{
                    var now = new Date().getTime();
                    var distance = breakEndTime - now;

                    if (distance > 0) {{
                        var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                        var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                        document.getElementById("countdown").innerHTML = "Break Time: " + minutes + "m " + seconds + "s ";
                    }} else {{
                        document.getElementById("countdown").innerHTML = "Break is over!";
                        clearInterval(breakInterval);
                    }}
                }}, 1000);
            }}
        </script>
    </body>
    </html>
    """

    # Use Streamlit's HTML component to display the timer directly in the app
    components.html(countdown_html, height=600)

def login_signup_page():
    st.title("Login or Sign Up")
    st.write(f"App Version: {APP_VERSION}")
    choice = st.radio("Choose an option", ["Login", "Sign Up"], key='choice')

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    email = st.text_input("Email") if choice == "Sign Up" else None

    if choice == "Sign Up":
        if st.button("Create Account"):
            if username and password and email:
                user_data = load_user_data()
                if username in user_data['username'].values:
                    st.warning("Username already exists. Please choose a different one.")
                elif email in user_data['email'].values:
                    st.warning("Email already in use. Please use a different email.")
                else:
                    save_user_data(username, password, email)
                    st.success("Account created successfully! Redirecting...")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.experimental_rerun()  # Redirect to the main page
    else:
        if st.button("Login"):
            if username and password:
                if authenticate_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['tasks'] = get_user_tasks(username)
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password.")
            else:
                st.warning("Please fill in both fields.")

def load_and_filter_completed_tasks(username):
    completed_tasks_df = load_completed_tasks()
    user_completed = completed_tasks_df[completed_tasks_df['username'] == username]
    return user_completed

def show_tasks_and_form():
    st.subheader("Add a New Task")
    with st.form("task_form"):
        task_name = st.text_input("Task Name")
        task_duration = st.selectbox("Duration (minutes)", options=[25, 18, 52])
        submitted = st.form_submit_button("Add Task")
        if submitted and task_name:
            add_task_to_csv(st.session_state['username'], task_name, task_duration)
            st.session_state['tasks'] = get_user_tasks(st.session_state['username'])
            st.experimental_rerun()

    st.subheader("Your Tasks")
    if st.session_state['tasks']:
        for i, task in enumerate(st.session_state['tasks']):
            task_name = task['task_name']
            task_duration = task['duration']

            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            with col1:
                st.write(f"{i + 1}. {task_name} - {task_duration} mins")
            with col2:
                if st.button(f"Start", key=f"start_{i}"):
                    start_timer(i)
            with col3:
                if st.button(f"Edit", key=f"edit_{i}"):
                    st.session_state['edit_mode'] = i
                    st.experimental_rerun()
            with col4:
                if st.button(f"Delete", key=f"delete_{i}"):
                    st.session_state['tasks'].pop(i)
                    save_tasks_data(st.session_state['tasks'])
                    st.experimental_rerun()
            with col5:
                if st.button(f"Complete", key=f"complete_{i}"):
                    complete_task(i)
                    st.experimental_rerun()

    if st.session_state['edit_mode'] != -1:
        edit_task_index = st.session_state['edit_mode']
        task_to_edit = st.session_state['tasks'][edit_task_index]

        st.write("### Edit Task")
        with st.form("edit_task_form"):
            edited_task_name = st.text_input("Task Name", value=task_to_edit['task_name'])
            edited_task_duration = st.selectbox("Duration (minutes)", options=[25, 18, 52], index=[25, 18, 52].index(task_to_edit['duration']))
            save_changes = st.form_submit_button("Save")
            cancel_changes = st.form_submit_button("Cancel")

            if save_changes:
                st.session_state['tasks'][edit_task_index] = {
                    'username': st.session_state['username'],
                    'task_name': edited_task_name,
                    'duration': edited_task_duration,
                    'completed': task_to_edit['completed']
                }
                save_tasks_data(st.session_state['tasks'])
                st.session_state['edit_mode'] = -1
                st.experimental_rerun()

            if cancel_changes:
                st.session_state['edit_mode'] = -1
                st.experimental_rerun()

    show_completed = st.checkbox("Show Completed Tasks", value=st.session_state.get('show_completed', False))
    
    if show_completed:
        user_completed = load_and_filter_completed_tasks(st.session_state['username'])
        if not user_completed.empty:
            st.write("### Completed Tasks")
            user_completed['completion_date'] = pd.to_datetime(user_completed['completion_date'])
            user_completed = user_completed.sort_values('completion_date', ascending=False)
            user_completed['completion_date'] = user_completed['completion_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.table(user_completed[['task_name', 'completion_date']])
        else:
            st.write("No completed tasks yet.")

def todo_app():
    st.title(f"FocusTrack - Welcome, {st.session_state['username']}!")
    st.write(f"App Version: {APP_VERSION}")
    show_tasks_and_form()

if __name__ == "__main__":
    if not st.session_state.get('logged_in', False):
        login_signup_page()
    else:
        todo_app()
