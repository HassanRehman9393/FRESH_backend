"""
TC-BE-56 … TC-BE-62  — Configuration & CORS settings
"""
import pytest


class TestSettings:
    def test_allowed_origins_is_list(self):
        """TC-BE-56: allowed_origins property returns a list."""
        from src.core.config import settings
        origins = settings.allowed_origins
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_allowed_origins_contains_localhost(self):
        """TC-BE-57: localhost:3000 always in allowed origins."""
        from src.core.config import settings
        assert "http://localhost:3000" in settings.allowed_origins

    def test_allowed_file_types_is_list(self):
        """TC-BE-58: allowed_file_types returns a list of MIME strings."""
        from src.core.config import settings
        types = settings.allowed_file_types
        assert isinstance(types, list)
        for t in types:
            assert "/" in t  # valid MIME format

    def test_algorithm_is_hs256(self):
        """TC-BE-59: JWT algorithm defaults to HS256."""
        from src.core.config import settings
        assert settings.algorithm == "HS256"

    def test_token_expire_minutes_positive(self):
        """TC-BE-60: Token expiry is a positive integer."""
        from src.core.config import settings
        assert settings.access_token_expire_minutes > 0

    def test_max_file_size_is_positive(self):
        """TC-BE-61: Max file size is positive."""
        from src.core.config import settings
        assert settings.max_file_size > 0

    def test_wildcard_origin_expands_to_list(self):
        """TC-BE-62: When ALLOWED_ORIGINS='*', property returns a list (not ['*'])."""
        from src.core.config import Settings
        s = Settings(ALLOWED_ORIGINS="*")
        origins = s.allowed_origins
        assert "*" not in origins
        assert isinstance(origins, list)
        assert len(origins) > 0
