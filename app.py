# ------ Vocabulary Builder & Smart Flashcards ------

import streamlit as st
import re
from modules.gemini_api import AIContentGenerator

# ------ Main title and subtitle ------

st.title("Vocabulary Builder & Smart Flashcard App")
st.write("Welcome! This is the main application hub.")

# ------ Creating 4 tabs ------


@st.cache_resource
def get_generator():
    return AIContentGenerator()


generator = get_generator()

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎Dictionary",
    "🃏Flashcards & Review",
    "📝Quiz & Scores",
    "🤖 Gemini AI"
])

# ------ With statement so our python knows which tab the elements belong to ------
# -------- Tab1: Dictionary ------

with tab1:
    st.header("🔎 Dictionary Word")
    st.write("Enter a word to search the dictionary.")

    word = st.text_input(
        "Enter a word to search",
        placeholder="e.g. resilient"
    )

    if st.button("Search"):
        if word:
            if re.fullmatch(r"[A-Za-z]+", word.strip()):
                st.success(f"Searching for: {word.strip()}")

                st.subheader("Word Information")

                st.write(
                    "*Definition:* Able to recover quickly from difficulties.")
                st.write("*Phonetics:* /rɪˈzɪliənt/")
                st.write(
                    "*Example:* She showed a resilient attitude after the setback.")
                st.write("*Synonyms:* strong, adaptable, tough")
                st.write("*Antonyms:* weak, fragile")

                if st.button("💾 Save to Flashcards"):
                    st.success("Word saved to flashcards!")
            else:
                st.error("Please enter a valid word using letters only.")
        else:
            st.warning("Please enter a word.")

# ------ Tab2: Flashcards & Scores ------

with tab2:
    st.header("🃏 Flashcards & Review")
    st.write("Review your saved vocabulary words here.")

    flashcard_word = st.text_input(
        "Word",
        placeholder="e.g. resilient"
    )

    flashcard_definition = st.text_area(
        "Definition",
        placeholder="Enter the word definition"
    )

    if st.button("Save Flashcard"):
        if flashcard_word.strip() and flashcard_definition.strip():
            st.success(f"'{flashcard_word.strip()}' saved to flashcards!")
        else:
            st.warning("Please enter both a word and definition.")

    st.subheader("Review Flashcards")

    if st.button("Show Flashcard"):
        if flashcard_word.strip() and flashcard_definition.strip():
            st.write(f"*Word:* {flashcard_word.strip()}")
            st.write(f"*Definition:* {flashcard_definition.strip()}")
        else:
            st.info("No flashcard available yet.")

# ------ Tab3: Quiz & Scores ------

with tab3:
    st.header("📝 Quiz & Scores")
    st.write("Test your vocabulary knowledge and track your scores.")

    st.subheader("Vocabulary Quiz")

    question = st.text_input(
        "Question",
        placeholder="e.g. What does 'resilient' mean?"
    )

    options = st.radio(
        "Choose your answer:",
        [
            "Able to recover quickly",
            "Unable to change",
            "Very difficult to understand",
            "Extremely tired"
        ]
    )

    if st.button("Submit Answer"):
        if question.strip():
            st.success("Answer submitted!")
        else:
            st.warning("Please enter a question first.")

    st.subheader("Quiz Score")

    score = st.number_input(
        "Score",
        min_value=0,
        value=0,
        step=1
    )

    if st.button("Save Score"):
        st.success(f"Score saved: {score}")

 # ------ Tab4: Gemini AI Helper ------

with tab4:
    st.header("🤖 Gemini AI Helper")
    st.info("Use AI to make vocabulary learning easier.")

    ai_word = st.text_input(
        "Enter a word",
        placeholder="e.g. resilient"
    )

    if st.button("Generate AI Content"):
        if ai_word.strip():
            content = generator.get_learning_content(ai_word.strip())

            if content["error"]:
                st.warning(content["error"])

            st.subheader("Simple Explanation")
            st.write(content["explanation"])

            st.subheader("Example Sentences")
            for example in content["examples"]:
                st.write(f"- {example}")

            st.subheader("Memory Trick")
            st.write(content["memory_trick"])
        else:
            st.warning("Please enter a word first.")
