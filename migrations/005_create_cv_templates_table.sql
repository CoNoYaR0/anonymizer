-- Migration 005: Create CV Templates Table
-- This table will store the HTML/Jinja2 templates created by users.

CREATE TABLE public.cv_templates (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE, -- Foreign key to Supabase auth users
    template_name character varying(255) NOT NULL,
    html_content text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Add a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_cv_templates_update
BEFORE UPDATE ON public.cv_templates
FOR EACH ROW
EXECUTE PROCEDURE public.handle_updated_at();

-- Add policies for row-level security (example)
ALTER TABLE public.cv_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow users to see their own templates"
ON public.cv_templates
FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Allow users to insert their own templates"
ON public.cv_templates
FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Allow users to update their own templates"
ON public.cv_templates
FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Allow users to delete their own templates"
ON public.cv_templates
FOR DELETE USING (auth.uid() = user_id);

COMMENT ON TABLE public.cv_templates IS 'Stores user-created HTML/Jinja2 templates for CV generation.';
