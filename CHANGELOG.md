# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project will use [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Initial FastAPI service and health endpoint.
- SQLite persistence managed by Alembic.
- One-time agent credential issuance with hashed token storage.
- Authenticated agent check-in, configuration sync, and idempotent metrics upload.
- Structured request logging, API tests, and GitHub Actions quality gates.
