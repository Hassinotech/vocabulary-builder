"""
Flashcard module: the Flashcard class, plus creating, saving and loading cards.

    from modules.flashcard import Flashcard, FlashcardDeck

    card = Flashcard.from_word(word, ai_content)   # word from the dictionary module
    deck = FlashcardDeck(data_manager)
    deck.add(card)                                  # saved to data.json
"""

from dataclasses import asdict, dataclass, field, fields
from datetime import date


@dataclass
class Flashcard:
    """One saved word. The front shows the word; the back shows the rest."""

    word: str
    definition: str
    phonetic: str = ""
    example: str = ""
    explanation: str = ""       # from the Gemini module
    memory_trick: str = ""      # from the Gemini module
    synonyms: list = field(default_factory=list)
    created: str = field(default_factory=lambda: date.today().isoformat())
    # Spaced repetition: which box the card is in and when it's next due.
    box: int = 1
    next_review: str = field(default_factory=lambda: date.today().isoformat())

    @classmethod
    def from_word(cls, word, ai_content=None):
        """Create a card from a dictionary Word and (optionally) AI content."""
        ai_content = ai_content or {}
        examples = word.examples or ai_content.get("examples", [])
        return cls(
            word=word.text,
            definition=word.first_definition,
            phonetic=word.phonetic,
            example=examples[0] if examples else "",
            explanation=ai_content.get("explanation", ""),
            memory_trick=ai_content.get("memory_trick", ""),
            synonyms=word.synonyms[:5],
        )

    def to_dict(self):
        """A plain dict, ready to be saved as JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Rebuild a card from saved JSON, ignoring any unknown keys."""
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})


class FlashcardDeck:
    """All saved flashcards, loaded from and saved to the data file."""

    def __init__(self, data_manager):
        self.data = data_manager

    def all(self):
        """Every saved card, as Flashcard objects, in the order they were saved."""
        return [Flashcard.from_dict(item) for item in self.data.get_flashcards()]

    def get(self, word):
        for card in self.all():
            if card.word == word:
                return card
        return None

    def add(self, card):
        """Save a new card. Returns False if the word is already saved."""
        cards = self.all()
        if any(existing.word == card.word for existing in cards):
            return False
        cards.append(card)
        self._save(cards)
        return True

    def update(self, card):
        """Save changes to an existing card (e.g. after a review)."""
        cards = [card if existing.word == card.word else existing for existing in self.all()]
        self._save(cards)

    def remove(self, word):
        self._save([card for card in self.all() if card.word != word])

    def _save(self, cards):
        self.data.save_flashcards([card.to_dict() for card in cards])
