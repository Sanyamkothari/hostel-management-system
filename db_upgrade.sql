-- Upgrading schema for hostel_management_v2

-- Step 1: First check if columns exist, then add only if they don't
-- Add student_id_number if it doesn't exist
SELECT CASE 
    WHEN COUNT(*) = 0 THEN
        'ALTER TABLE students ADD COLUMN student_id_number TEXT DEFAULT NULL;'
    ELSE
        'SELECT 1;' -- Do nothing
END AS sql_command
FROM pragma_table_info('students') 
WHERE name = 'student_id_number'
INTO @sql_command;

PRAGMA @sql_command;

-- Add expected_checkout_date if it doesn't exist
SELECT CASE 
    WHEN COUNT(*) = 0 THEN
        'ALTER TABLE students ADD COLUMN expected_checkout_date DATE DEFAULT NULL;'
    ELSE
        'SELECT 1;' -- Do nothing
END AS sql_command
FROM pragma_table_info('students') 
WHERE name = 'expected_checkout_date'
INTO @sql_command;

PRAGMA @sql_command;

-- Step 2: Create new student_details table (if it doesn't exist)
CREATE TABLE IF NOT EXISTS student_details (
    student_id INTEGER PRIMARY KEY,
    home_address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    parent_name TEXT,
    parent_contact TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    additional_notes TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Step 3: Ensure unique constraint on student_id_number
CREATE UNIQUE INDEX IF NOT EXISTS idx_students_student_id_number 
ON students(student_id_number)
WHERE student_id_number IS NOT NULL;
