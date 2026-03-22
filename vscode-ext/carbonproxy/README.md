# CarbonProxy AI

CarbonProxy AI is a VS Code extension that adds a Copilot Chat participant `@carbonproxy` and command-based prompt optimization with CO₂/token tracking.

## Features

- `@carbonproxy` chat participant for optimized prompt handling
- Prompt compression preview with `/optimize`
- Optimize and forward to Copilot Chat with `/send`
- Session stats with `/stats` and reset with `/reset`
- Semantic cache integration with cache-hit metrics
- Command palette + editor context optimization command
- Status bar CO₂ savings indicator

## Commands

- `CarbonProxy: Optimize Selection`
- `CarbonProxy: Optimize Prompt for Copilot`
- `CarbonProxy: Open Web Dashboard`
- `CarbonProxy: Reset Session Metrics`

### Optimize before sending to Copilot

Use `CarbonProxy: Optimize Prompt for Copilot` from the Command Palette.

It will:

1. Ask for your prompt (prefills editor selection if any)
2. Run prompt optimization via the CarbonProxy backend
3. Offer actions:
	- Send to Copilot Chat
	- Copy optimized prompt
	- Replace selected text
	- Preview optimization

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

## Copilot Chat flow

- `@carbonproxy /optimize <your prompt>` → shows compression preview
- `@carbonproxy /send <your prompt>` → optimizes prompt and opens Copilot Chat with the optimized text
