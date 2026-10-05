"""Reconstruct document-processing schema from the existing database.

Revision ID: 0004
Revises: 0003

Reconstructed from inspected schema; the original migration was unavailable.
"""

from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")

    op.execute("""
        ALTER TABLE public.documents
        ADD COLUMN status character varying NOT NULL DEFAULT 'uploaded',
        ADD COLUMN processing_error character varying
    """)

    op.execute("""
        CREATE TABLE public.document_chunks (
            id uuid NOT NULL,
            document_id uuid NOT NULL,
            workspace_id uuid NOT NULL,
            chunk_index integer NOT NULL,
            content character varying NOT NULL,
            embedding public.vector(384) NOT NULL,
            created_at timestamp with time zone NOT NULL DEFAULT now(),

            CONSTRAINT document_chunks_pkey PRIMARY KEY (id),

            CONSTRAINT document_chunks_document_id_fkey
                FOREIGN KEY (document_id)
                REFERENCES public.documents(id) ON DELETE CASCADE,

            CONSTRAINT document_chunks_workspace_id_fkey
                FOREIGN KEY (workspace_id)
                REFERENCES public.workspaces(id) ON DELETE CASCADE,

            CONSTRAINT document_chunks_document_id_chunk_index_key
                UNIQUE (document_id, chunk_index)
        )
    """)

    op.execute("""
        CREATE INDEX ix_document_chunks_document_id
        ON public.document_chunks (document_id)
    """)

    op.execute("""
        CREATE INDEX ix_document_chunks_workspace_id
        ON public.document_chunks (workspace_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE public.document_chunks")

    op.execute("""
        ALTER TABLE public.documents
        DROP COLUMN processing_error,
        DROP COLUMN status
    """)