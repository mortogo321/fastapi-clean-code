# FastAPI Clean Code

A Python port of [max38/golang-clean-code-architecture](https://github.com/max38/golang-clean-code-architecture).
It keeps the same Clean Architecture (domain → use cases → interface → infrastructure), user registration
with JWT authentication and generic data-browsing endpoints, rewritten with **FastAPI, SQLAlchemy 2 (async)
and PostgreSQL**. A **Next.js** frontend consumes the API.

| Part | Stack |
| --- | --- |
| `api/` | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic, PyJWT, bcrypt, uv |
| `web/` | Next.js 16 (App Router, server actions), React 19, TypeScript, Tailwind CSS 4, Bun, Biome |
| `compose.yml` | PostgreSQL 18, API (applies migrations on start), web |

## Quick start

Requires Docker.

```bash
ENV=development docker compose up --build
```

| URL | |
| --- | --- |
| http://localhost:3000 | Web app: register, sign in, browse data |
| http://localhost:8000/api/v1/ | API |
| http://localhost:8000/swagger | Swagger UI (enabled in development) |

`ENV=development` uses the development defaults in `api/.env.development`, including a throwaway JWT secret
and database password. Without it, Compose uses `.env.production`, which has no default secrets and
disables Swagger:

```bash
export APP_SECRET_KEY="$(openssl rand -hex 32)" POSTGRES_PASSWORD="$(openssl rand -hex 16)"
docker compose up --build -d
```

Host ports can be changed with `WEB_PORT`, `API_PORT` and `DB_PORT` (all ports bind to `127.0.0.1`).

## Project structure

```
.
├── api/            FastAPI backend (Clean Architecture)
├── web/            Next.js frontend (backend-for-frontend)
└── compose.yml     db → api (start.sh: alembic upgrade head, then uvicorn) → web
```

### Backend layers

```
api/src/app/
├── domain/                  Business core: plain Python + Pydantic, no web or database framework
│   ├── entities/            Request/response contracts (UserRegisterRequest, UserLoginResponse, ...)
│   ├── models/              Stored data shapes (UserModel, UserTokenModel, UserPermissionModel)
│   ├── repositories/        Ports: typing.Protocol interfaces the use cases depend on
│   └── errors.py            Business errors (EmailAlreadyRegisteredError, InvalidTokenError, ...)
├── usecases/                Application logic: registration, login, token rotation, data browsing
├── interface/               Adapters
│   ├── handlers/fastapi/    HTTP routes, error contract, Bearer-token dependency
│   └── repositories/postgres/  SQLAlchemy implementations of the repository ports
├── infrastructure/          Frameworks and drivers
│   ├── database/postgres/   Engine lifecycle + Alembic migrations
│   └── fastapi/             App factory, middleware, composition root (main.py)
├── config/                  Settings from environment; the list of models published under /data
└── shared/                  JWT, bcrypt, Avro-style schema generator, name converters
```

Dependencies only point inwards. `tests/unit/test_architecture.py` enforces this: it fails if `domain/`
imports a framework, or if an inner layer imports an outer one.

```
infrastructure ──▶ interface ──▶ usecases ──▶ domain
```

- **Ports and adapters.** `domain/repositories` declares what the use cases need (`IUserRepository`,
  `ICRUDRepository`) as `Protocol`s. `interface/repositories/postgres` implements them. The use cases never
  import SQLAlchemy and are unit-tested with in-memory fakes.
- **Composition root.** `infrastructure/fastapi/main.py` is the only module that knows every concrete class.
  On startup it opens one connection pool, builds the repositories and use cases, and hands them to the
  HTTP layer.
- **Errors cross layers as domain exceptions.** A use case raises `InvalidCredentialsError`; the route
  maps it to `401` with error code `users-002`. Use cases know nothing about HTTP.

Example: `GET /api/v1/users/profile`:

1. `interface/handlers/fastapi/dependencies.py` reads the Bearer token and calls
   `UserUsecase.user_authentication`.
2. The use case verifies the JWT (`shared/authentication/jwt.py`), then asks `IUserRepository` whether that
   session is still live (not logged out or rotated).
3. `PostgresUserRepository` runs the query. The route returns the `UserEntity`, which Pydantic serialises
   to JSON.

### Go → Python map

| Go (`src/...`) | Python (`api/src/app/...`) |
| --- | --- |
| `config/config.go`, `config/crudModels.go` | `config/settings.py`, `config/crud_models.py` |
| `domain/entities`, `domain/models`, `domain/repositories` | same names; repositories are `Protocol`s, plus `domain/errors.py` |
| `usecases/user`, `usecases/crud` | `usecases/user.py`, `usecases/crud.py` |
| `interface/handlers/gofiber` | `interface/handlers/fastapi` |
| `interface/repositories/postgres` | `interface/repositories/postgres` |
| `infrastructure/gofiber` (main, server, middlewares) | `infrastructure/fastapi` (main, server, middlewares) |
| `infrastructure/database/postgres` (GORM `AutoMigrate`) | `infrastructure/database/postgres` (Alembic revisions) |
| `shared/authentication`, `shared/crud`, `shared/converter.go` | `shared/authentication`, `shared/crud`, `shared/converter.py` |

## API

Base path `/api/v1`; `GET /` redirects there.

| Method | Path | Auth | |
| --- | --- | --- | --- |
| GET | `/` | | Server name and version |
| POST | `/users/register` | | Create an account; returns `201` with the user |
| POST | `/users/login` | | Returns the user and `{access, refresh}` tokens |
| POST | `/users/refresh-token` | | Rotates the token pair (body: `refresh_token`) |
| POST | `/users/logout` | | Revokes the session; returns `204` (body: `refresh_token`) |
| GET | `/users/profile` | Bearer | The current user |
| GET | `/data/` | Bearer | Slugs of the published data models |
| GET | `/data/{model}/describe` | Bearer | Avro-style schema of a model |
| GET | `/data/{model}/?_page=1&_pageSize=10` | Bearer | One page of records (`_pageSize` ≤ 100) |
| GET | `/data/{model}/{id}` | Bearer | One record |

Errors keep the Go response shape, `{"trace_id": "<code>", "message": "..."}`. Validation errors add
`details: [{field, message}]`.

| Code | Status | Meaning |
| --- | --- | --- |
| `users-001` | 409 | Email already registered |
| `users-002` | 401 | Invalid email or password (same response for both) |
| `users-003` | 401 | Refresh token invalid, expired or already used |
| `users-004` | 401 | Logout with an invalid token |
| `middleware-001` | 404 / 405 | Unknown route or method |
| `middleware-002` | 401 | Missing, invalid or revoked access token |
| `middleware-003` | 422 | Validation error |
| `middleware-000` | 500 | Unexpected error (logged; never echoed to the client) |
| `data-001` | 404 | Unknown data model |
| `data-002` | 404 | Record not found, or owned by another user |

### Authentication

- HS256 tokens: access (15 min) and refresh (7 days). Parsing requires the issuer, audience and token
  `type`, so a refresh token is never accepted as an access token.
- Every login creates a server-side session. It stores only SHA-256 hashes of the two tokens, so a database
  leak does not leak usable tokens. Logout deletes the session, and the access token stops working at once.
- Refresh rotates the pair with a compare-and-swap update: replaying an old refresh token fails, and a
  session's lifetime is never extended.
- Passwords use bcrypt, run off the event loop. A login with an unknown email still does the bcrypt work,
  so response times do not reveal which emails exist.
- In `/data`, users see only their own rows. A user with the `admin` permission sees every row:

  ```bash
  docker compose exec db psql -U postgres -d fastapi_clean_code \
    -c "INSERT INTO user_permissions (user_id, permission) VALUES (1, 'admin')"
  ```

### Publishing another model under `/data`

1. Define it in `domain/models/`: subclass `CRUDDataModel` and set `table_name` and `owner_field`.
2. Add the table to `interface/repositories/postgres/orm.py`, then generate a migration:
   `uv run alembic revision --autogenerate -m "add ..."`.
3. Add the model to `CRUD_MODELS` in `config/crud_models.py`.

## Web frontend

`web/` is a Next.js App Router app that works as a backend-for-frontend:

- The browser only talks to Next.js. Server actions (login, register, logout) and server components call
  the API at `API_URL`. Tokens live in httpOnly, `SameSite=Lax` cookies and never reach client-side
  JavaScript. Behind a reverse proxy that terminates TLS, forward `X-Forwarded-Proto: https` so the
  cookies also get the `Secure` flag.
- `src/proxy.ts` uses the refresh cookie to renew an expired access token before the page renders, so a
  session outlives the 15-minute access token. A revoked session is sent back to `/login`.
- Pages:
  - `/login`, `/register`;
  - `/dashboard` (profile and API info);
  - `/data` (the models);
  - `/data/[slug]` (a paginated table whose columns come from the model schema);
  - `/data/[slug]/[id]`.

Known limitation: a refresh token works only once. If two requests arrive together with only the refresh
cookie (say, two tabs reopened after the access token expired), one refresh succeeds and the other request
is sent to `/login`. If that response reaches the browser last, it also clears the cookies, and the user
has to sign in again. Link prefetches skip the proxy, so they never start a refresh.

## Local development

```bash
# PostgreSQL only, published on localhost:5432
ENV=development docker compose up -d db

# API: http://localhost:8000
cd api
uv sync
cp .env.development .env
uv run alembic upgrade head
uv run uvicorn app.infrastructure.fastapi.main:app --reload

# Web: http://localhost:3000 (reads API_URL from .env.development)
cd web
bun install
bun run dev
```

### Hot reload in Docker

```bash
ENV=development docker compose -f compose.yml -f compose.dev.yml up --build --watch
```

`compose.dev.yml` runs the same stack (same ports and database) with the Dockerfiles' `dev` targets, tagged
`:dev` so the production images stay intact. Compose Watch copies every change under `api/src` and
`web/src` into the containers, where `uvicorn --reload` and `next dev` pick it up within a few seconds.
Changing `pyproject.toml`, `uv.lock`, `package.json` or `bun.lock` rebuilds the image. Running
`ENV=development docker compose up --build -d` switches the stack back to the production builds.

### Checks

```bash
cd api
uv run ruff check . && uv run ruff format --check . && uv run mypy   # mypy --strict over src and tests
uv run pytest                                                        # unit + HTTP tests, in-memory fakes

# Integration tests against real PostgreSQL. They recreate the schema, so they only run on a database named app_test
docker compose exec db createdb -U postgres app_test
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_test uv run pytest

cd ../web
bun run lint && bun run typecheck && bun run build

# End-to-end: Playwright drives Chromium through the running stack (browser → Next.js → API → PostgreSQL)
ENV=development docker compose up --build -d   # from the repository root
bunx playwright install chromium               # once
bun run test:e2e                               # E2E_BASE_URL / E2E_API_URL override localhost:3000 / :8000
```

The e2e suite (`web/e2e`) covers registration, sign-in and sign-out, the data pages (paging, and a 404 for
another user's record), token renewal and revoked sessions, httpOnly cookies, security headers and
off-site redirect targets. Run it against the production builds: under the hot-reload overlay, `next dev`
compiles each page on its first request and the suite's 5-second assertions time out.

## Configuration

`.env.development` and `.env.production` are committed, and every value is written as `${VAR:-default}`.
That lets real environment variables override any entry, both in the apps and in Compose. Each app reads a
git-ignored `.env`: copy one of the two files for local work. The Docker images copy the file chosen by the
`ENV` build argument.

| Variable | Default (development) | |
| --- | --- | --- |
| `APP_NAME`, `APP_VERSION` | `FastAPI Clean Code`, `0.1.0` | Shown by `GET /api/v1/`; the name is also the JWT issuer |
| `APP_SECRET_KEY` | dev-only value | JWT signing key, ≥ 32 characters. Required in production |
| `APP_JWT_ACCESS_EXPIRES`, `APP_JWT_REFRESH_EXPIRES` | `900`, `604800` | Token lifetimes in seconds |
| `APP_BCRYPT_ROUNDS` | `12` | bcrypt cost |
| `APP_CORS_ORIGINS` | `[]` | JSON list. The web app calls the API server-side, so it needs none |
| `APP_DOCS_ENABLED` | `true` (`false` in production) | Swagger UI at `/swagger` |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `localhost`, `5432`, `postgres`, `postgres`, `fastapi_clean_code` | Also used by the `db` container to initialise the database |
| `API_URL` (web) | `http://localhost:8000` (`http://api:8000` in production) | Read at runtime by the Next.js server |

## Differences from the Go version

The route paths, the `{trace_id, message}` error shape and the `users-00x` codes follow the Go project.
The differences below are deliberate, mostly where the Go template has a bug, a typo or a security gap:

| Area | Go template | This port |
| --- | --- | --- |
| Routes | `/` is a 404; `/api/v1` and `/api/v1/` both match | `GET /` redirects to `/api/v1/`; a path without its trailing slash redirects (`307`) to the slash form |
| Profile route | `POST /users/profile` | `GET /users/profile` |
| Model list | No `GET /data/` route | `GET /data/` returns the published model slugs |
| Swagger | Always served at `/swagger/*` | `/swagger` and `/openapi.json`, only when `APP_DOCS_ENABLED` is true |
| Error codes | `middlware-001` to `-005` (sic); unknown routes answer `"rotuer not found"` | `middleware-` and `"router not found"`; new `middleware-000` (500), `data-001` and `data-002` |
| Error statuses | `400` for every user and `/data` error (`500` for a duplicate email), trace_id `"error"` on `/data`; a wrong method is a `404` | `401`, `404`, `405`, `409` and `422`, as listed under [API](#api) |
| Validation | Bad JSON or an invalid email is a `400` with the parser's message; unknown fields are ignored; no length rules | `422` `middleware-003` with per-field `details`; unknown fields are rejected; passwords need 8 characters (at most 72 bytes), names 1 to 100 |
| Logout | `200` with a `null` body | `204` |
| Account enumeration | Login returns "record not found" vs "password is invalid"; a duplicate registration returns 500 with the database error | One `401` for bad credentials; `409` for a taken email |
| Error messages | `err.Error()` from the database layer is sent to the client | Fixed messages; unexpected errors become a generic `500` |
| Refresh token lifetime | Computed from `GOAPP_JWT_ACCESS_EXPIRES`; `GOAPP_JWT_REFRESH_EXPIRES` is never read | Its own setting; an access token never outlives its refresh token |
| Token checks | Signature and expiry only (`iss`, `aud` and `sub` are not checked) | HS256 only, with issuer, audience, token type and all registered claims required |
| Token payload | The user id sits in a custom `claims` object | The user id is `sub`, plus a `type` claim and a unique `jti`; tokens from one project don't work in the other |
| JWT issuer | The `strings.Replace` result is not assigned, so spaces stay in `iss` | A slug of the app name |
| Sessions | Tokens are stored in clear text, one row per user | SHA-256 hashes, one row per login (several devices), atomic rotation |
| Password hashing | bcrypt cost fixed at `10` | `APP_BCRYPT_ROUNDS`, default `12` |
| `/data/user-tokens` | Returns every user's stored tokens to any signed-in user | Returns session metadata only, scoped to the caller unless the caller is an admin |
| `/data` bodies | Every response also carries `code` (always `0`) and `message` (always `""`) | Dropped |
| Pagination | `total_data` and `total_page` count only the current page; no `ORDER BY` | `COUNT(*)` and `ORDER BY id` |
| Page size | `_pageSize` is capped at 1000; invalid values silently fall back to the defaults | `_pageSize` 1 to 100 and `_page` 1 to 1,000,000; anything else is a `422` |
| Schema types | Integer fields are `"int"` in `/describe` (`"long"` only for `uint64`) | `"long"`, since Python integers are unbounded; floats are `"double"` |
| Database connections | Each `/data` request opens a new GORM pool | One pool per process |
| Schema changes | GORM `AutoMigrate`, run by hand as a separate command (`migration/main.go`) | Versioned Alembic migrations, applied by `api/start.sh` before the server starts |
| CORS | `AllowOrigins: *` | No cross-origin access unless `APP_CORS_ORIGINS` lists origins; `GET` and `POST` only |
| Request log | Fiber logger middleware (`time [ip] status - method path`) | Uvicorn's access log |
| Configuration | `GOAPP_*` variables, including `GOAPP_HOST`, `GOAPP_PORT` and `GOAPP_POSTGRES_DB_*` | `APP_*` and `POSTGRES_*` (see [Configuration](#configuration)); host and port are uvicorn flags in `api/start.sh` |
| MongoDB | An adapter exists, but no model uses it | Not ported; the per-model `datasource` switch is kept for adding one |
