"""
Spaced Repetition module: decides when each flashcard should be reviewed.

It uses the Leitner box system. Every card starts in box 1. Remembering a
card moves it up one box, so it comes back after a longer gap. Forgetting
it sends it back to box 1, so it comes back tomorrow.

    Box:            1    2    3    4    5    6
    Review after:   1    2    4    7   14   30  days

    from modules.spaced_repetition import SpacedRepetitionManager

    manager = SpacedRepetitionManager()
    due = manager.due_cards(deck.all())        # cards to review today
    manager.review(card, remembered=True)       # updates card.box and card.next_review
"""

from datetime import date, timedelta

# Days to wait before the next review, for boxes 1, 2, 3, ...
DEFAULT_INTERVALS = (1, 2, 4, 7, 14, 30)


class SpacedRepetitionManager:
    """Schedules flashcard reviews with the Leitner box system."""

    def __init__(self, intervals=DEFAULT_INTERVALS):
        self.intervals = intervals

    @property
    def max_box(self):
        return len(self.intervals)

    def is_due(self, card, today=None):
        today = today or date.today()
        return date.fromisoformat(card.next_review) <= today

    def due_cards(self, cards, today=None):
        """Cards due today or earlier, the most overdue first."""
        due = [card for card in cards if self.is_due(card, today)]
        return sorted(due, key=lambda card: card.next_review)

    def review(self, card, remembered, today=None):
        """Record a review and schedule the next one. Changes the card in place."""
        today = today or date.today()
        if remembered:
            card.box = min(card.box + 1, self.max_box)
        else:
            card.box = 1
        wait_days = self.intervals[card.box - 1]
        card.next_review = (today + timedelta(days=wait_days)).isoformat()
        return card

    def describe_next_review(self, card, today=None):
        """A friendly description, e.g. "today", "tomorrow" or "in 4 days"."""
        today = today or date.today()
        days = (date.fromisoformat(card.next_review) - today).days
        if days <= 0:
            return "today"
        if days == 1:
            return "tomorrow"
        return f"in {days} days"
