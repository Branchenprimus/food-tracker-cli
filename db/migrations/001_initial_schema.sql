CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    serving_amount REAL NOT NULL DEFAULT 1.0,
    kcal REAL NOT NULL,
    fat_g REAL NOT NULL,
    carbs_g REAL NOT NULL,
    protein_g REAL NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    date TEXT NOT NULL CHECK(length(date)=10), -- YYYY-MM-DD
    time TEXT NOT NULL CHECK(length(time)=5), -- HH:MM
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    ts_local TEXT GENERATED ALWAYS AS (date || 'T' || time) VIRTUAL
);

CREATE INDEX idx_entries_date ON entries(date);
CREATE INDEX idx_entries_date_time ON entries(date, time);
