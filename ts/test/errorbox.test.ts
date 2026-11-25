// The shared message part (section 4C point 2): every level has its word and icon, an error always carries its fix, the summary
// lists each field to fix, and a problem on LynkOmni's side offers Try again and a reference.
import { test } from "node:test";
import assert from "node:assert/strict";
import { noticeHtml, summaryHtml, ourSideHtml, fieldMsgHtml } from "../src/errorbox.js";

const t = (k: string, v?: Record<string, string | number>): string => `${k}${v ? JSON.stringify(v) : ""}`;

test("each level has its word, its icon and the right way to be read out", () => {
  for (const level of ["error", "warning", "info", "success"] as const) {
    const h = level === "error" ? noticeHtml(t, { level, text: "x", how: "do this" }) : noticeHtml(t, { level, text: "x" });
    assert.ok(h.includes(`fd_${level}`) && h.includes("ebx-mark") && h.includes(`lf-${level}`), level);
    assert.ok(h.includes(level === "error" ? 'role="alert"' : 'role="status"'), level);
  }
});
test("an error says where, why and how to fix it", () => {
  const h = noticeHtml(t, { level: "error", text: "why", field: "trkStep", fix: { label: "Mark Called first", act: "trk:pick:called" } });
  assert.ok(h.includes('data-field="trkStep"') && h.includes('id="trkStep-msg"') && h.includes('data-act="trk:pick:called"') && h.includes("Mark Called first"));
  const f = noticeHtml(t, { level: "error", text: "why", fix: { label: "Choose the proof", focus: "trkProof" } });
  assert.ok(f.includes('data-ebx-focus="trkProof"'));
});
test("several things to fix are listed with a way to each field", () => {
  const h = summaryHtml(t, [{ field: "a", text: "A" }, { field: "b", text: "B" }]);
  assert.ok(h.includes('fd_things_to_fix') && h.includes('data-ebx-focus="a"') && h.includes('data-ebx-focus="b"'));
  assert.ok(summaryHtml(t, [{ field: "a", text: "A" }]).includes("fd_one_to_fix"));
  assert.equal(summaryHtml(t, []), "");
});
test("a problem on our side is never the person's fault and carries a reference", () => {
  const h = ourSideHtml(t, { ref: "LOCASE-0000-0000-0000", retryAct: "retry", supportAct: "support" });
  assert.ok(h.includes("fd_our_side") && h.includes("LOCASE-0000-0000-0000") && h.includes('data-act="retry"') && h.includes('data-act="support"'));
});
test("the field message stays empty until there is something to say", () => {
  assert.equal(fieldMsgHtml(t, "x", null, ""), '<p class="lf-msg" id="x-msg" aria-live="polite"></p>');
  assert.ok(fieldMsgHtml(t, "x", "error", "too long").includes("ebx-mark"));
});
