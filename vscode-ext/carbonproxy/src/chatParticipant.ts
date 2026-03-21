import * as vscode from 'vscode';
import { optimizePrompt, checkCache, storeCache, getMetrics, resetBackendSession } from './api';
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

async function handleFullRequest(
  userPrompt: string,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<void> {
  if (!userPrompt.trim()) {
    stream.markdown('Please enter a prompt. Example: `@carbonproxy explain async/await in JavaScript`');
    return;
  }

  stream.progress('Checking semantic cache...');

  try {
    const cacheResult = await checkCache(userPrompt);

    if (cacheResult.hit && cacheResult.cached_response) {
      const tokensBefore = estimateTokens(userPrompt);

      stream.markdown(cacheResult.cached_response);
      stream.markdown(
        buildMetricsTable({
          cacheHit: true,
          tokensBefore,
          tokensAfter: 0,
          co2G: 0,
          model: 'cache',
          savingsPct: 100,
        })
      );

      recordMetric({ model: 'cache', co2G: 0, tokensSaved: tokensBefore, cached: true });
      void refreshStatusBar();
      return;
    }
  } catch {
    // Non-fatal cache check failure
  }

  if (token.isCancellationRequested) return;
  stream.progress('Optimizing prompt...');

  try {
    const result = await optimizePrompt(userPrompt);

    if (token.isCancellationRequested) return;

    const responseText = result.response ?? result.cached_response ?? '';
    stream.markdown(responseText);

    stream.markdown(
      buildMetricsTable({
        cacheHit: false,
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
      cached: false,
    });
    void refreshStatusBar();

    if (responseText) {
      void storeCache(userPrompt, responseText);
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    stream.markdown(`**CarbonProxy error:** ${msg}

Make sure the backend is running:
\`\`\`bash
cd backend && uvicorn main:app --reload --port 8080
\`\`\`
`);
  }
}
