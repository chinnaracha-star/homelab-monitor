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
- Python Ubuntu agent with `run` and `collect` commands.
- CPU, memory, filesystem, load-average, uptime, OS, hostname, and optional
  temperature collection.
- Server-controlled reporting intervals and threshold configuration sync.
- Bounded exponential retry and persistent SQLite offline report queue.
- Graceful SIGINT/SIGTERM shutdown and hardened systemd service example.
- Agent collector, transport, authentication, buffering, restart, and retry tests.
- Read-only Dashboard API for overview counts, agent lists, agent details, and
  latest metric reports.
- Persisted alert-state engine for CPU, memory, disk, temperature, and offline
  agent detection.
- Reusable Telegram Bot API notifier for new and reopened alert transitions,
  with environment configuration and duplicate-notification suppression.
