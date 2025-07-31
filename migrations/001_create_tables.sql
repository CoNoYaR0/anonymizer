-- This script sets up the initial database schema for the CV Anonymizer project.
-- It includes tables for candidates, their education, skills, experiences, languages, and sectors.

-- Table to store the main candidate information (anonymized)
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the candidate
    initials VARCHAR(10) NOT NULL, -- Anonymized initials (e.g., "JTA")
    job_title VARCHAR(255), -- Candidate's current or most recent job title
    experience_years INTEGER, -- Total years of professional experience
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Timestamp of when the record was created
);

COMMENT ON TABLE candidates IS 'Stores anonymized information about each candidate.';
COMMENT ON COLUMN candidates.initials IS 'Anonymized initials of the candidate, e.g., J.D.';
COMMENT ON COLUMN candidates.job_title IS 'Current or most recent job title of the candidate.';
COMMENT ON COLUMN candidates.experience_years IS 'Total years of professional experience.';


-- Table to store the candidate''s educational background
CREATE TABLE educations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the education entry
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE, -- Foreign key to the candidates table
    year VARCHAR(4), -- Year of graduation or completion
    title VARCHAR(255), -- Name of the degree or diploma
    institution VARCHAR(255) -- Name of the school or institution
);

COMMENT ON TABLE educations IS 'Stores the educational background for each candidate.';
COMMENT ON COLUMN educations.candidate_id IS 'Links to the candidate this education belongs to.';


-- Table to store technical and functional skills, grouped by category
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the skill entry
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE, -- Foreign key to the candidates table
    category VARCHAR(100), -- Category of the skills (e.g., "Programming Languages", "Databases")
    skills_list TEXT[] -- Array of skills within this category
);

COMMENT ON TABLE skills IS 'Stores categorized skills for each candidate.';
COMMENT ON COLUMN skills.category IS 'The category of the skills, e.g., "Outils de tests".';
COMMENT ON COLUMN skills.skills_list IS 'An array of individual skills, e.g., {"Java", "Python"}.';


-- Table to store professional experiences
CREATE TABLE experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the experience entry
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE, -- Foreign key to the candidates table
    job_title VARCHAR(255), -- Title of the position
    company_name VARCHAR(255), -- Name of the company
    start_date VARCHAR(20), -- Start date of the employment
    end_date VARCHAR(20), -- End date of the employment
    job_context TEXT, -- Context or description of the role
    missions TEXT[], -- Array of missions or responsibilities
    technologies TEXT[] -- Array of technologies used in this role
);

COMMENT ON TABLE experiences IS 'Stores detailed professional experiences for each candidate.';
COMMENT ON COLUMN experiences.missions IS 'List of key missions and tasks performed.';
COMMENT ON COLUMN experiences.technologies IS 'List of technologies and tools used.';


-- Table to store language proficiency
CREATE TABLE languages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the language entry
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE, -- Foreign key to the candidates table
    language VARCHAR(50), -- The language spoken
    level VARCHAR(50) -- The proficiency level (e.g., "Fluent", "Native")
);

COMMENT ON TABLE languages IS 'Stores language skills and proficiency levels for each candidate.';


-- Table to store sectors of intervention
CREATE TABLE sectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for the sector entry
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE, -- Foreign key to the candidates table
    sector_name VARCHAR(255) -- The name of the industry or sector
);

COMMENT ON TABLE sectors IS 'Stores the sectors or industries the candidate has worked in.';


-- Table to log each extraction event and its raw JSON output
CREATE TABLE extractions (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY, -- Unique, auto-incrementing identifier for the extraction log
    filename TEXT, -- The original filename of the uploaded CV
    storage_path TEXT, -- The path to the original CV in Supabase Storage
    data JSONB, -- The raw JSON data that was extracted from the CV
    created_at TIMESTAMPTZ DEFAULT NOW() -- Timestamp of when the extraction was performed
);

COMMENT ON TABLE extractions IS 'Stores the raw JSON output from the OCR and NER extraction process for each CV.';
