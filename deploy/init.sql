CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agentpilot_bootstrap (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO agentpilot_bootstrap (name)
VALUES ('AgentPilot database initialized')
ON CONFLICT DO NOTHING;
