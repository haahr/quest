// The Quest extension: starts the Quest language server (tools/lsp/quest-lsp,
// docs/lsp-plan.md) for .quest documents. The server is found from the
// quest.server.path setting, else in the checkout the extension was
// installed from (tools/vscode/install records it in checkout.json).

const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const { LanguageClient } = require("vscode-languageclient/node");

let client;

function serverPath(context) {
    const configured = vscode.workspace.getConfiguration("quest").get("server.path");
    if (configured) {
        return configured;
    }
    const recorded = path.join(context.extensionPath, "checkout.json");
    if (fs.existsSync(recorded)) {
        const checkout = JSON.parse(fs.readFileSync(recorded, "utf8")).checkout;
        return path.join(checkout, "tools", "lsp", "quest-lsp");
    }
    return path.join(context.extensionPath, "..", "lsp", "quest-lsp");
}

function activate(context) {
    const command = serverPath(context);
    const includePaths = vscode.workspace.getConfiguration("quest").get("server.includePaths") || [];
    client = new LanguageClient(
        "quest",
        "Quest",
        { run: { command }, debug: { command } },
        {
            documentSelector: [{ scheme: "file", language: "quest" }],
            initializationOptions: { includePaths },
        });
    client.start();
    context.subscriptions.push({ dispose: () => client && client.stop() });
}

function deactivate() {
    return client ? client.stop() : undefined;
}

module.exports = { activate, deactivate };
