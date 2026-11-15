// The REPL's loop over a session (docs/wasm-plan.md steps 11 and 12), for node
// and for a page alike: questlang/driver/repl's run, reading lines without
// editing them and writing its prompts, results, and errors as it does, so
// that the REPL's transcripts (tests/repl) give their goldens.
//
// Each line is added to the phrase in progress, and the session is asked
// whether the phrase is complete (an isComplete request); a complete phrase
// that is not blank is executed. The REPL's prompt is ">>  " before a phrase
// and "    " within one; a result's first line follows "==  ", and its other
// lines are indented to match.

import {decodeRecord, requestLine} from "./session.mjs";

export const firstPrompt = ">>  ";
export const continuedPrompt = "    ";

// request(line): a Promise of a request's records, as the session gives them
// out(text), err(text): write the REPL's standard output and error
// prompt(text): writes a prompt, out unless given (a page shows it beside the
// line it reads, not in the transcript)
export class Repl {
  constructor(request, out, err, prompt = out) {
    this.request = request;
    this.out = out;
    this.err = err;
    this.showPrompt = prompt;
    this.lines = [];
  }

  // The prompt for the next line
  prompt() { return this.lines.length === 0 ? firstPrompt : continuedPrompt; }

  // Writes the first prompt
  begin() { this.showPrompt(this.prompt()); }

  // Takes one line, without its newline: runs the phrase it completes, then
  // writes the next prompt. Resolves to the records of the execution, if
  // there was one.
  async line(text) {
    this.lines.push(text);
    const phrase = this.lines.join("\n");
    const records = (await this.request(requestLine({isComplete: phrase}))).map(decodeRecord);
    const status = records.find(r => "status" in r);
    let executed = null;
    if (!status || status.status === "complete") {
      this.lines.length = 0;
      if (phrase.trim() !== "") executed = await this.execute(phrase);
    }
    this.showPrompt(this.prompt());
    return executed;
  }

  // Runs a phrase, writing its results and errors
  async execute(phrase) {
    const records = (await this.request(requestLine({execute: phrase}))).map(decodeRecord);
    for (const r of records) {
      if ("result" in r) {
        const [first, ...more] = r.result.split("\n");
        this.out(`==  ${first}\n`);
        for (const m of more) this.out(`    ${m}\n`);
      } else if ("error" in r) {
        this.err(r.rendered);
      }
    }
    return records;
  }

  // Forgets the phrase in progress, as an interrupt at the prompt does
  discard() { this.lines.length = 0; }

  // The end of the input: the phrase in progress is discarded, and the REPL
  // ends its last prompt's line
  end() {
    this.lines.length = 0;
    this.out("\n");
  }
}
