"""Shoji helper functions."""

# These have been extracted from server/tests/controllers/base.py
# I imagine they should go into pycrunch.

def as_catalog(x, **kwargs) -> dict:
    """Format and return `x` as a shoji catalog"""
    return dict(element="shoji:catalog", index=x, **kwargs)


def as_entity(body, **kwargs) -> dict:
    """Return shoji Entity dict with *body* and other attributes passed as *kwargs*."""
    return dict(element="shoji:entity", body=body, **kwargs)


def as_order(x, **kwargs) -> dict:
    """Format and return `x` as a shoji order"""
    return dict(element="shoji:order", graph=x, **kwargs)


def as_value(x) -> dict:
    """Format and return `x` as a shoji view"""
    return {"element": "shoji:view", "value": x}
