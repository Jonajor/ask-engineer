import os
import psycopg2
from pgvector.psycopg2 import register_vector

EMBEDDING_DIM = 384


def get_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    register_vector(conn)
    return conn


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL DEFAULT 'trial',
                    trial_ends_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS report_chunks (
                    id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIM}),
                    company_id UUID,
                    uploaded_by UUID
                )
            """)

            # Idempotent migrations for existing report_chunks table
            cur.execute("ALTER TABLE report_chunks ADD COLUMN IF NOT EXISTS company_id UUID")
            cur.execute("ALTER TABLE report_chunks ADD COLUMN IF NOT EXISTS uploaded_by UUID")

            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_report_id ON report_chunks(report_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_company_id ON report_chunks(company_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_uploaded_by ON report_chunks(uploaded_by)")

        conn.commit()
