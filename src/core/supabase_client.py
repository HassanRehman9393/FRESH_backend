from supabase import create_client, Client
from src.core.config import settings

# Initialize Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
