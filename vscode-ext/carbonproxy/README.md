# CarbonProxy AI

CarbonProxy AI is a VS Code extension that adds a Copilot Chat participant `@carbonproxy` and command-based prompt optimization with CO₂/token tracking.

## Features

- `@carbonproxy` chat participant for optimized prompt handling
- Prompt compression preview with `/optimize`
- Session stats with `/stats` and reset with `/reset`
- Semantic cache integration with cache-hit metrics
- Command palette + editor context optimization command
- Status bar CO₂ savings indicator

## Commands

- `CarbonProxy: Optimize Selection`
- `CarbonProxy: Open Web Dashboard`
- `CarbonProxy: Reset Session Metrics`

Keyboard shortcut:

- macOS: `Cmd+Shift+E`
- Windows/Linux: `Ctrl+Shift+E`

## Configuration

- `carbonproxy.backendUrl` (default: `http://localhost:8080`)

## Backend

The extension expects a backend exposing endpoints including:

- `POST /api/optimize`
- `POST /api/cache/check`
- `POST /api/cache/store`
- `GET /api/metrics`
- `POST /api/demo/reset`
- `GET /api/health`
