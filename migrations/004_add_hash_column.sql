-- Add a new column to store the SHA256 hash of the uploaded file
ALTER TABLE public.extractions
ADD COLUMN file_hash VARCHAR(64);

-- Add a unique constraint to the new column to prevent duplicate file entries.
-- An index is automatically created on the column.
ALTER TABLE public.extractions
ADD CONSTRAINT unique_file_hash UNIQUE (file_hash);
