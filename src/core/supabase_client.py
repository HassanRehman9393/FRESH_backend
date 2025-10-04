from supabase import create_client, Client
from src.core.config import settings

# Initialize Supabase clients
# Anon client for public operations
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

# Service role client for admin operations
admin_supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
