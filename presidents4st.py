import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import random
import time
import google.generativeai as genai
import key

# gemini api setup
genai.configure(api_key=key.mykey)
model = genai.GenerativeModel("gemini-2.0-flash")
gemini_cache: dict[str, str] = {}

def ask_gemini(request: str) -> str:
    if request not in gemini_cache:
        response = model.generate_content(request)
        gemini_cache[request] = response.text
    return gemini_cache[request]

# streamlit setup
st.set_page_config(page_title="President Quiz", layout="centered")

@st.cache_data
def fetch_presidents():
    url = "https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    presidents = []
    tables = soup.find_all('table', class_='wikitable')

    for row in tables[0].find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 2:
            name_cell = cols[1]
            link = name_cell.find('a')
            name = link.text.strip() if link else None

            image_cell = cols[0]
            img_tag = image_cell.find('img')
            image_url = "https:" + img_tag['src'] if img_tag else None

            if name and image_url:
                presidents.append({"name": name, "image": image_url})
    return presidents

# Game State
if 'score' not in st.session_state:
    st.session_state.score = 0
    st.session_state.current_question = 0
    st.session_state.used_names = set()
    st.session_state.game_over = False
    st.session_state.correct_president = None
    st.session_state.options = []
    st.session_state.clicked_option = None
    st.session_state.feedback_text = ""

presidents = fetch_presidents()

st.markdown("""
    <style>
    .main { background-color: #e0e0e0; }
    .stApp { background-color: #e0e0e0; }
    .question-box {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 0px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .custom-progress .stProgress > div > div {
        background-color: #555 !important;
    }
    .fact-line {
        font-size: 24px;
        margin-bottom: 14px;
    }
    .stButton > button {
        font-size: 22px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Load new question if needed
if not st.session_state.game_over and not st.session_state.correct_president:
    remaining = [p for p in presidents if p['name'] not in st.session_state.used_names]
    if len(remaining) == 0 or st.session_state.current_question >= 10:
        st.session_state.game_over = True
    else:
        st.session_state.correct_president = random.choice(remaining)
        st.session_state.used_names.add(st.session_state.correct_president['name'])

        wrong_choices = [p for p in presidents if p['name'] != st.session_state.correct_president['name']]
        st.session_state.options = random.sample(wrong_choices, 3) + [st.session_state.correct_president]
        random.shuffle(st.session_state.options)

# Quiz in progress
if not st.session_state.game_over and st.session_state.correct_president:
    president = st.session_state.correct_president['name']
    prompt = f"please write three descriptive sentences of up to 200 characters about {president}. the descriptive sentences should unique features about the president, and can mention events and matters he dealt with, but not disclose his identity directly, like mentioning whom he succeeded or what was the number of his presidency, years of his tenure, etc., and not use too general information like 'he was an outstanding diplomat/ speaker', which could fit many others as well"
    facts = ask_gemini(prompt)

    with st.container():
        st.markdown('<div class="question-box">', unsafe_allow_html=True)

        col_img, col_desc = st.columns([1, 2])
        with col_img:
            st.image(Image.open(BytesIO(requests.get(st.session_state.correct_president['image']).content)), width=250)

        with col_desc:
            for line in facts.split('\n'):
                clean = line.strip()
                if clean and not clean.lower().startswith("here are") and not clean.endswith(":"):
                    st.markdown(f"<div class='fact-line'>{clean}</div>", unsafe_allow_html=True)

        st.markdown('<div class="custom-progress">', unsafe_allow_html=True)
        st.progress((st.session_state.current_question) / 10)
        st.markdown('</div>', unsafe_allow_html=True)

        st.write(f"**Question {st.session_state.current_question + 1} of 10**")

        if not st.session_state.clicked_option:
            for option in st.session_state.options:
                if st.button(option['name']):
                    st.session_state.clicked_option = option['name']
                    if option['name'] == st.session_state.correct_president['name']:
                        st.session_state.score += 1
                        st.session_state.feedback_text = "✅ Correct!"
                    else:
                        correct = st.session_state.correct_president['name']
                        st.session_state.feedback_text = f"❌ Nope! It was {correct}."
                    st.rerun()
        else:
            st.write(st.session_state.feedback_text)
            time.sleep(1)
            st.session_state.current_question += 1
            st.session_state.correct_president = None
            st.session_state.options = []
            st.session_state.clicked_option = None
            st.session_state.feedback_text = ""
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# Game over screen
if st.session_state.game_over:
    st.markdown("---")
    st.header(f"Game Over! You scored {st.session_state.score} out of 10.")
    if st.button("Play Again"):
        st.session_state.score = 0
        st.session_state.current_question = 0
        st.session_state.used_names = set()
        st.session_state.correct_president = None
        st.session_state.options = []
        st.session_state.clicked_option = None
        st.session_state.feedback_text = ""
        st.session_state.game_over = False
        st.rerun()
