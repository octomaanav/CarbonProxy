# CarbonProxy AI

CarbonProxy AI is a VS Code extension that adds a Copilot Chat participant `@carbonproxy` and command-based prompt optimization with CO₂/token tracking.

## Features

- `@carbonproxy` chat participant for optimized prompt handling
- Automatic prompt compression and memory persistence (each prompt/response saved per project session)
- Session stats with `/stats` and reset with `/reset`
- Semantic cache integration with cache-hit metrics
- Command palette + editor context optimization command
- Status bar CO₂ savings indicator

## Commands

- `CarbonProxy: Optimize Selection`
- `CarbonProxy: Optimize Prompt for Copilot`
- `CarbonProxy: Open Web Dashboard`
- `CarbonProxy: Reset Session Metrics`

### Available Commands

- `/stats` — show session statistics (tokens saved, CO₂ avoided, cache hit rate)
- `/reset` — reset session metrics to zero

Use: `@carbonproxy /stats` or `@carbonproxy /reset`

## Configuration

- `carbonproxy.backendUrl` (default: `http://localhost:8080`)
- `carbonproxy.memorySessionId` (optional; if empty, extension auto-generates a project-scoped session id)

## Backend

The extension expects a backend exposing endpoints including:

- `POST /api/optimize`
- `POST /api/cache/check`
- `POST /api/cache/store`
- `GET /api/metrics`
- `POST /api/demo/reset`
- `GET /api/health`

## Usage

Simply use `@carbonproxy <your prompt>` to:
- Automatically optimize (compress) your prompt
- Get an AI response
- Persist the interaction to your project's memory database

Example: `@carbonproxy explain how to implement binary search in Python`

All prompts are automatically optimized and saved per project session for context reuse.
