-- LynkOmni core schema (SQLite dialect, used on devices and in tests). Invariants live in the database, not only in application code.
PRAGMA foreign_keys = ON;

CREATE TABLE public_ids (
  public_id   TEXT PRIMARY KEY CHECK (public_id GLOB 'LO[A-Z]*-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
  type        TEXT NOT NULL,
  internal_id TEXT,
  status      TEXT NOT NULL CHECK (status IN ('assigned','leased','retired')),
  leased_to   TEXT,
  created_at  REAL NOT NULL
);
CREATE UNIQUE INDEX public_ids_internal ON public_ids(type, internal_id) WHERE internal_id IS NOT NULL;
CREATE TRIGGER public_ids_never_deleted BEFORE DELETE ON public_ids BEGIN SELECT RAISE(ABORT, 'public identifiers are permanent and are never deleted or reissued'); END;
CREATE TRIGGER public_ids_immutable BEFORE UPDATE OF public_id, type ON public_ids BEGIN SELECT RAISE(ABORT, 'public identifier and type never change'); END;

CREATE TABLE persons (internal_id TEXT PRIMARY KEY, lynkid TEXT NOT NULL UNIQUE REFERENCES public_ids(public_id),
  status TEXT NOT NULL CHECK (status IN ('active','restricted','suspended','closed')), created_at REAL NOT NULL);
CREATE TABLE organizations (internal_id TEXT PRIMARY KEY, lynkoid TEXT NOT NULL UNIQUE REFERENCES public_ids(public_id),
  kind TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('active','restricted','suspended','closed')), created_at REAL NOT NULL);
CREATE TABLE memberships (member_id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES persons(internal_id), org_id TEXT NOT NULL REFERENCES organizations(internal_id),
  role TEXT NOT NULL CHECK (role IN ('owner','manager','cashier')), status TEXT NOT NULL CHECK (status IN ('active','removed')));
CREATE UNIQUE INDEX membership_active ON memberships(person_id, org_id) WHERE status = 'active';
CREATE TRIGGER last_owner_update BEFORE UPDATE ON memberships WHEN OLD.role = 'owner' AND OLD.status = 'active' AND (NEW.role <> 'owner' OR NEW.status <> 'active')
  AND (SELECT COUNT(*) FROM memberships WHERE org_id = OLD.org_id AND role = 'owner' AND status = 'active' AND member_id <> OLD.member_id) = 0
  BEGIN SELECT RAISE(ABORT, 'an organization must keep at least one active owner'); END;
CREATE TRIGGER last_owner_delete BEFORE DELETE ON memberships WHEN OLD.role = 'owner' AND OLD.status = 'active'
  AND (SELECT COUNT(*) FROM memberships WHERE org_id = OLD.org_id AND role = 'owner' AND status = 'active' AND member_id <> OLD.member_id) = 0
  BEGIN SELECT RAISE(ABORT, 'an organization must keep at least one active owner'); END;

CREATE TABLE audit_events (event_id TEXT PRIMARY KEY, at REAL NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT, outcome TEXT NOT NULL);
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit records are append-only'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit records are append-only'); END;

CREATE TABLE verification_cases (case_id TEXT PRIMARY KEY, subject TEXT NOT NULL, claim TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('not_started','pending','in_review','verified','additional_evidence_required','rejected','expired','suspended','revoked')),
  method TEXT, policy_version TEXT NOT NULL, source_available INTEGER NOT NULL DEFAULT 1, expires_at REAL,
  CHECK (status <> 'verified' OR (method IS NOT NULL AND source_available = 1)));   -- an unavailable source can never produce 'verified'

CREATE TABLE consent_records (consent_id TEXT PRIMARY KEY, subject TEXT NOT NULL, grantee TEXT NOT NULL, scope TEXT NOT NULL, expires_at REAL, revoked_at REAL);

CREATE TABLE support_cases (case_id TEXT PRIMARY KEY, requester_ref TEXT NOT NULL, category TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE conversations (conv_id TEXT PRIMARY KEY,
  route TEXT NOT NULL CHECK (route IN ('business','support')),            -- there is no personal or group route
  case_id TEXT REFERENCES support_cases(case_id), owner_kind TEXT NOT NULL CHECK (owner_kind IN ('agent','queue','merchant')), owner TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('initiated','queued','assigned','in_progress','pending_customer','transfer_pending','resolved','closed')));
CREATE TABLE transfers (transfer_id TEXT PRIMARY KEY, conv_id TEXT NOT NULL REFERENCES conversations(conv_id), from_owner TEXT NOT NULL, dest_kind TEXT NOT NULL, dest TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending','accepted','rejected','timed_out')), reason TEXT, requested_at REAL NOT NULL);
