import datetime


class SpacedRepetitionManager:

    def __init__(self, date, time):
        self.date = date
        self.time = time

    def convert_date(self, date):
        return datetime.datetime.strptime(date, "%Y-%m-%d")

    def convert_time(self, time):
        return datetime.datetime.strptime(time, "%H:%M")

    def schedule_review(self, rating):

        if rating == "easy":
            day = 7

        elif rating == "medium":
            day = 4

        elif rating == "hard":
            day = 1

        else:
            return "Invalid rating"

        current_date = self.convert_date(self.date)

        next_review = current_date + datetime.timedelta(days=day)

        return next_review