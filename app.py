# ------ Vocabulary Builder & Smart Flashcards ------

import streamlit as st
import re

# ------ Main title and subtitle ------

st.title("Vocabulary Builder & Smart Flashcard App")
st.write("Welcome! This is the main application hub.")

# ------ Creating 4 tabs ------

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎Dictionary",
    "🃏Flashcards & Review",
    "📝Quiz & Scores",
    "🤖 Gemini AI"
])

# ------ With statement so our python knows which tab the elements belong to ------
# -------- Tab1: Dictionary ------

with tab1:
    st.header("🔎 Dictionary search")
    st.info("Enter a word to search the dictionary!")

    word = st.text_input("Enter a word to search",
                         placeholder="e.g. resilient")
    if st.button("Search"):
        if word:
            if re.fullmatch(r"[A-Za-z]+", word.strip()):

                st.success(f"Searching for: {word.strip()}")
            else:
                st.error("Please enter a valid word using letters only.")
        else:
            st.warning("Please enter a word.")

    st.subheader("Word Information")
    st.write("Defintion: _")
    st.write("Phonetics: _")
    st.write("Examples: _")
    st.write("Synonyms: _")
    st.write("Antonyms: _")

    if st.button("🍱 Save to Flashcards"):
        st.success("Word saved to flashcards!")

# ------ Tab2: Flashcards & Scores ------

with tab2:
    st. header("🃏  Flashcards & Review")
    st.info("Your saved flashcards will appear here")

# ------ Tab3: Quiz & Scores ------

with tab3:
    st.header("📝Quiz & Scores")
    st.info("Your quizzes & scores will appear here")

 # ------ Tab4: Gemini AI Helper ------

with tab4:
    st.header("🤖 Gemini AI Helper")
    st.info("AI-generated learning content will appear here.")
