CREATE TABLE IF NOT EXISTS
tasks(
    task_id integer primary key autoincrement,
    task_name text not null,
    duration int not null,
    due_date text,
    priority int
);
CREATE TABLE IF NOT EXISTS
events(
    event_id integer primary key autoincrement,
    task_id integer,
    start_time text not null,
    end_time text not null,
    monday boolean not null,
    tuesday boolean not null,
    wednesday boolean not null,
    thursday boolean not null,
    friday boolean not null,
    saturday boolean not null,
    sunday boolean not null
);