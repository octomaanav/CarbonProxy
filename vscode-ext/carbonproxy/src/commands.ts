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
