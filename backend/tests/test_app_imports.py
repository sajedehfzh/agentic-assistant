"""Smoke test — import the FastAPI app.

This catches FastAPI route-registration errors that aren't caught by static
syntax checks (e.g. invalid `status_code` + `response_model` combinations,
duplicate paths, mis-typed dependencies). If this passes, uvicorn will at
least manage to start.
"""

from __future__ import annotations


def test_app_imports() -> None:
    from app.main import app

    routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
    assert "/health" in routes
    assert "/api/auth/login" in routes
    assert "/api/meetings" in routes
    assert "/api/actions/{action_id}/approve" in routes
    assert "/api/analysis/{meeting_id}/start" in routes
    assert "/api/companies" not in routes
    assert "/api/interviews" not in routes


def test_delete_routes_have_no_response_model() -> None:
    """Regression test for the FastAPI 0.115 strict 204 check.

    Each DELETE route must declare `response_model=None` (or omit a body)
    when the status code is 204, otherwise uvicorn fails to start with
    `AssertionError: Status code 204 must not have a response body`.
    """
    from app.main import app

    delete_204_paths: list[str] = []
    for route in app.routes:
        if (
            getattr(route, "methods", None)
            and "DELETE" in route.methods  # type: ignore[union-attr]
            and getattr(route, "status_code", None) == 204
        ):
            delete_204_paths.append(route.path)  # type: ignore[attr-defined]

    assert delete_204_paths, "No DELETE 204 routes found — did the API change?"
    assert "/api/meetings/{meeting_id}" in delete_204_paths
