"""
Smoke test for the FastAPI entry point.

Juliana found that a missing import in `apps/api/__main__.py` broke
the container startup while all unit tests remained green.

This test simply imports the module to ensure there are no NameError
or ImportError at module level.
"""

def test_main_module_imports_without_errors():
    # If there is a NameError, this will fail at import time
    import apps.api.__main__
    assert True
