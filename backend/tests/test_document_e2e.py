"""End-to-end endpoint tests for document upload, listing, retrieval, and RAG drill."""
import pytest
from starlette.testclient import TestClient
from server import app
from auth import get_current_user


class FakeCollection:
    def __init__(self):
        self.data = []

    async def insert_one(self, doc):
        self.data.append(dict(doc))
        return type("Result", (), {"inserted_id": doc.get("id")})()

    async def insert_many(self, docs):
        for d in docs:
            self.data.append(dict(d))
        return type("Result", (), {"inserted_ids": [d.get("id") for d in docs]})()

    def find(self, query=None, projection=None):
        results = []
        for item in self.data:
            match = True
            if query:
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
            if match:
                res = dict(item)
                if projection:
                    for pk, pv in projection.items():
                        if pv == 0 and pk in res:
                            del res[pk]
                results.append(res)

        class FakeCursor:
            def __init__(self, items):
                self._items = items

            def sort(self, *args, **kwargs):
                return self

            async def to_list(self, length=100):
                return self._items[:length]

        return FakeCursor(results)

    async def find_one(self, query=None, projection=None):
        for item in self.data:
            match = True
            if query:
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
            if match:
                res = dict(item)
                if projection:
                    for pk, pv in projection.items():
                        if pv == 0 and pk in res:
                            del res[pk]
                return res
        return None

    async def delete_many(self, query):
        initial = len(self.data)
        self.data = [
            item for item in self.data if not all(item.get(k) == v for k, v in query.items())
        ]
        return type("Result", (), {"deleted_count": initial - len(self.data)})()

    async def delete_one(self, query):
        for i, item in enumerate(self.data):
            if all(item.get(k) == v for k, v in query.items()):
                self.data.pop(i)
                return type("Result", (), {"deleted_count": 1})()
        return type("Result", (), {"deleted_count": 0})()

    async def create_index(self, *args, **kwargs):
        return "index_ok"


class FakeDB:
    def __init__(self):
        self.documents = FakeCollection()
        self.document_chunks = FakeCollection()
        self.sessions = FakeCollection()
        self.users = FakeCollection()


@pytest.fixture
def test_app():
    fake_db = FakeDB()
    app.state.db = fake_db

    fake_user = {"id": "user-test-123", "email": "test@typeforge.app", "role": "user"}
    app.dependency_overrides[get_current_user] = lambda: fake_user
    client = TestClient(app)
    yield client, fake_db
    app.dependency_overrides.clear()


def test_upload_and_retrieve_document_e2e(test_app, monkeypatch):
    client, fake_db = test_app

    # 1. Upload a markdown document
    content = b"""# Distributed Systems Notes
Consensus protocols ensure distributed processes agree on a single data value.
The Raft consensus algorithm decomposes state machine replication into leader election, log replication, and safety.
Paxos achieves consensus across unreliable network links through two phases of prepare and accept rounds.
Byzantine fault tolerance handles arbitrary node failures including malicious attacks.
"""
    files = {"file": ("distributed_systems.md", content, "text/markdown")}
    resp = client.post("/api/documents", files=files)
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["filename"] == "distributed_systems.md"
    assert doc["total_chunks"] >= 1
    doc_id = doc["id"]

    # 2. List documents
    list_resp = client.post if False else client.get("/api/documents")
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id

    # 3. Get document details and chunks
    detail_resp = client.get(f"/api/documents/{doc_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["document"]["id"] == doc_id
    assert len(detail["chunks"]) >= 1
    assert "embedding" not in detail["chunks"][0]  # Verify embeddings excluded from client

    # 4. Generate AI Drill with Mock LLM
    def mock_chat(system, user, **kwargs):
        return '{"text": "Consensus protocols in distributed systems enable nodes to agree on a state.", "notes": ["Raft leader election", "Log replication"]}'

    monkeypatch.setattr("ai_service._chat", mock_chat)

    drill_resp = client.post(
        "/api/documents/generate-drill",
        json={"document_id": doc_id, "query": "Raft", "difficulty": "Intermediate"},
    )
    assert drill_resp.status_code == 200
    drill = drill_resp.json()
    assert "Consensus protocols" in drill["text"]
    assert drill["domain"] == "Custom Document"
    assert drill["topic"] == "distributed_systems.md"
    assert len(drill["notes"]) == 2

    # 5. Delete document
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"deleted": True}

    # Verify document is gone
    get_after = client.get(f"/api/documents/{doc_id}")
    assert get_after.status_code == 404
