import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# --- Supabase Client Initialization ---
supabase_url: Optional[str] = os.getenv("SUPABASE_URL")
supabase_key: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
supabase_client: Optional[Client] = None

def initialize_supabase_client():
    """
    Initializes the Supabase client for storage operations.
    """
    global supabase_client
    if supabase_client:
        return

    if not all([supabase_url, supabase_key]):
        print("Error: Supabase URL or Key is not set in environment variables.", file=sys.stderr)
        sys.exit(1)

    try:
        print("Initializing Supabase client...")
        supabase_client = create_client(supabase_url, supabase_key)
        print("Supabase client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}", file=sys.stderr)
        sys.exit(1)

def get_supabase_client() -> Client:
    """
    Returns the initialized Supabase client.
    """
    if not supabase_client:
        raise Exception("Supabase client has not been initialized.")
    return supabase_client

# --- Storage Functions ---

def upload_file_to_storage(bucket_name: str, file_path: str, file_content: bytes) -> str:
    """
    Uploads a file to a specified Supabase storage bucket.

    Args:
        bucket_name: The name of the bucket to upload to (e.g., "cvs").
        file_path: The desired path and filename in the bucket for the uploaded file.
        file_content: The binary content of the file to upload.

    Returns:
        The public URL of the uploaded file.
    """
    # TODO: Implement the file upload logic.
    # 1. Get the Supabase client.
    # 2. Use `client.storage.from_(bucket_name).upload(...)`
    # 3. Use `client.storage.from_(bucket_name).get_public_url(...)`
    # 4. Return the public URL.

    print(f"TODO: Uploading {file_path} to bucket {bucket_name}.")

    # Placeholder return
    client = get_supabase_client()
    # In a real implementation, you would get this from the upload response.
    public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{file_path}"
    return public_url


def download_file_from_storage(bucket_name: str, file_path: str) -> bytes:
    """
    Downloads a file from a specified Supabase storage bucket.

    Args:
        bucket_name: The name of the bucket to download from.
        file_path: The path of the file in the bucket.

    Returns:
        The binary content of the downloaded file.
    """
    # TODO: Implement the file download logic.
    # 1. Get the Supabase client.
    # 2. Use `client.storage.from_(bucket_name).download(...)`
    # 3. Return the file content.

    print(f"TODO: Downloading {file_path} from bucket {bucket_name}.")

    # Placeholder return
    return b"placeholder file content"


# Initialize the client when the module is loaded
initialize_supabase_client()
