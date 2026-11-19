import { test } from "node:test";
import assert from "node:assert/strict";
import { applyLayout, turn, keep, putBack, layoutAttributes } from "../src/turn.js";
import { DEVICES } from "../src/interfaces.generated.js";

function fakeRoot() {
  const a = new Map<string, string>(); let writes = 0;
  return { setAttribute: (k: string, v: string) => { a.set(k, v); writes++; }, getAttribute: (k: string) => a.get(k) ?? null, attrs: a, writes: () => writes };
}

test("a turn only writes the layout on the root and is announced once (TURN UPDATE 76.2)", () => {
  const root = fakeRoot();
  const up = turn(DEVICES, root, { interface: "phone.touch", width: 390, height: 844 }, null);
  assert.equal(root.attrs.get("data-nav"), "bottom_bar");
  assert.equal(up.announce, null, "the first layout is not a turn");
  const side = turn(DEVICES, root, { interface: "phone.touch", width: 844, height: 390 }, up.layout);
  assert.equal(root.attrs.get("data-nav"), "side_rail");
  assert.equal(side.announce, "nav_turned_sideways");
  const n = root.writes();
  const again = turn(DEVICES, root, { interface: "phone.touch", width: 844, height: 390 }, side.layout);
  assert.equal(again.announce, null, "the same shape twice changes nothing and says nothing");
  assert.equal(root.writes(), n);
  assert.equal(applyLayout(root, again.layout), false);
});

test("a locked kiosk keeps its direction; a person's own phone is never locked", () => {
  const kiosk = turn(DEVICES, fakeRoot(), { interface: "computer.touch", width: 1920, height: 1080, device: "self-order-kiosk", lock: "upright" }, null).layout;
  assert.deepEqual([kiosk.orientation, kiosk.locked], ["upright", true]);
  const phone = turn(DEVICES, fakeRoot(), { interface: "phone.touch", width: 844, height: 390, device: "smartphone", lock: "upright" }, null).layout;
  assert.deepEqual([phone.orientation, phone.locked], ["sideways", false]);
  assert.equal(Object.keys(layoutAttributes(kiosk)).every((k) => k.startsWith("data-")), true);
});

test("scroll positions and focus are put back after a turn", () => {
  const box = { scrollTop: 420, scrollLeft: 0 };
  let focused = 0; const field = { focus: () => { focused++; } };
  const k = keep([box], field);
  box.scrollTop = 0;                      // the browser moved it while the layout changed
  putBack(k, null);
  assert.equal(box.scrollTop, 420); assert.equal(focused, 1);
  putBack(k, field); assert.equal(focused, 1, "focus already on the same control is left alone");
});
