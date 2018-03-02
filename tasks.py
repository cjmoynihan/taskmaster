__author__ = 'cj'
import datetime
str_from_datetime = lambda date_time: date_time.strftime('%c')
datetime_from_str = lambda s: datetime.datetime.strptime(s, '%c')
minutes_from_timedelta = lambda delta: delta.totalseconds() / 60.0

import itertools
import sqlite3 as sq3

# Set priorities!!
HIGH = 0
MEDIUM = HIGH+5
LOW = MEDIUM+5
NO_PRIORITY = LOW*20

DAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')

DB_NAME = 'tasks.db'


class Database:
    def __init__(self):
        self.conn = sq3.connect(DB_NAME)
        self.c = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        with open('schema.sql', 'r') as f:
            for command in ''.join(line for line in f).split(';'):
                self.c.execute(command)
        self.conn.commit()

    def add_task(self, task):
        self.c.execute("INSERT INTO tasks(task_name, duration, due_date, priority) VALUES(?, ?, ?, ?)",
                       (task.name, minutes_from_timedelta(task.duration), str_from_datetime(task.due_date), task.priority))
        self.c.execute("SELECT last_insert_row_id()")
        self.conn.commit()
        return self.c.fetchone()

    def get_tasks(self):
        self.c.execute("SELECT * FROM tasks")
        return [Task(name, datetime.timedelta(minutes=duration), datetime_from_str(due_date), priority)
                for (_id, name, duration, due_date, priority)
                in self.c]

    def add_event(self, event, task_id=None):
        if task_id is None:
            task_id = self.add_task(event)
        self.c.execute("""INSERT INTO events(
        task_id, start_time, end_time, monday, tuesday, wednesday, thursday, friday, saturday, sunday)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       [task_id, event.start_time, event.end_time] + [event.which_days[day] for day in DAYS])
        self.c.execute("SELECT last_insert_row_id()")
        self.conn.commit()
        return self.c.fetchone()

    def get_events(self):
        self.c.execute("""SELECT
        task_name, duration, due_date, priority, start_time, end_time,
        monday, tuesday, wednesday, thursday, friday, saturday, sunday
        FROM events NATURAL JOIN tasks ON task_id""")
        return [Event(Task(task_name, datetime.timedelta(minutes=duration), datetime_from_str(due_date), priority),
                      start_time, end_time, monday, tuesday, wednesday, thursday, friday, saturday, sunday)
                for (task_name, duration, due_date, priority, start_time, end_time,
                     monday, tuesday, wednesday, thursday, friday, saturday, sunday)
                in self.c]

class Anytime:
    """
    A due date, for whenever
    """
    def __eq__(self, other):
        # Only true if both anytime
        return isinstance(other, Anytime)

    def __lt__(self, other):
        # Should always be false! Like math.inf
        return False

    def __gt__(self, other):
        # If they are no equal, then it's bigger!
        return not self.__eq__(other)

    def __add__(self, other):
        return Anytime()

    def __sub__(self, other):
        return Anytime()


class Calendar:
    # Running tally of what is actually happening
    def __init__(self, database=None):
        self.tasks = list()
        self.definite_events = list()
        # Assumes that the recurring events are added here
        # self.recurring_events = {day: list() for day in DAYS}
        self.recurring_events = list()

    def _add_task(self, task):
        self.tasks.append(task)

    def add_task(self, *args, **kwargs):
        self._add_task(Task(*args, **kwargs))

    def add_event(self, event):
        """
        If the event is recurring, adds it to for each day of the week
        """
        if event.recurring:
            self.recurring_events.append(event)
            # for day in DAYS:
            #     if getattr(event, day):
            #         getattr(self.recurring_events, day).append(event)
        else:
            self.definite_events.append(event)

    def recurring_event_days(self):
        """
        Gets events by day, sorted by endtime
        """
        return {day: sorted((event for event in self.recurring_events if event.day), key=lambda e: e.endtime.time()) for day in DAYS}

    def check_recurring_conflict(self):
        """
        Returns true if there are any recurring conflicts on the same day
        """
        for (day, events) in self.recurring_event_days().items():
            for (prev_event, event) in zip(events, events[1:]):
                if prev_event.end_time.time() > event.end_time.time():
                    return True
        return False

    def check_all_conflict(self):
        """
        Returns true if there are at least two definite events with overlap
        and false otherwise
        """
        if self.check_recurring_conflict():
            return True
        # There must not be a recurring conflict past this point
        # Generate all of the dates for which an event occurs
        separate_dates = set()
        for event in self.definite_events:
            for date_ranges in range((event.end_time.date() - event.start_time.date()).days() + 1):
                separate_dates.add(event.start_time.date() + datetime.timedelta(date_ranges))
        recurring_event_days = self.recurring_event_days()
        # Mix in recurring events on all those days
        all_events = self.definite_events + list(itertools.chain(*[
            map(lambda event: event.generate_recurring(date), recurring_event_days[DAYS[date.weekday()]])
            for date in separate_dates]))
        # Order again by the end times
        all_events.sort(key=lambda event: event.end_time)
        for (prev_event, event) in zip(all_events, all_events[1:]):
            if prev_event.end_time > event.start_time:
                return True
        return False

    def assign_tasks(self, break_time=datetime.timedelta(minutes=15)):
        """
        Generates a possible series of events given requirements and events
        """
        # Ordering by earliest deadline minimized lateness
        # Sorts by earliest due date, w/ ties broken by priority then shortest duration
        self.tasks.sort(key=lambda task: (task.due_date, task.priority, task.duration))
        events = list()
        # Give a short headstart
        start = datetime.datetime.now() + datetime.timedelta(minutes=5)
        # Breakdown the break stuff to make it easier
        if not isinstance(break_time, datetime.timedelta):
            break_time = datetime.timedelta(break_time)
        break_task = Task('BREAK', duration=break_time)
        # Fill out the events with events and breaks
        for task in self.tasks:
            events.append(Event(task.name, start))
            start += task.duration
            # Take a break. You deserve it :)
            events.append(Event(break_task, start))
            start += break_time
        return events

    def assign_all_events(self, break_time=datetime.timedelta(minutes=15)):
        # First assign the 'definite' events
        # Then do 1d bin sorting using the tasks, making sure to keep track of recurring events
        raise RuntimeError("Hasn't yet been implemented")

class Task:
    # A currently unassigned event, that hasn't yet been assigned
    def __init__(self, name, duration=datetime.timedelta(minutes=30), due_date=Anytime(), priority=NO_PRIORITY):
        self.name = name
        self.due_date = due_date
        self.priority = priority  # Priority is determined numerically. Low numbers are high priorities
        if not isinstance(duration, datetime.timedelta):
            duration = datetime.timedelta(duration)
        self.duration = duration

    def time_after(self, start=None):
        """
        Determine the time after the task
        """
        if start is None:
            start = datetime.datetime.now()
        return start + self.duration

    def last_chance(self):
        """
        Determine when it must be started at the latest
        """
        return self.due_date - self.duration

    def slack(self, start=None):
        """
        Determine the amount of time between now and when it must be started
        """
        end_time = self.last_chance
        if isinstance(end_time, Anytime):
            return None
        if start is None:
            start = datetime.datetime.now()
        return end_time - start


class Event(Task):
    # Something that is presumed to be happening at a given time
    def __init__(self, task, start_time, end_time=None, monday=False, tuesday=False, wednesday=False,
                 thursday=False, friday=False, saturday=False, sunday=False):
        super().__init__(**task.__dict__)
        self.start_time = start_time
        if end_time is None:
            self.end_time = self.start_time + self.duration
        else:
            self.end_time = end_time
        day_vals = (monday, tuesday, wednesday, thursday, friday, saturday, sunday)
        self.which_days = dict()
        # Add days to event
        for (day_name, day_val) in zip(DAYS, day_vals):
            setattr(self, day_name, day_val)
            self.which_days[day_name] = day_val
        self.recurring = any(day_vals)

    def generate_recurring(self, date):
        """
        Returns a new Event with the same information but for a given date
        Will throw an exception if it doesn't have a recurrance on that day
        """
        if not self.which_days[DAYS[date.weekday()]]:
            raise ValueError("The event {0} doesn't have a recurring date during {1}".format(self.name, DAYS[date.weekday()]))
        return Event(self, start_time=date.date()+self.start_time.time(), end_time=date.date()+self.start_time.time()+self.duration, **self.which_days)

    def __eq__(self, other):
        if isinstance(other, Event):
            if not (self.recurring and other.recurring):
                # If not recurring, just compare all values
                return self.__dict__ == other.__dict__
            # Otherwise, check all values, except replace start and end with their actual times instead of dates
            return (self.name == other.name) and (self.which_days == other.which_days) and \
                   (self.start_time.time() == other.start_time.time()) and \
                   (self.end_time.time() == other.end_time.time())
        return super().__eq__(self, other)

    def __ne__(self, other):
        return not (self == other)

if __name__ == '__main__':
    db = Database()
    cal = Calendar(db)
