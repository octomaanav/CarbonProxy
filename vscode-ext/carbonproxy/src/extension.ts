import * as vscode from 'vscode';
import { initStatusBar } from './statusBar';
import { registerChatParticipant } from './chatParticipant';
import {
	handleOptimizeCommand,
	handleOptimizeForCopilot,
	handleShowDashboard,
	handleResetSession,
} from './commands';

export function activate(context: vscode.ExtensionContext): void {
	console.log('CarbonProxy AI: activating...');

	initStatusBar(context);
	registerChatParticipant(context);

	context.subscriptions.push(
		vscode.commands.registerCommand(
			'carbonproxy.optimize',
			handleOptimizeCommand
		),
		vscode.commands.registerCommand(
			'carbonproxy.optimizeForCopilot',
			handleOptimizeForCopilot
		),
		vscode.commands.registerCommand(
			'carbonproxy.showDashboard',
			handleShowDashboard
		),
		vscode.commands.registerCommand(
			'carbonproxy.resetSession',
			handleResetSession
		)
	);

	console.log('CarbonProxy AI: activated. Use @carbonproxy in Copilot Chat.');
}

export function deactivate(): void {
	// context.subscriptions handles cleanup
}
