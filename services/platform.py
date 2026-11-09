"""The full LynkOmni platform: v0.1 services plus Chat, the section 7 additions and the Control Center."""
from services.suite import DataRights, Platform as _Base, ServiceOff  # noqa: F401
from services.extras import Assistant, Chat, Credit, Receipts, ShopQR, Staff
from services.control import ControlCenter
from services.catalog import ServiceCatalog
from services.ads import Ads
from services.vcard import VCard
from services.billing import Billing
from services.identity import StepUp
from services.devplatform import DevPlatform
from core.ids import IdAllocator
from core.capability import Capabilities
from services.privacy import PiiVault
from identity.platform import IdentityPlatform
from services.support import Disclosure, FAQ, Feedback, Safety, StatusBoard, Support

class Platform(_Base):
    def __init__(s, path=":memory:", fx=None, providers=None, ai=None):
        super().__init__(path, fx, providers)
        s.rights = DataRights(s.c)
        s.chat = Chat(s.c, s.paylinks, s.rights)
        s.credit, s.shopqr, s.receipts, s.staff = Credit(s.c), ShopQR(s.c), Receipts(s.c), Staff(s.c)
        s.assistant = Assistant(s.c, s.accountant, s.inventory, s.credit, s.rights, ai)
        s.control = ControlCenter(s.c)
        s.services = ServiceCatalog(s.c, s.payments, s.rights, s.control)
        s.ads = Ads(s.c, s.control)
        s.billing = Billing(s.c, s.control)
        s.ads.billing = s.billing
        s.identity = StepUp()
        s.services.identity = s.identity
        s.dev = DevPlatform(s.c, s.billing, s.rights)
        s.ids, s.vault, s.caps = IdAllocator(s.c.store.db), PiiVault(s.c.store.db), Capabilities(s.c.store.db)
        s.idp = IdentityPlatform(s.c, s.ids)
        s.chat.ids = s.ids
        s.support = Support(s.c, s.ids, s.idp, s.billing)
        s.faq, s.status = FAQ(), StatusBoard(s.c, s.ids)
        s.feedback, s.safety, s.disclosure = Feedback(s.c, s.ids, s.support), Safety(s.c, s.ids, s.support), Disclosure(s.c, s.ids, s.support)
        s.vcard = VCard(s)
        from services.newsletter import Newsletter
        s.newsletter = Newsletter(s)
        from services.improvements import (AuditExport, BusinessSettings, Edge, GuestCheckout, Meter, OfflineRisk, ProofPack, Seats, Split)
        s.risk_limits, s.proof, s.audit_export, s.split = OfflineRisk(s), ProofPack(s), AuditExport(s), Split(s)
        s.seats, s.meter, s.edge, s.guest, s.settings = Seats(s), Meter(s), Edge(s), GuestCheckout(s), BusinessSettings(s)
        from services.invoicing import Invoicing
        s.invoicing = Invoicing(s)
        from services.flow import Flow
        from identity.account import Account
        from identity.automations import register as register_section_2
        s.flow = Flow(s.c)                                   # LynkFlow: every automation in catalog/automations.v1.json runs here
        s.account = Account(s, s.flow)                        # LynkOmni Account (build section 2)
        register_section_2(s.flow, s.account, s)
        from merchant.cloud import Cloud
        from merchant.agent import AgentPoint
        from merchant.delivery import Deliveries
        from merchant.restaurant import Restaurant
        from merchant.buy_together import BuyTogether
        from merchant.devices import Devices
        from merchant.business import Business
        from merchant.automations import register as register_section_3
        s.cloud = Cloud(s, s.flow)                            # Business app server events (build section 3)
        s.agent, s.deliveries, s.restaurant = AgentPoint(s.cloud, s), Deliveries(s.cloud, s), Restaurant(s.cloud, s)
        s.buy_together, s.devices, s.business = BuyTogether(s.cloud, s), Devices(s.cloud, s), Business(s.cloud, s, s.account.usernames)
        register_section_3(s.flow, s.business, s.agent, s.deliveries, s.restaurant, s.devices, s)
        from services.tracking import PlatformTracking
        s.tracking = PlatformTracking(s)                      # one tracking engine for every service (catalog/tracking.v1.json)
    def mesh_for(s, ccbox, **kw):
        """A mesh relay whose state is saved in this platform's database."""
        from services.improvements import MeshRelay
        return MeshRelay(ccbox, db=s.c.store.db, **kw)
