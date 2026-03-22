import * as vscode from 'vscode';
import { createHash } from 'crypto';
import { chatWithMemory, getMetrics, resetBackendSession } from './api';
import { buildMetricsTable, estimateTokens, co2ToEquivalent } from './metrics';
import { recordMetric, resetSession, session } from './session';
import { refreshStatusBar } from './statusBar';

export function registerChatParticipant(
  context: vscode.ExtensionContext
): void {
  const participant = vscode.chat.createChatParticipant(
    'carbonproxy.chat',
    handleRequest
  );

  participant.iconPath = vscode.Uri.joinPath(
    context.extensionUri,
    'media',
    'ecostack-icon.png'
  );

  context.subscriptions.push(participant);
}

async function handleRequest(
  request: vscode.ChatRequest,
  _context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<void> {
  const { command, prompt } = request;

  if (command === 'stats') {
    return handleStatsCommand(stream);
  }

  if (command === 'reset') {
    return handleResetCommand(stream);
  }

  return handleFullRequest(prompt, stream, token);
}

async function handleStatsCommand(
  stream: vscode.ChatResponseStream
): Promise<void> {
  let backendData;
  try {
    backendData = await getMetrics();
  } catch {
    backendData = null;
  }

  const co2 = backendData?.co2_saved_g ?? session.co2SavedG;
  const tokensSaved = backendData?.tokens_saved ?? session.tokensSaved;
  const requests = backendData?.requests ?? session.requests;
  const cacheHits = backendData?.cache_hits ?? session.cacheHits;
  const hitRate = requests > 0 ? Math.round((cacheHits / requests) * 100) : 0;

  const perRequest = requests > 0 ? co2 / requests : 0;
  const annualTeam = Math.round(perRequest * 10 * 50 * 250);

  stream.markdown(`## CarbonProxy Session Stats

| Metric | Value |
|---|---|
| Total requests | \`${requests}\` |
| Tokens saved | \`${tokensSaved.toLocaleString()}\` |
| CO₂ avoided | \`${co2.toFixed(5)}g\` |
| Cache hit rate | \`${hitRate}%\` (\`${cacheHits}\` hits) |
| Equivalent to | ${co2ToEquivalent(co2)} avoided |

**Team projection:** If 10 developers used CarbonProxy for 50 AI queries/day, you'd avoid ~\`${annualTeam}g\` CO₂/year.

*Use \`@carbonproxy /reset\` to clear these stats.*
`);
}

async function handleResetCommand(
  stream: vscode.ChatResponseStream
): Promise<void> {
  try {
    await resetBackendSession();
  } catch {
    // Non-fatal
  }
  resetSession();
  void refreshStatusBar();
  stream.markdown('Session metrics have been reset to zero. Ready for a fresh demo.');
}

async function handleFullRequest(
  userPrompt: string,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<void> {
  if (!userPrompt.trim()) {
    stream.markdown('Please enter a prompt. Example: `@carbonproxy explain async/await in JavaScript`');
    return;
  }

  if (token.isCancellationRequested) return;
  stream.progress('Running full memory pipeline...');

  try {
    const sessionId = getProjectSessionId();
    const result = await chatWithMemory(sessionId, userPrompt);

    if (token.isCancellationRequested) return;

    const responseText = result.response ?? '';
    stream.markdown(responseText);

    if (result.memory) {
      stream.markdown(
        `Memory: used \`${result.memory.chunks_used}\` / \`${result.memory.chunks_available}\` chunks in session \`${sessionId}\`.`
      );
    }

    stream.markdown(
      buildMetricsTable({
        cacheHit: result.cache_hit ?? false,
        tokensBefore: result.tokens_before,
        tokensAfter: result.tokens_after,
        co2G: result.co2_g ?? 0,
        model: result.model ?? 'unknown',
        savingsPct: result.savings_pct ?? 0,
      })
    );

    recordMetric({
      model: result.model ?? 'unknown',
      co2G: result.co2_g ?? 0,
      tokensSaved: result.tokens_before - result.tokens_after,
      cached: result.cache_hit ?? false,
    });
    void refreshStatusBar();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    stream.markdown(`**CarbonProxy error:** ${msg}

Make sure the backend is running:
\`\`\`bash
cd api && uvicorn main:app --reload --port 8080
\`\`\`
`);
  }
}

function getProjectSessionId(): string {
  const configured = vscode.workspace
    .getConfiguration('carbonproxy')
    .get<string>('memorySessionId', '')
    .trim();

  if (configured) {
    return configured;
  }

  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    return 'default';
  }

  const fsPath = folder.uri.fsPath;
  const hash = createHash('sha1').update(fsPath).digest('hex').slice(0, 10);
  return `project:${folder.name}:${hash}`;
}
