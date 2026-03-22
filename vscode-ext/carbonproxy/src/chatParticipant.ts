import * as vscode from 'vscode';
import { createHash } from 'crypto';
import { optimizePrompt, chatWithMemory, getMetrics, resetBackendSession } from './api';
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

  if (command === 'optimize') {
    return handlePreviewOptimize(prompt, stream);
  }

  if (command === 'send') {
    return handleOptimizeAndSendToCopilot(prompt, stream);
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

async function handlePreviewOptimize(
  prompt: string,
  stream: vscode.ChatResponseStream
): Promise<void> {
  if (!prompt.trim()) {
    stream.markdown('Please provide a prompt to preview. Example: `@carbonproxy /optimize explain how TCP works`');
    return;
  }

  stream.progress('Compressing prompt...');

  try {
    const result = await optimizePrompt(prompt);
    stream.markdown(`**Prompt compression preview**

**Before** (${result.tokens_before} tokens):
\`\`\`
${result.original_prompt}
\`\`\`

**After** (${result.tokens_after} tokens — ${result.savings_pct}% smaller):
\`\`\`
${result.optimized_prompt}
\`\`\`

Model that would be selected: \`${result.model}\`
Estimated CO₂ if sent: \`${(result.co2_g ?? 0).toFixed(5)}g\`

*Run without \`/optimize\` to get the actual response.*
`);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    stream.markdown(`**Error:** ${msg}. Is the CarbonProxy backend running?`);
  }
}

async function handleOptimizeAndSendToCopilot(
  prompt: string,
  stream: vscode.ChatResponseStream
): Promise<void> {
  if (!prompt.trim()) {
    stream.markdown('Please provide a prompt. Example: `@carbonproxy /send explain JavaScript promises with examples`');
    return;
  }

  stream.progress('Running memory pipeline and sending to Copilot...');

  try {
    const sessionId = getProjectSessionId();
    const result = await chatWithMemory(sessionId, prompt);
    const optimized = (result.optimized_prompt ?? result.compressed_prompt ?? prompt).trim();

    await vscode.env.clipboard.writeText(optimized);

    try {
      await vscode.commands.executeCommand('workbench.action.chat.open', {
        query: optimized,
      });
    } catch {
      await vscode.commands.executeCommand('workbench.action.chat.open');
    }

    stream.markdown(`**Memory-pipeline prompt sent to Copilot Chat**

- Before: \`${result.tokens_before}\` tokens
- After: \`${result.tokens_after}\` tokens
- Savings: \`${result.savings_pct}%\`
  - Session: \`${sessionId}\`

  Prompt was processed via \`/api/chat\` (memory injected + stored), then optimized text was copied to clipboard as fallback.`);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    stream.markdown(`**Error:** ${msg}. Is the CarbonProxy backend running?`);
  }
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
