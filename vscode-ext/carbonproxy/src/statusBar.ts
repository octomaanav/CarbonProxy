import * as vscode from 'vscode';
import { getMetrics } from './api';

let bar: vscode.StatusBarItem;
let pollTimer: NodeJS.Timeout | undefined;

export function initStatusBar(context: vscode.ExtensionContext): void {
  bar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  bar.text = '$(leaf) 0.000g CO₂ saved';
  bar.tooltip = 'CarbonProxy: CO₂ avoided this session — click for stats';
  bar.command = 'carbonproxy.showDashboard';
  bar.show();
  context.subscriptions.push(bar);

  pollTimer = setInterval(refreshStatusBar, 5000);
  context.subscriptions.push({
    dispose: () => {
      if (pollTimer) clearInterval(pollTimer);
    },
  });
}

export async function refreshStatusBar(): Promise<void> {
  try {
    const metrics = await getMetrics();
    bar.text = `$(leaf) ${metrics.co2_saved_g.toFixed(3)}g CO₂ saved`;
    bar.backgroundColor = undefined;
  } catch {
    bar.text = '$(leaf) CarbonProxy offline';
    bar.backgroundColor = new vscode.ThemeColor(
      'statusBarItem.warningBackground'
    );
  }
}

export function setStatusBarText(text: string): void {
  if (bar) bar.text = text;
}
