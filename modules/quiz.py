"""
Quiz module: builds quizzes from saved flashcards, checks answers and scores them.

Questions come from the Gemini module. If the AI isn't available, the quiz
is built from the saved definitions instead, so a quiz is always possible.

    from modules.quiz import QuizGenerator

    quiz = QuizGenerator(ai_generator)
    questions, source = quiz.build_quiz(deck.all(), num_questions=5)
    result = quiz.score(questions, answers)     # answers = the user's choices
"""

import random
import re
from datetime import datetime

from modules.gemini_api import AIServiceError

QUESTION_KEYS = ("word", "question_type", "question", "options", "correct_answer", "explanation")


class QuizError(Exception):
    """Raised when a quiz can't be made (e.g. not enough saved words)."""


def _hide_word(text, word):
    """Replace the word (and forms like "happier") with ____ so it doesn't give the answer away."""
    return re.sub(rf"\b{re.escape(word)}\w*", "____", text, flags=re.IGNORECASE)


class QuizGenerator:
    """Creates quiz questions, checks answers and calculates scores."""

    def __init__(self, ai_generator=None):
        # The Gemini AIContentGenerator, or None to only use saved definitions.
        self.ai = ai_generator

    def build_quiz(self, cards, num_questions=5):
        """Return (questions, source).

        questions: list of dicts with the keys in QUESTION_KEYS, options shuffled.
        source: "ai" or "saved definitions", so the UI can say where they came from.

        Raises:
            QuizError: if there are no saved words, or too few for a quiz without AI.
        """
        if not cards:
            raise QuizError("Save some words to your flashcards first, then take a quiz.")

        questions, source = None, "ai"
        if self.ai is not None:
            try:
                questions = self.ai.generate_quiz(
                    [card.word for card in cards],
                    definitions={card.word: card.definition for card in cards if card.definition},
                    num_questions=num_questions,
                )
            except AIServiceError:
                questions = None    # fall back to saved definitions below

        if questions is None:
            questions, source = self._questions_from_cards(cards, num_questions), "saved definitions"

        # Randomise the order of questions and of each question's options.
        random.shuffle(questions)
        for question in questions:
            random.shuffle(question["options"])
        return questions[:num_questions], source

    @staticmethod
    def _questions_from_cards(cards, num_questions):
        """'Which word means ...?' questions, with other saved words as wrong options."""
        usable = [card for card in cards if card.definition]
        if len(usable) < 2:
            raise QuizError(
                "The AI is unavailable, and a quiz from saved definitions needs at "
                "least 2 saved words. Save more words or try again later."
            )
        chosen = random.sample(usable, min(num_questions, len(usable)))
        questions = []
        for card in chosen:
            others = [other.word for other in usable if other.word != card.word]
            options = random.sample(others, min(3, len(others))) + [card.word]
            questions.append({
                "word": card.word,
                "question_type": "meaning",
                "question": f"Which word means: \"{_hide_word(card.definition, card.word)}\"?",
                "options": options,
                "correct_answer": card.word,
                "explanation": f"'{card.word}' means: {card.definition}",
            })
        return questions

    @staticmethod
    def check_answer(question, answer):
        """True if the user's answer is the correct one."""
        return answer == question["correct_answer"]

    def score(self, questions, answers):
        """Score a finished quiz. answers[i] is the user's choice for questions[i].

        Returns a dict ready to be saved with DataManager.add_quiz_score().
        """
        correct = sum(
            self.check_answer(question, answer) for question, answer in zip(questions, answers)
        )
        total = len(questions)
        return {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score": correct,
            "total": total,
            "percent": round(100 * correct / total) if total else 0,
            "words": sorted({question["word"] for question in questions}),
        }
