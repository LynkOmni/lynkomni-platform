-- LynkOmni core schema (PostgreSQL dialect). NOT executed in the build sandbox: run it through the CI database service before relying on it. Invariants live in the database, not only in application code.

CREATE TABLE public_ids (
  public_id   TEXT PRIMARY KEY CHECK (public_id ~ '^LO[A-Z]{2,4}-[0-9]{4}-[0-9]{4}-[0-9]{4}$'),
  type        TEXT NOT NULL,
  internal_id TEXT,
  status      TEXT NOT NULL CHECK (status IN ('assigned','leased','retired')),
  leased_to   TEXT,
  created_at  DOUBLE PRECISION NOT NULL
);
CREATE UNIQUE INDEX public_ids_internal ON public_ids(type, internal_id) WHERE internal_id IS NOT NULL;

CREATE TABLE persons (internal_id TEXT PRIMARY KEY, lynkid TEXT NOT NULL UNIQUE REFERENCES public_ids(public_id),
  status TEXT NOT NULL CHECK (status IN ('active','restricted','suspended','closed')), created_at DOUBLE PRECISION NOT NULL);
CREATE TABLE organizations (internal_id TEXT PRIMARY KEY, lynkoid TEXT NOT NULL UNIQUE REFERENCES public_ids(public_id),
  kind TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('active','restricted','suspended','closed')), created_at DOUBLE PRECISION NOT NULL);
CREATE TABLE memberships (member_id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES persons(internal_id), org_id TEXT NOT NULL REFERENCES organizations(internal_id),
  role TEXT NOT NULL CHECK (role IN ('owner','manager','cashier')), status TEXT NOT NULL CHECK (status IN ('active','removed')));
CREATE UNIQUE INDEX membership_active ON memberships(person_id, org_id) WHERE status = 'active';

CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, at DOUBLE PRECISION NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT, outcome TEXT NOT NULL);

CREATE TABLE verification_cases (case_id TEXT PRIMARY KEY, subject TEXT NOT NULL, claim TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('not_started','pending','in_review','verified','additional_evidence_required','rejected','expired','suspended','revoked')),
  method TEXT, policy_version TEXT NOT NULL, source_available BOOLEAN NOT NULL DEFAULT TRUE, expires_at DOUBLE PRECISION,
  CHECK (status <> 'verified' OR (method IS NOT NULL AND source_available)));   -- an unavailable source can never produce 'verified'

CREATE TABLE consent_records (consent_id TEXT PRIMARY KEY, subject TEXT NOT NULL, grantee TEXT NOT NULL, scope TEXT NOT NULL, expires_at DOUBLE PRECISION, revoked_at DOUBLE PRECISION);

CREATE TABLE support_cases (case_id TEXT PRIMARY KEY, requester_ref TEXT NOT NULL, category TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE conversations (conv_id TEXT PRIMARY KEY,
  route TEXT NOT NULL CHECK (route IN ('business','support')),            -- there is no personal or group route
  case_id TEXT REFERENCES support_cases(case_id), owner_kind TEXT NOT NULL CHECK (owner_kind IN ('agent','queue','merchant')), owner TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('initiated','queued','assigned','in_progress','pending_customer','transfer_pending','resolved','closed')));
CREATE TABLE transfers (transfer_id TEXT PRIMARY KEY, conv_id TEXT NOT NULL REFERENCES conversations(conv_id), from_owner TEXT NOT NULL, dest_kind TEXT NOT NULL, dest TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending','accepted','rejected','timed_out')), reason TEXT, requested_at DOUBLE PRECISION NOT NULL);

-- Triggers (PL/pgSQL)
CREATE FUNCTION forbid() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION '%', TG_ARGV[0]; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER public_ids_never_deleted BEFORE DELETE ON public_ids FOR EACH ROW EXECUTE FUNCTION forbid('public identifiers are permanent and are never deleted or reissued');
CREATE TRIGGER public_ids_immutable BEFORE UPDATE OF public_id, type ON public_ids FOR EACH ROW EXECUTE FUNCTION forbid('public identifier and type never change');
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION forbid('audit records are append-only');
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION forbid('audit records are append-only');
CREATE FUNCTION keep_one_owner() RETURNS trigger AS $$ BEGIN
  IF OLD.role = 'owner' AND OLD.status = 'active' AND (TG_OP = 'DELETE' OR NEW.role <> 'owner' OR NEW.status <> 'active')
     AND (SELECT COUNT(*) FROM memberships WHERE org_id = OLD.org_id AND role = 'owner' AND status = 'active' AND member_id <> OLD.member_id) = 0
  THEN RAISE EXCEPTION 'an organization must keep at least one active owner'; END IF;
  RETURN COALESCE(NEW, OLD); END; $$ LANGUAGE plpgsql;
CREATE TRIGGER last_owner BEFORE UPDATE OR DELETE ON memberships FOR EACH ROW EXECUTE FUNCTION keep_one_owner();
