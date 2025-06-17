-- Multi-hostel system database migration
-- Creates tables for hostels and users, adds hostel_id to existing tables

-- Create hostels table
CREATE TABLE IF NOT EXISTS hostels (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    contact_person TEXT,
    contact_email TEXT,
    contact_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL, -- Changed from password to password_hash
    full_name TEXT,
    role TEXT NOT NULL CHECK (role IN ('owner', 'manager')),
    hostel_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hostel_id) REFERENCES hostels(id)
);

-- Add hostel_id to students table
ALTER TABLE students ADD COLUMN hostel_id INTEGER REFERENCES hostels(id);

-- Add hostel_id to rooms table
ALTER TABLE rooms ADD COLUMN hostel_id INTEGER REFERENCES hostels(id);

-- Add hostel_id to fees table
ALTER TABLE fees ADD COLUMN hostel_id INTEGER REFERENCES hostels(id);

-- Add hostel_id to complaints table
ALTER TABLE complaints ADD COLUMN hostel_id INTEGER REFERENCES hostels(id);

-- Create expenses table for tracking hostel expenses
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    expense_date DATE DEFAULT CURRENT_DATE,
    category TEXT NOT NULL, -- Maintenance, Utilities, Food, Supplies, Staff, Other
    expense_type TEXT DEFAULT 'Operational', -- Operational, Capital, Emergency
    vendor_name TEXT,
    receipt_number TEXT,
    payment_method TEXT DEFAULT 'Cash', -- Cash, Card, Bank Transfer, Cheque
    approved_by INTEGER,
    notes TEXT,
    hostel_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (hostel_id) REFERENCES hostels(id) ON DELETE SET NULL
);

-- Create indexes for expenses
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_hostel_id ON expenses(hostel_id);
CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(expense_type);

-- Insert default owner account
INSERT INTO users (username, password_hash, full_name, role) -- Changed from password to password_hash
VALUES ('owner', '$2b$12$HxhX/DHPa9PFB1jVIGwA1eBWpuQrGH.DW1g5ULG/Fz4YRQxWW8ety', 'Hostel Owner', 'owner');
-- Note: password is 'owner123' hashed with bcrypt
