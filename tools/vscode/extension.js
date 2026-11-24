// The Quest extension: starts the Quest language server (`quest lsp`,
// docs/lsp.md) for .quest documents. The quest command is the
// quest.server.path setting, else ./quest in the checkout the extension was
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
        return path.join(checkout, "quest");
    }
    return path.join(context.extensionPath, "..", "..", "quest");
}

function activate(context) {
    const command = serverPath(context);
    const includePaths = vscode.workspace.getConfiguration("quest").get("server.includePaths") || [];
    client = new LanguageClient(
        "quest",
        "Quest",
        { run: { command, args: ["lsp"] }, debug: { command, args: ["lsp"] } },
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
