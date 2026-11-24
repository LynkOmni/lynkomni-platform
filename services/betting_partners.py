"""Licensed betting operators behind the betting counter (BETTING UPDATE, owner 2026-11-24, master blueprint section 86).

"betting" needs a licensed betting operator per country, signed through the Partner Hub, and stays "Coming to your country soon."
until it is signed there and the lawyer has confirmed the country's law (providers/registry.v1.json). The operator's system
takes the bet, sets the odds, decides every result and amount, locks payouts and answers referrals; LynkOmni only carries the
request and writes the operator's answer from the cloud. Rules every adapter keeps:
- a bet or a payout is a fact only when the operator confirms it; a repeated answer changes nothing;
- a customer's ID and the photos of a big win go only to the operator, never into an event or LynkOmni's storage;
- amounts are whole minor units of the shop's currency; odds are whole thousandths (core/betting.py).
"""
from core import betting as B


class BettingOperator:
    """A licensed betting operator: its games and odds, bets, ticket checks, payout locks and head-office referrals."""
    def games(self, country):
        raise NotImplementedError

    def place(self, shop_ref, selections, stake, currency, method):
        raise NotImplementedError

    def check(self, ticket_code):
        raise NotImplementedError

    def lock_payout(self, ticket_code, shop_ref):
        raise NotImplementedError

    def refer(self, ticket_code, shop_ref, evidence_ref):
        raise NotImplementedError


class SandboxBettingOperator(BettingOperator):
    """SANDBOX: a labelled sample operator with sample games and tickets; no real bet is taken and no money moves."""
    def __init__(self):
        self.tickets = {}
        self._n = 0

    def games(self, country):
        return [{"game": f"sample-{i}", "sample": True, "odds": {"home": 1850 + 50 * i, "draw": 3200, "away": 2100 + 100 * i}} for i in range(1, 6)]

    def place(self, shop_ref, selections, stake, currency, method):
        if not B.stake_method_ok(method):
            return {"state": "failed", "reason": "method_not_allowed"}
        if not selections:
            return {"state": "failed", "reason": "no_selection"}
        self._n += 1
        code = f"SAMPLE{self._n:08d}"
        win = B.possible_win(stake, [s["odds"] for s in selections])
        self.tickets[code] = {"known": True, "result": "pending", "paid": False, "payable": 0, "possible_win": win, "expires": 90, "sample": True}
        return {"state": "confirmed", "ticket_code": code, "possible_win": win, "currency": currency, "sample": True}

    def settle(self, ticket_code, result):
        """Sandbox only: what the operator's system does when the games end."""
        t = self.tickets[ticket_code]
        t["result"] = result
        t["payable"] = t["possible_win"] if result == "won" else 0
        return t

    def check(self, ticket_code):
        return dict(self.tickets.get(ticket_code, {"known": False}))

    def lock_payout(self, ticket_code, shop_ref):
        t = self.tickets.get(ticket_code)
        if not t or t["paid"] or t["result"] not in ("won", "void"):
            return {"state": "failed", "reason": "not_payable"}
        t["paid"] = True                                  # locked once: a second lock, a copy included, fails
        return {"state": "confirmed", "payable": t["payable"]}

    def refer(self, ticket_code, shop_ref, evidence_ref):
        if not evidence_ref:
            return {"state": "failed", "reason": "photos_missing"}               # the photos went to the operator, which gave this reference
        return {"state": "sent", "step": "referred"}
