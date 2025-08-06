-- Migration to create a cache table for DOCX-to-HTML conversions.
-- This table will store the SHA-256 hash of a .docx file and the resulting
-- HTML content from the Convertio API, preventing redundant API calls.

CREATE TABLE html_conversion_cache (
    -- The SHA-256 hash of the .docx file content, serving as a unique key.
    file_hash TEXT PRIMARY KEY,

    -- The full HTML content returned by the conversion service.
    html_content TEXT NOT NULL,

    -- Timestamp of when the record was created.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE html_conversion_cache IS 'Caches the results of .docx to HTML conversions to avoid repeated API calls.';
COMMENT ON COLUMN html_conversion_cache.file_hash IS 'SHA-256 hash of the source .docx file.';
COMMENT ON COLUMN html_conversion_cache.html_content IS 'The converted HTML content.';
