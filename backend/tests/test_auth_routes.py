"""Regression tests for the `/api/auth/login` request schema.

The login route accepts a `LoginRequest` body — `{username, password}` at the
top level of the JSON. Earlier, a Pydantic-typed sub-dependency
(`Settings | None`) on `get_auth_provider` was making FastAPI promote
`settings` into a body field, which silently broke the contract by wrapping
the whole body under a `payload` key. Anyone working on auth dependencies
should keep these tests passing.
"""

from app.main import app


def _login_route_body_schema() -> dict:
    spec = app.openapi()
    body_ref = spec["paths"]["/api/auth/login"]["post"]["requestBody"]
    schema_ref = body_ref["content"]["application/json"]["schema"]["$ref"]
    schema_name = schema_ref.rsplit("/", 1)[-1]
    return spec["components"]["schemas"][schema_name]


def test_login_body_is_login_request_directly() -> None:
    """Body is `LoginRequest` itself, not a synthetic `Body_login_*` envelope."""
    spec = app.openapi()
    schema_ref = spec["paths"]["/api/auth/login"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]["$ref"]
    assert schema_ref.endswith("/LoginRequest"), (
        f"Login body schema was wrapped in an envelope ({schema_ref}). "
        "Some sub-dependency is leaking a Pydantic-typed parameter into the "
        "body — declare it as `Annotated[X, Depends(...)]` instead of using "
        "a default value or a non-FastAPI default."
    )


def test_login_body_only_has_username_and_password() -> None:
    body = _login_route_body_schema()
    props = set(body.get("properties", {}).keys())
    assert props == {"username", "password"}, (
        f"Login body schema must only contain {{username, password}}; got {props}. "
        "Check that no Settings/Repository/Service is sneaking into the body."
    )


def test_response_models_serialize_id_not_underscore_id() -> None:
    """API contract: clients see `id`, never the Mongo internal `_id`.

    FastAPI defaults to `by_alias=True` for response serialization, so any
    `Field(alias="_id")` on a response model would leak the Mongo field name
    onto the wire and break frontend keys/links.
    """
    spec = app.openapi()
    for name, schema in spec["components"]["schemas"].items():
        props = schema.get("properties", {}) or {}
        assert "_id" not in props, (
            f"Schema `{name}` exposes `_id` to clients. Drop the alias from "
            "MongoModel — the repository already maps _id -> id."
        )
