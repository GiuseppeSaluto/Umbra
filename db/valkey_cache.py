"""Valkey cache layer (open source Redis fork). Introduced in Phase 3."""


def get_client(url: str):
    """Return the Valkey client configured for the requested URL."""
    raise NotImplementedError
