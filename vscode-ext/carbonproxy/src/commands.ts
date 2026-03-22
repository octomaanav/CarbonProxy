import * as vscode from 'vscode';
import { optimizePrompt, resetBackendSession } from './api';
import { buildResultHtml } from './webview';
import { recordMetric, resetSession } from './session';
import { refreshStatusBar } from './statusBar';

export async function handleOptimizeCommand(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage('CarbonProxy: Open a file first.');
    return;
  }

  const selected = editor.document.getText(editor.selection);
  if (!selected.trim()) {
    vscode.window.showWarningMessage('CarbonProxy: Select a prompt to optimize.');
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'CarbonProxy: Optimizing prompt...',
      cancellable: false,
    },
    async () => {
      try {
        const result = await optimizePrompt(selected);

        recordMetric({
          model: result.model ?? 'unknown',
          co2G: result.co2_g ?? 0,
          tokensSaved: (result.tokens_before ?? 0) - (result.tokens_after ?? 0),
          cached: result.cache_hit ?? false,
        });

        void refreshStatusBar();
        showResultPanel(result);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(
          `CarbonProxy: ${msg}. Is the backend running?`
        );
      }
    }
  );
}

export async function handleOptimizeForCopilot(): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  const selected = editor ? editor.document.getText(editor.selection).trim() : '';

  const input = await vscode.window.showInputBox({
    title: 'CarbonProxy: Optimize Prompt for Copilot',
    prompt: 'Paste or type the prompt you want to optimize before sending to Copilot',
    value: selected,
    ignoreFocusOut: true,
    validateInput: (value) => (value.trim() ? null : 'Prompt cannot be empty'),
  });

  if (!input || !input.trim()) {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'CarbonProxy: Optimizing for Copilot...',
      cancellable: false,
    },
    async () => {
      try {
        const result = await optimizePrompt(input);
        const optimized = (result.optimized_prompt ?? input).trim();

        const action = await vscode.window.showQuickPick(
          [
            'Send to Copilot Chat',
            'Copy optimized prompt',
            'Replace selected text',
            'Preview optimization',
          ],
          {
            title: 'CarbonProxy: Optimized prompt ready',
            placeHolder: `${result.tokens_before} → ${result.tokens_after} tokens (${result.savings_pct}% saved)`,
            ignoreFocusOut: true,
          }
        );

        if (!action) {
          return;
        }

        if (action === 'Copy optimized prompt') {
          await vscode.env.clipboard.writeText(optimized);
          vscode.window.showInformationMessage('CarbonProxy: Optimized prompt copied to clipboard.');
          return;
        }

        if (action === 'Replace selected text') {
          if (!editor || editor.selection.isEmpty) {
            vscode.window.showWarningMessage('CarbonProxy: No active selection to replace.');
            return;
          }
          await editor.edit((builder) => builder.replace(editor.selection, optimized));
          vscode.window.showInformationMessage('CarbonProxy: Replaced selected text with optimized prompt.');
          return;
        }

        if (action === 'Preview optimization') {
          showResultPanel(result);
          return;
        }

        await vscode.env.clipboard.writeText(optimized);
        try {
          await vscode.commands.executeCommand('workbench.action.chat.open', {
            query: optimized,
          });
        } catch {
          await vscode.commands.executeCommand('workbench.action.chat.open');
        }

        vscode.window.showInformationMessage(
          'CarbonProxy: Opened Copilot Chat. Optimized prompt has been copied to clipboard.'
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(
          `CarbonProxy: ${msg}. Is the backend running?`
        );
      }
    }
  );
}

export function handleShowDashboard(): void {
  const config = vscode.workspace.getConfiguration('carbonproxy');
  const backendUrl = config.get<string>('backendUrl', 'http://localhost:8080');
  const dashboardUrl = backendUrl.replace(':8080', ':5173');
  void vscode.env.openExternal(vscode.Uri.parse(dashboardUrl));
}

export async function handleResetSession(): Promise<void> {
  try {
    await resetBackendSession();
  } catch {
    // Backend reset failing is non-fatal
  }
  resetSession();
  void refreshStatusBar();
  vscode.window.showInformationMessage('CarbonProxy: Session metrics reset.');
}

function showResultPanel(data: Awaited<ReturnType<typeof optimizePrompt>>): void {
  const panel = vscode.window.createWebviewPanel(
    'carbonproxyResult',
    'CarbonProxy Result',
    vscode.ViewColumn.Beside,
    { enableScripts: false }
  );
  panel.webview.html = buildResultHtml(data);
}
