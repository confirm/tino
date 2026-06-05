.. _ADR-05:

ADR-05: FastAPI single-process architecture
===========================================

Context
-------

TINO needed a Python web framework to serve the REST API and WebSocket endpoints.
The main candidates were:

- `Django <https://www.djangoproject.com/>`_
- `Flask <https://flask.palletsprojects.com/>`_
- `FastAPI <https://fastapi.tiangolo.com/>`_

Separately, modern web applications are often split into multiple services: a frontend server, an API server, a WebSocket server, and so on.
The question was whether TINO should follow that pattern.

Decision
--------

TINO uses FastAPI with `Uvicorn <https://www.uvicorn.org/>`_ as the ASGI server, running as a single process.
The same application serves the REST API, the WebSocket collaboration endpoints, and the static frontend files. 
There is no separate build pipeline, reverse proxy (in development), or inter-service communication.

Consequences
------------

Positive
~~~~~~~~

- | **Simple deployment**
  | A single container with a single volume is all that is needed — no service mesh, no orchestration, no inter-service networking to configure.
- | **Simple development**
  | One process to start, one log stream to watch, one thing to restart.
- | **Automatic API docs**
  | OpenAPI (Swagger UI, ReDoc) is generated automatically from type hints and docstrings, with zero additional effort.
- | **Dependency injection**
  | FastAPI's ``Depends()`` system makes service wiring, authentication, and per-request state clean and testable.
- | **Type-safe request/response**
  | Pydantic models validate all incoming and outgoing data at the boundary, catching errors early.
- | **Async-native**
  | FastAPI is built on ASGI, making it a natural fit for WebSocket support and concurrent I/O — both required for real-time collaboration.
- | **No distributed state**
  | The Yjs collaboration manager, the file service, and the API all share the same process memory — no message broker or shared cache required.

Negative
~~~~~~~~

- | **Younger ecosystem**
  | FastAPI is newer than Flask or Django; some integrations and patterns are less established.
- | **Pydantic coupling**
  | Heavy reliance on Pydantic means a major Pydantic version bump can require widespread model updates.
- | **Vertical scaling only**
  | The collaboration manager holds per-file state in process memory, making horizontal scaling across multiple instances non-trivial.
- | **Single point of failure**
  | A crash or restart affects all functionality simultaneously — API, collaboration, and the frontend become unavailable together.
