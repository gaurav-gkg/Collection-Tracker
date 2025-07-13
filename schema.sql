-- Table: people
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

-- Table: collections
CREATE TABLE IF NOT EXISTS collections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id INTEGER,
  date TEXT,
  collected BOOLEAN,
  amount REAL,
  FOREIGN KEY (person_id) REFERENCES people(id),
  UNIQUE (person_id, date)
); 