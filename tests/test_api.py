from uuid import uuid4


def _register_and_login(client):
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "StrongPass123"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    body = login_response.json()

    token = body["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers


def test_register_and_login_success(client):
    email = f"auth-{uuid4().hex[:8]}@example.com"
    password = "StrongPass123"

    register_response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["token"]
    assert isinstance(payload["user_id"], int)


def test_add_text_note_requires_auth(client):
    response = client.post("/notes/text", json={"content": "My note"})
    assert response.status_code == 401


def test_add_text_note_authenticated(client, monkeypatch):
    import api.notes as notes_api

    monkeypatch.setattr(notes_api, "embed_texts", lambda texts: [[0.0] * 384 for _ in texts])
    monkeypatch.setattr(notes_api, "upsert_chunks", lambda *args, **kwargs: None)

    headers = _register_and_login(client)

    response = client.post(
        "/notes/text",
        json={"content": "FastAPI is great for APIs."},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Note added successfully"
    assert body["source"] == "text"


def test_query_fallback_returns_answer_when_no_chunks(client, monkeypatch):
    import api.query as query_api

    monkeypatch.setattr(query_api, "embed_texts", lambda texts: [[0.0] * 384 for _ in texts])
    monkeypatch.setattr(query_api, "search_chunks", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        query_api,
        "generate_answer",
        lambda context, question: "General fallback answer",
    )

    headers = _register_and_login(client)

    response = client.post(
        "/query/",
        json={"question": "Explain Python briefly"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "General fallback answer"
    assert body["sources_count"] == 0


def test_stats_track_query_activity(client, monkeypatch):
    import api.query as query_api

    monkeypatch.setattr(query_api, "embed_texts", lambda texts: [[0.0] * 384 for _ in texts])
    monkeypatch.setattr(query_api, "search_chunks", lambda *args, **kwargs: [])
    monkeypatch.setattr(query_api, "generate_answer", lambda context, question: "answer")

    headers = _register_and_login(client)

    for _ in range(2):
        query_response = client.post(
            "/query/",
            json={"question": "What is stored?"},
            headers=headers,
        )
        assert query_response.status_code == 200

    stats_response = client.get("/stats/me", headers=headers)
    assert stats_response.status_code == 200

    stats = stats_response.json()
    assert stats["queries_total"] >= 2
    assert stats["queries_last_7d"] >= 2


def test_note_list_filter_and_delete(client, monkeypatch):
    import api.notes as notes_api

    monkeypatch.setattr(notes_api, "embed_texts", lambda texts: [[0.0] * 384 for _ in texts])
    monkeypatch.setattr(notes_api, "upsert_chunks", lambda *args, **kwargs: None)
    monkeypatch.setattr(notes_api, "delete_note_chunks", lambda *args, **kwargs: None)

    headers = _register_and_login(client)

    note_ids = []
    for content in ["My first managed note", "My second managed note", "My third managed note"]:
        create_response = client.post(
            "/notes/text",
            json={"content": content},
            headers=headers,
        )
        assert create_response.status_code == 200
        note_ids.append(create_response.json()["note_id"])

    note_id = note_ids[0]

    list_response = client.get("/notes/", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total_count"] >= 3
    assert list_payload["returned_count"] >= 1
    assert any(note["id"] == note_id for note in list_payload["notes"])

    filtered_response = client.get("/notes/?source=text", headers=headers)
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["total_count"] >= 3
    assert all(note["source"] == "text" for note in filtered_payload["notes"])

    paged_response = client.get("/notes/?limit=1&offset=1", headers=headers)
    assert paged_response.status_code == 200
    paged_payload = paged_response.json()
    assert paged_payload["limit"] == 1
    assert paged_payload["offset"] == 1
    assert paged_payload["returned_count"] == 1

    delete_response = client.delete(f"/notes/{note_id}", headers=headers)
    assert delete_response.status_code == 200

    after_delete_response = client.get("/notes/", headers=headers)
    assert after_delete_response.status_code == 200
    after_delete_payload = after_delete_response.json()
    assert all(note["id"] != note_id for note in after_delete_payload["notes"])
