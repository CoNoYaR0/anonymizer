CREATE POLICY "Allow public uploads in cvs bucket"
ON storage.objects FOR INSERT TO public
WITH CHECK ( bucket_id = 'cvs' );

CREATE POLICY "Allow public read access on cvs bucket"
ON storage.objects FOR SELECT TO public
USING ( bucket_id = 'cvs' );
