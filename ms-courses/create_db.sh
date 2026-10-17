#!/bin/bash

sqlite3 courses.db <<EOF
CREATE TABLE IF NOT EXISTS courses (
    ID INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL
);
EOF

echo "Database 'courses.db' and table 'courses' created."
