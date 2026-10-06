# Vocabulary Builder & Smart Flashcard App

Group 15 · Python Advanced Cohort 37 · NITDA / NCAIR

A Streamlit app that helps learners understand, practise and remember new words.

**Flow:** search a word → see its definition, phonetics, examples, synonyms and antonyms → get a simple AI explanation, example sentences and a memory trick → save it as a flashcard → review it with spaced repetition → take a quiz → see your saved scores.

## Setup

1. Install Python 3.10 or newer.
2. Install the packages:
   ```
   pip install -r requirements.txt
   ```
3. Get a free Gemini API key at https://aistudio.google.com/apikey and save it as an environment variable (Windows):
   ```
   setx GEMINI_API_KEY "your-key-here"
   ```
   Then close and reopen your terminal or VS Code. Never put the key in the code.
4. Run the app:
   ```
   streamlit run app.py
   ```

The app still works without a key: dictionary search, flashcards and reviews work, and quizzes are built from saved definitions instead of AI questions.

## Project structure

| File | What it does |
| --- | --- |
| `app.py` | Streamlit interface with 4 tabs: Dictionary, Flashcards & Review, Quiz & Scores, Gemini AI |
| `modules/dictionary_api.py` | `Word` and `DictionaryClient`: looks words up in the Free Dictionary API with `requests` |
| `modules/gemini_api.py` | `AIContentGenerator`: simple explanations, example sentences, memory tricks and quiz questions from Gemini |
| `modules/flashcard.py` | `Flashcard` and `FlashcardDeck`: creating, saving and loading flashcards |
| `modules/spaced_repetition.py` | `SpacedRepetitionManager`: Leitner boxes (review after 1, 2, 4, 7, 14, 30 days) |
| `modules/quiz.py` | `QuizGenerator`: builds quizzes, shuffles options, checks answers and scores |
| `modules/storage.py` | `DataManager`: saves flashcards and quiz scores in `data.json` |
| `modules/validation.py` | regular expressions to validate words and clean text |
| `data.json` | the saved flashcards and quiz scores |

## Python concepts used

- **OOP:** `Word`, `Flashcard`, `FlashcardDeck`, `DictionaryClient`, `AIContentGenerator`, `QuizGenerator`, `SpacedRepetitionManager`, `DataManager`
- **File handling:** JSON storage, with safe writes and a backup of damaged files
- **Exception handling:** word not found, empty or invalid input, dictionary and AI errors (with retries and fallbacks), file read/write errors
- **Regular expressions:** validating words, removing punctuation, cleaning AI text
- **`random`:** shuffling quiz questions and answer options
- **`datetime`:** flashcard review schedules and quiz dates

## Team (roles from the project proposal)

| Member | Role |
| --- | --- |
| Hassan Shehu | Project Lead & Integration |
| Ayomide Oshunlalu | Dictionary API Module |
| Omobolaji Oniyanda | AI/Gemini Module |
| Jesse Angulu | Flashcard Module |
| Ayman Aruwa | Spaced Repetition Module |
| Mariyam Abdullahi | Quiz Module |
| Annick Benjamin | Data & Validation |
| Salma Ismail | Streamlit UI |
