# ------ Vocabulary Builder & Smart Flashcards ------
# Run with:  streamlit run app.py

import streamlit as st

from modules.dictionary_api import DictionaryAPIError, DictionaryClient, WordNotFoundError
from modules.flashcard import Flashcard, FlashcardDeck
from modules.gemini_api import AIContentGenerator
from modules.quiz import QuizError, QuizGenerator
from modules.spaced_repetition import SpacedRepetitionManager
from modules.storage import DataManager, StorageError
from modules.validation import InvalidWordError

st.set_page_config(page_title="Vocabulary Builder", page_icon="📚")


# ------ Create the helpers once ------
# Streamlit reruns this file on every click. st.cache_resource keeps these
# objects (and the caches inside them) alive between reruns.

@st.cache_resource
def get_services():
    ai = AIContentGenerator()
    return DictionaryClient(), ai, QuizGenerator(ai), SpacedRepetitionManager()


dictionary, ai, quiz_maker, scheduler = get_services()
data = DataManager()
deck = FlashcardDeck(data)

# ------ Remembered between reruns ------

for key, default in {
    "word": None,           # the Word from the last search
    "ai_content": None,     # Gemini content for that word
    "revealed": None,       # the flashcard whose answer is showing
    "quiz": None,           # the current quiz questions
    "quiz_source": None,    # "ai" or "saved definitions"
    "quiz_result": None,    # the score once submitted
    "quiz_answers": None,
    "quiz_id": 0,           # changes per quiz, so old answers don't carry over
}.items():
    st.session_state.setdefault(key, default)

# ------ Main title and subtitle ------

st.title("Vocabulary Builder & Smart Flashcard App")
st.write("Search a word, learn it with AI help, save it as a flashcard, review it and test yourself.")

data.load()
if data.load_error:
    st.error(data.load_error)

# ------ Creating 4 tabs ------

tab1, tab2, tab3, tab4 = st.tabs([
    "🔎 Dictionary",
    "🃏 Flashcards & Review",
    "📝 Quiz & Scores",
    "🤖 Gemini AI",
])


def save_flashcard(word):
    """Create a flashcard for the word (with AI content) and save it."""
    with st.spinner("Creating your flashcard..."):
        content = ai.get_learning_content(word.text, definition=word.first_definition)
    card = Flashcard.from_word(word, content)
    try:
        added = deck.add(card)
    except StorageError as error:
        st.error(str(error))
        return
    if added:
        st.success(f"'{word.text}' saved to your flashcards!")
        if content["source"] == "fallback":
            st.caption(f"Saved without AI content: {content['error']}")
    else:
        st.info(f"'{word.text}' is already in your flashcards.")


# -------- Tab1: Dictionary ------

with tab1:
    st.header("🔎 Dictionary search")

    with st.form("search_form"):
        query = st.text_input("Enter a word to search", placeholder="e.g. resilient")
        searched = st.form_submit_button("Search")

    if searched:
        try:
            with st.spinner("Looking up the word..."):
                st.session_state.word = dictionary.lookup(query)
            st.session_state.ai_content = None
        except InvalidWordError as error:
            st.error(str(error))
        except WordNotFoundError as error:
            st.warning(str(error))
        except DictionaryAPIError as error:
            st.error(str(error))

    word = st.session_state.word
    if word:
        st.subheader(word.text)
        if word.phonetic:
            st.write(f"**Phonetics:** {word.phonetic}")
        if word.audio_url:
            st.audio(word.audio_url)

        for meaning in word.meanings:
            st.markdown(f"**{meaning['part_of_speech']}**")
            for number, item in enumerate(meaning["definitions"][:3], start=1):
                st.write(f"{number}. {item['definition']}")
                if item["example"]:
                    st.caption(f"Example: {item['example']}")

        st.write("**Synonyms:** " + (", ".join(word.synonyms[:10]) or "none found"))
        st.write("**Antonyms:** " + (", ".join(word.antonyms[:10]) or "none found"))

        if st.button("💾 Save to Flashcards", key="save_tab1"):
            save_flashcard(word)
        st.caption("Open the Gemini AI tab for a simple explanation and a memory trick.")
    else:
        st.info("Enter a word to search the dictionary!")

# ------ Tab2: Flashcards & Review ------

with tab2:
    st.header("🃏 Flashcards & Review")
    cards = deck.all()
    due = scheduler.due_cards(cards)

    col1, col2 = st.columns(2)
    col1.metric("Saved words", len(cards))
    col2.metric("Due for review today", len(due))

    st.subheader("Review")
    if not cards:
        st.info("Your saved flashcards will appear here. Search a word and save it first.")
    elif not due:
        st.success("Nothing to review today. Come back tomorrow!")
    else:
        card = due[0]
        st.caption(f"{len(due)} card(s) left to review today · box {card.box}")
        st.markdown(f"## {card.word}")
        if card.phonetic:
            st.write(card.phonetic)

        if st.session_state.revealed != card.word:
            if st.button("Show answer"):
                st.session_state.revealed = card.word
                st.rerun()
        else:
            st.write(f"**Definition:** {card.definition}")
            if card.explanation:
                st.write(f"**In simple words:** {card.explanation}")
            if card.example:
                st.write(f"**Example:** {card.example}")
            if card.memory_trick:
                st.info(f"💡 {card.memory_trick}")

            left, right = st.columns(2)
            remembered = left.button("✅ I remembered", width="stretch")
            forgot = right.button("❌ I forgot", width="stretch")
            if remembered or forgot:
                scheduler.review(card, remembered=remembered)
                try:
                    deck.update(card)
                except StorageError as error:
                    st.error(str(error))
                else:
                    st.session_state.revealed = None
                    st.rerun()

    st.subheader("All saved flashcards")
    for card in cards:
        with st.expander(f"{card.word} · next review {scheduler.describe_next_review(card)}"):
            st.write(f"**Definition:** {card.definition}")
            if card.explanation:
                st.write(f"**In simple words:** {card.explanation}")
            if card.example:
                st.write(f"**Example:** {card.example}")
            if card.memory_trick:
                st.write(f"**Memory trick:** {card.memory_trick}")
            if card.synonyms:
                st.write(f"**Synonyms:** {', '.join(card.synonyms)}")
            st.caption(f"Saved {card.created} · box {card.box}")
            if st.button("Delete", key=f"delete_{card.word}"):
                try:
                    deck.remove(card.word)
                except StorageError as error:
                    st.error(str(error))
                else:
                    st.rerun()

# ------ Tab3: Quiz & Scores ------

with tab3:
    st.header("📝 Quiz & Scores")
    quiz = st.session_state.quiz

    if quiz is None:
        cards = deck.all()
        if not cards:
            st.info("Save some words to your flashcards first, then take a quiz.")
        else:
            st.write(f"The quiz uses your {len(cards)} saved word(s).")
            num_questions = st.slider("Number of questions", 3, 10, 5)
            if st.button("Start quiz"):
                try:
                    with st.spinner("Creating your quiz..."):
                        questions, source = quiz_maker.build_quiz(cards, num_questions)
                except QuizError as error:
                    st.warning(str(error))
                else:
                    st.session_state.quiz = questions
                    st.session_state.quiz_source = source
                    st.session_state.quiz_result = None
                    st.session_state.quiz_id += 1
                    st.rerun()
    else:
        if st.session_state.quiz_source != "ai":
            st.info("The AI is unavailable right now, so these questions use your saved definitions.")

        result = st.session_state.quiz_result
        if result is None:
            with st.form("quiz_form"):
                answers = []
                for number, question in enumerate(quiz, start=1):
                    answers.append(st.radio(
                        f"**Q{number}.** {question['question']}",
                        question["options"],
                        index=None,
                        key=f"quiz{st.session_state.quiz_id}_q{number}",
                    ))
                submitted = st.form_submit_button("Submit answers")

            if submitted:
                if None in answers:
                    st.warning("Please answer every question before submitting.")
                else:
                    result = quiz_maker.score(quiz, answers)
                    try:
                        data.add_quiz_score(result)
                    except StorageError as error:
                        st.error(str(error))
                    st.session_state.quiz_result = result
                    st.session_state.quiz_answers = answers
                    st.rerun()
        else:
            st.success(f"You scored {result['score']} out of {result['total']} ({result['percent']}%)")
            for number, (question, answer) in enumerate(
                zip(quiz, st.session_state.quiz_answers), start=1
            ):
                mark = "✅" if quiz_maker.check_answer(question, answer) else "❌"
                st.markdown(f"{mark} **Q{number}.** {question['question']}")
                st.write(f"Your answer: {answer} · Correct answer: {question['correct_answer']}")
                st.caption(question["explanation"])

            if st.button("New quiz"):
                st.session_state.quiz = None
                st.session_state.quiz_result = None
                st.rerun()

    st.subheader("Score history")
    scores = data.get_quiz_scores()
    if scores:
        st.dataframe(
            [
                {"Date": s["date"], "Score": f"{s['score']}/{s['total']}", "Percent": s["percent"]}
                for s in reversed(scores)
            ],
            hide_index=True,
            width="stretch",
        )
        if len(scores) > 1:
            st.line_chart([s["percent"] for s in scores], y_label="Percent", x_label="Quiz number")
    else:
        st.info("Your quiz scores will appear here.")

# ------ Tab4: Gemini AI Helper ------

with tab4:
    st.header("🤖 Gemini AI Helper")
    word = st.session_state.word

    if not word:
        st.info("Search a word in the Dictionary tab first.")
    else:
        st.write(f"AI learning content for **{word.text}**")
        if st.button("Generate AI explanation"):
            with st.spinner("Asking Gemini..."):
                st.session_state.ai_content = ai.get_learning_content(
                    word.text, definition=word.first_definition
                )

        content = st.session_state.ai_content
        if content and content["word"] == word.text:
            if content["source"] == "fallback":
                st.warning(content["error"])
            st.subheader("Simple explanation")
            st.write(content["explanation"])
            if content["examples"]:
                st.subheader("Example sentences")
                for example in content["examples"]:
                    st.write(f"• {example}")
            if content["memory_trick"]:
                st.subheader("Memory trick")
                st.info(f"💡 {content['memory_trick']}")

            if st.button("💾 Save to Flashcards", key="save_tab4"):
                save_flashcard(word)
