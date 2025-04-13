-- Drop existing tables if they exist
DROP TABLE IF EXISTS journal_entries CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Journal entries table
CREATE TABLE journal_entries (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_journal_entries_owner_id ON journal_entries(owner_id);
CREATE INDEX idx_users_email ON users(email);
