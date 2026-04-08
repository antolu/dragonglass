from __future__ import annotations

import contextlib
import contextvars
import typing

_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "dragonglass_request_id", default="-"
)


def get_request_id() -> str:
    return _REQUEST_ID.get()


@contextlib.contextmanager
def bind_request_id(request_id: str) -> typing.Iterator[None]:
    token = _REQUEST_ID.set(request_id)
    try:
        yield
    finally:
        _REQUEST_ID.reset(token)
