"""The Business app and the whole of LynkPOS, build section 3 (master blueprint 41 S row 3, 42 C, 42 I, 42 J, 44 C, 44 I N1 N2 N8 N11, 45 E row 3).

The device side is dv/box.py (LynkDVBox: every local fact as a contract event, offline). This package is the cloud side and the
rules that need no device: the partner's answers to agent, collection and partner-finance requests, deliveries, group orders,
registered devices and the web rule, device drivers behind one interface, the business profile (tabs by type, setup, daily close,
second currency, practice mode) and the twenty section-3 automations on LynkFlow.

    from merchant.cloud import Cloud            # server events into the platform store, validated against the contract
    from merchant.agent import AgentPoint       # agent point mode: partners, float, limits, confirmations, commissions, statements
    from merchant.delivery import Deliveries    # N8 delivery and pickup
    from merchant.restaurant import Restaurant  # N1 tables, kitchen, tips: tier limits and projections
    from merchant.buy_together import BuyTogether   # N11 group orders, no pooled money
    from merchant.devices import Devices, DeviceDrivers, SandboxDrivers   # registered devices, the web rule, printers and readers
    from merchant.business import Business      # tabs, setup, daily close, second currency, receipt channels, data sharing
    from merchant.automations import register   # the 20 automations

LynkOmni never holds money: cash belongs to the agent, the float sits in the agent's own account at the licensed partner,
and nothing is shown as done before the partner confirms."""
