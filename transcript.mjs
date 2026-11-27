// The page's transcript (docs/wasm.md section 6.5): text appended to an
// element, gathered and added once a frame. A program that prints in a loop
// sends a message for each write, and a change to the element, with the
// layout a scroll then reads, for each was quadratic and froze the page.
// Each frame's text of a kind is one text node added to that kind's last
// span; scroller, the element that scrolls (the element itself unless
// given), stays scrolled to its end if it was there.

export class Transcript {
  constructor(element, scroller = element) {
    this.element = element;
    this.scroller = scroller;
    this.queued = [];
    this.asked = false;
    // resolved when what is queued now has been added
    this.waiting = [];
  }

  // Queues text of kind (a span's class: out, err, input, note) for the next
  // frame, joined to the text queued before it if that is of the same kind
  append(text, kind) {
    const last = this.queued.at(-1);
    if (last && last.kind === kind) last.text += text;
    else this.queued.push({text, kind});
    if (!this.asked) {
      this.asked = true;
      requestAnimationFrame(() => this.flush());
    }
  }

  // What is queued, added now
  flush() {
    this.asked = false;
    const e = this.element, s = this.scroller;
    if (this.queued.length > 0) {
      const atEnd = s.scrollTop + s.clientHeight >= s.scrollHeight - 4;
      for (const {text, kind} of this.queued.splice(0)) {
        const last = e.lastChild;
        if (last && last.nodeType === 1 && last.className === kind && last.tagName === "SPAN") {
          last.append(document.createTextNode(text));
        } else {
          const span = document.createElement("span");
          span.className = kind;
          span.textContent = text;
          e.append(span);
        }
      }
      if (atEnd) s.scrollTop = s.scrollHeight;
    }
    for (const resolve of this.waiting.splice(0)) resolve();
  }

  // Resolves once what is queued has been added
  settled() {
    if (this.queued.length === 0) return Promise.resolve();
    return new Promise(resolve => this.waiting.push(resolve));
  }

  // Everything queued and shown, gone
  clear() {
    this.queued.length = 0;
    this.element.textContent = "";
  }
}
