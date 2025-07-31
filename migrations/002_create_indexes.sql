-- This script creates indexes on foreign keys to improve the performance of JOIN operations.
-- An index on each `candidate_id` column is crucial as we will frequently query
-- for all data related to a specific candidate.

-- Index for the educations table
CREATE INDEX idx_educations_candidate_id ON educations(candidate_id);

-- Index for the skills table
CREATE INDEX idx_skills_candidate_id ON skills(candidate_id);

-- Index for the experiences table
CREATE INDEX idx_experiences_candidate_id ON experiences(candidate_id);

-- Index for the languages table
CREATE INDEX idx_languages_candidate_id ON languages(candidate_id);

-- Index for the sectors table
CREATE INDEX idx_sectors_candidate_id ON sectors(candidate_id);
