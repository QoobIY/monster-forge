"""Monster Forge: modular humanoid asset production tools."""


def create_app(*args, **kwargs):
    """Load the web adapter only when an application is actually requested."""
    from .web import create_app as factory

    return factory(*args, **kwargs)

__all__ = ["create_app"]
