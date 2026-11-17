CREATE TABLE IF NOT EXISTS sessions (
 id text PRIMARY KEY, wallet text NOT NULL, cap bigint NOT NULL CHECK(cap>0), reserved bigint NOT NULL DEFAULT 0,
 spent bigint NOT NULL DEFAULT 0, expires_at timestamptz NOT NULL,
 CHECK(reserved>=0 AND spent>=0 AND spent+reserved<=cap)
);
CREATE TABLE IF NOT EXISTS runs (
 id uuid PRIMARY KEY, session_id text NOT NULL REFERENCES sessions(id), goal text NOT NULL,
 status text NOT NULL DEFAULT 'queued', plan jsonb, results jsonb NOT NULL DEFAULT '{}',
 answer text, share_token text UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_session ON runs(session_id, created_at DESC);
CREATE TABLE IF NOT EXISTS events (
 id bigserial PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(id), type text NOT NULL, data jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id,id);
CREATE TABLE IF NOT EXISTS payments (
 id text PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(id), agent_id bigint NOT NULL,
 amount bigint NOT NULL CHECK(amount>0), status text NOT NULL DEFAULT 'reserved',
 payload jsonb, tx_hash text, escrow_id text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS payments_run ON payments(run_id);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS obligation text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'x402'
 CHECK(mode IN ('x402','escrow'));
CREATE UNIQUE INDEX IF NOT EXISTS payments_obligation_active ON payments(obligation)
 WHERE status <> 'cancelled';
CREATE TABLE IF NOT EXISTS agent_calls (
 id text PRIMARY KEY, binding text NOT NULL, status text NOT NULL, result jsonb, receipt jsonb,
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chain_transactions (
 id text PRIMARY KEY, raw_tx text NOT NULL, tx_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
