// A JupyterLab 4 extension that registers Quest with JupyterLab's editor,
// CodeMirror 6, for text/x-quest (the kernel's language_info mimetype) and
// .quest files: highlighting and indentation from mode.js, an indentation
// unit of four spaces, and tabs turned into spaces as they are typed or pasted
// (docs/jupyter-kernel.md section 6).

import {IEditorLanguageRegistry} from "@jupyterlab/codemirror";
import {LanguageSupport, StreamLanguage, indentUnit} from "@codemirror/language";
import {EditorState, Prec, Transaction} from "@codemirror/state";
import {UNIT, quest} from "./mode.js";

const SPACES = " ".repeat(UNIT);

// Replaces each tab a change inserts with spaces to the next multiple of UNIT
// columns, so that a Quest cell or file never holds a tab. The cursor keeps
// its place relative to the inserted text's end.
const noTabs = EditorState.transactionFilter.of((tr) => {
    if (!tr.docChanged) {
        return tr;
    }
    let tabs = false;
    tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
        tabs = tabs || inserted.toString().includes("\t");
    });
    if (!tabs) {
        return tr;
    }
    const doc = tr.startState.doc;
    const changes = [];
    tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
        const line = doc.lineAt(fromA);
        let column = fromA - line.from;
        let text = "";
        for (const ch of inserted.toString()) {
            if (ch === "\t") {
                const n = UNIT - (column % UNIT);
                text += " ".repeat(n);
                column += n;
            } else {
                text += ch;
                column = ch === "\n" ? 0 : column + 1;
            }
        }
        changes.push({from: fromA, to: toA, insert: text});
    });
    const spec = {
        changes,
        effects: tr.effects,
        scrollIntoView: tr.scrollIntoView,
    };
    if (tr.selection) {
        // Back to the start state's positions, then through the new changes
        const changeSet = tr.startState.changes(changes);
        spec.selection = tr.selection.map(tr.changes.invertedDesc, 1).map(changeSet, 1);
    }
    const event = tr.annotation(Transaction.userEvent);
    if (event) {
        spec.userEvent = event;
    }
    return spec;
});

const support = new LanguageSupport(StreamLanguage.define(quest), [Prec.high(indentUnit.of(SPACES)), noTabs]);

const plugin = {
    id: "quest-jupyterlab:language",
    description: "Quest highlighting and indentation in JupyterLab's editor",
    autoStart: true,
    requires: [IEditorLanguageRegistry],
    activate(app, languages) {
        languages.addLanguage({
            name: "quest",
            displayName: "Quest",
            mime: "text/x-quest",
            extensions: ["quest"],
            support,
        });
    },
};

export default plugin;
