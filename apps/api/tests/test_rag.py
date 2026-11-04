import asyncio
import uuid

from app.services import rag
from app.services.rag import answer_question
from app.services.retrieval import RetrievedChunk


class FakeAIProvider:
    def __init__(self) -> None:
        self.received_prompt = ""

    async def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return "Users can upload and organize documents [S1]."


def test_answer_question_builds_prompt_and_citations(
    monkeypatch,
) -> None:
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    async def fake_retrieve_relevant_chunks(
        question,
        workspace_id,
        db,
        top_k=5,
    ):
        return [
            RetrievedChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                filename="smallpdf.pdf",
                chunk_index=0,
                content=(
                    "Users can upload, organize, and share "
                    "digital documents."
                ),
                similarity=0.8,
            )
        ]

    monkeypatch.setattr(
        rag,
        "retrieve_relevant_chunks",
        fake_retrieve_relevant_chunks,
    )

    provider = FakeAIProvider()

    result = asyncio.run(
        answer_question(
            question="What can users do with documents?",
            workspace_id=workspace_id,
            db=None,
            provider=provider,
        )
    )

    assert result.answer == (
        "Users can upload and organize documents [S1]."
    )

    assert len(result.citations) == 1

    citation = result.citations[0]

    assert citation.label == "S1"
    assert citation.document_id == document_id
    assert citation.filename == "smallpdf.pdf"
    assert citation.chunk_index == 0

    assert "[S1]" in provider.received_prompt
    assert "smallpdf.pdf" in provider.received_prompt
    assert "Users can upload, organize, and share" in provider.received_prompt
    assert "What can users do with documents?" in provider.received_prompt
def test_answer_question_raises_when_no_context(
    monkeypatch,
) -> None:
    async def fake_retrieve_relevant_chunks(
        question,
        workspace_id,
        db,
        top_k=5,
    ):
        return []

    monkeypatch.setattr(
        rag,
        "retrieve_relevant_chunks",
        fake_retrieve_relevant_chunks,
    )

    provider = FakeAIProvider()

    try:
        asyncio.run(
            answer_question(
                question="What is the refund policy?",
                workspace_id=uuid.uuid4(),
                db=None,
                provider=provider,
            )
        )
    except rag.RAGNoContextError as exc:
        assert str(exc) == (
            "no relevant document context is available"
        )
    else:
        raise AssertionError(
            "RAGNoContextError was not raised"
        )    