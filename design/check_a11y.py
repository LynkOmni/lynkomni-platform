#!/usr/bin/env python3
"""Accessibility release gate. WCAG 2.2 AA target; this checks what a script can check. A human audit is still required.
Run: python3 design/check_a11y.py"""
import json, os, re, sys
import pathlib
HERE = os.path.dirname(os.path.abspath(__file__))
def problems():
    css = pathlib.Path(os.path.join(HERE, "generated", "tokens.css")).read_text(); src = json.loads(pathlib.Path(os.path.join(HERE, "tokens.v1.json")).read_text()); out = []
    need = {"reduced motion": "prefers-reduced-motion: reduce", "forced colours": "forced-colors: active", "visible focus": ":focus-visible", "touch target var": "--touch-target",
            "touch target rule": "min-height: var(--touch-target)", "lite mode": '[data-mode="lite"]', "sunlight mode": '[data-mode="sunlight"]', "right-to-left": "direction: rtl", "high contrast": "prefers-contrast: more"}
    out += [f"missing: {k}" for k, v in need.items() if v not in css]
    if src["modes"]["touch_target_px"] < 44: out.append("touch target below 44 px")
    if src["modes"]["min_text_scale_percent"] < 200: out.append("text scaling below 200%")
    if re.search(r"--text-\d+: [\d.]+px", css): out.append("type sizes must be rem, not px, so text can scale")
    icons, labels = set(), set()
    for k, v in src["states"].items():
        if not v.get("icon") or not v.get("label"): out.append(f"state {k} must have an icon and a label (never colour alone)")
        if v["icon"] in icons or v["label"] in labels: out.append(f"state {k} repeats another state's icon or label")
        icons.add(v["icon"]); labels.add(v["label"])
        if f"--status-{v['tone']}-text" not in css: out.append(f"state {k}: tone {v['tone']} has no token")
    if set(src["states"]) != {"queued", "sent", "accepted", "confirmed", "failed"}: out.append("state vocabulary must be queued, sent, accepted, confirmed, failed")
    return out
if __name__ == "__main__":
    p = problems(); print("\n".join(p) if p else "a11y gate: ok (script checks only; a human audit is still required)"); sys.exit(1 if p else 0)
