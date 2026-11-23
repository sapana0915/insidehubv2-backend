import uuid

from app.organizations.models import Organization
from app.users.models import User
from tests.conftest import TestingSessionLocal


def _register_and_login(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"writer_{suffix}@example.com"
    token = client.post(
        "/api/v1/users/register",
        json={
            "email": email,
            "username": f"writer_{suffix}",
            "password": "password123",
        },
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _assign_org(headers, client, *, slug: str | None = None) -> str:
    """Put the logged-in user into an organization so they can post."""
    me = client.get("/api/v1/users/me", headers=headers).json()
    org_slug = slug or f"org-{uuid.uuid4().hex[:8]}"
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == uuid.UUID(me["id"])).one()
        org = Organization(
            name=org_slug,
            slug=org_slug,
            created_by_id=user.id,
        )
        db.add(org)
        db.flush()
        user.organization_id = org.id
        user.org_role = "owner"
        db.commit()
        return str(org.id)
    finally:
        db.close()


def _register_org_user(client, *, org_slug: str | None = None):
    headers = _register_and_login(client)
    _assign_org(headers, client, slug=org_slug)
    return headers


def _create_post(client, headers, **overrides):
    body = {
        "title": "Sunrise over Hampi",
        "content": "Boulders, temples and a very early alarm.",
        "category": "travel-stories",
        "images": ["https://example.com/hampi.jpg"],
    }
    body.update(overrides)
    return client.post("/api/v1/posts", json=body, headers=headers)


def test_categories_are_public(client):
    response = client.get("/api/v1/posts/categories")
    assert response.status_code == 200
    slugs = [c["slug"] for c in response.json()]
    assert "travel-stories" in slugs


def test_create_post_embeds_author(client):
    headers = _register_org_user(client)
    response = _create_post(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["author"]["username"].startswith("writer_")
    assert body["images"][0]["image_url"] == "https://example.com/hampi.jpg"
    assert body["organization_id"]


def test_invalid_category_rejected(client):
    headers = _register_org_user(client)
    response = _create_post(client, headers, category="not-a-category")
    assert response.status_code == 422


def test_feed_is_org_scoped(client):
    org_slug = f"shared-{uuid.uuid4().hex[:6]}"
    alice = _register_org_user(client, org_slug=org_slug)
    bob = _register_and_login(client)
    # Put bob in the same org as alice
    me_alice = client.get("/api/v1/users/me", headers=alice).json()
    me_bob = client.get("/api/v1/users/me", headers=bob).json()
    db = TestingSessionLocal()
    try:
        alice_user = db.query(User).filter(User.id == uuid.UUID(me_alice["id"])).one()
        bob_user = db.query(User).filter(User.id == uuid.UUID(me_bob["id"])).one()
        bob_user.organization_id = alice_user.organization_id
        bob_user.org_role = "member"
        db.commit()
    finally:
        db.close()

    outsider = _register_org_user(client)
    post_a = _create_post(client, alice, category="food").json()
    post_b = _create_post(client, bob, category="food").json()
    post_out = _create_post(client, outsider, category="food").json()

    # Anonymous cannot list
    assert client.get("/api/v1/posts", params={"category": "food"}).status_code in (401, 403)

    # Same-org users see each other, not outsider
    alice_feed = client.get("/api/v1/posts", params={"category": "food", "limit": 100}, headers=alice)
    assert alice_feed.status_code == 200
    alice_ids = {p["id"] for p in alice_feed.json()}
    assert {post_a["id"], post_b["id"]} <= alice_ids
    assert post_out["id"] not in alice_ids

    out_feed = client.get("/api/v1/posts", params={"category": "food", "limit": 100}, headers=outsider)
    out_ids = {p["id"] for p in out_feed.json()}
    assert post_out["id"] in out_ids
    assert post_a["id"] not in out_ids

    # Cross-org detail is hidden
    assert client.get(f"/api/v1/posts/{post_a['id']}", headers=outsider).status_code == 404
    assert client.get(f"/api/v1/posts/{post_a['id']}", headers=alice).status_code == 200


def test_cannot_post_without_organization(client):
    headers = _register_and_login(client)
    response = _create_post(client, headers)
    assert response.status_code == 403


def test_only_owner_can_edit_or_delete(client):
    org_slug = f"edit-{uuid.uuid4().hex[:6]}"
    alice = _register_org_user(client, org_slug=org_slug)
    bob = _register_and_login(client)
    me_alice = client.get("/api/v1/users/me", headers=alice).json()
    me_bob = client.get("/api/v1/users/me", headers=bob).json()
    db = TestingSessionLocal()
    try:
        alice_user = db.query(User).filter(User.id == uuid.UUID(me_alice["id"])).one()
        bob_user = db.query(User).filter(User.id == uuid.UUID(me_bob["id"])).one()
        bob_user.organization_id = alice_user.organization_id
        bob_user.org_role = "member"
        db.commit()
    finally:
        db.close()

    post = _create_post(client, alice).json()

    assert client.patch(f"/api/v1/posts/{post['id']}", json={"title": "x"}, headers=bob).status_code == 404
    assert client.delete(f"/api/v1/posts/{post['id']}", headers=bob).status_code == 404

    updated = client.patch(f"/api/v1/posts/{post['id']}", json={"title": "New"}, headers=alice)
    assert updated.status_code == 200
    assert updated.json()["title"] == "New"
    assert client.delete(f"/api/v1/posts/{post['id']}", headers=alice).status_code == 200


def test_create_requires_auth(client):
    response = client.post(
        "/api/v1/posts",
        json={"title": "t", "content": "c", "category": "food"},
    )
    assert response.status_code in (401, 403)


def test_me_and_public_profile(client):
    headers = _register_org_user(client)
    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    _create_post(client, headers)

    profile = client.get(f"/api/v1/users/{me.json()['id']}/profile")
    assert profile.status_code == 200
    body = profile.json()
    assert body["post_count"] == 1
    assert "email" not in body


def test_users_cannot_edit_other_users(client):
    alice = _register_and_login(client)
    bob = _register_and_login(client)
    bob_id = client.get("/api/v1/users/me", headers=bob).json()["id"]
    response = client.patch(f"/api/v1/users/{bob_id}", json={"full_name": "Hacked"}, headers=alice)
    assert response.status_code == 404


def test_photography_is_photos_and_optional_place_names(client):
    headers = _register_org_user(client)

    missing = _create_post(client, headers, category="photography", title="", content="", images=[])
    assert missing.status_code == 422

    created = _create_post(
        client,
        headers,
        category="photography",
        title="This headline should not be stored",
        content="This story should not be stored",
        images=[
            {"url": "https://example.com/a.jpg", "place_name": "  Hampi  "},
            "https://example.com/b.jpg",
        ],
    )
    assert created.status_code == 200
    body = created.json()
    assert body["title"] == ""
    assert body["content"] == ""
    assert body["images"][0]["place_name"] == "Hampi"
    assert body["images"][0]["image_url"] == "https://example.com/a.jpg"
    assert body["images"][1]["place_name"] is None
    assert body["images"][1]["image_url"] == "https://example.com/b.jpg"

    found = client.get("/api/v1/posts", params={"search": "Hampi"}, headers=headers)
    assert body["id"] in {post["id"] for post in found.json()}

    story = _create_post(client, headers, title=" ", content=" ")
    assert story.status_code == 422


def test_image_upload(client, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MEDIA_DIR", str(tmp_path))
    headers = _register_and_login(client)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 16

    response = client.post(
        "/api/v1/posts/images",
        content=png,
        headers={**headers, "Content-Type": "image/png"},
    )
    assert response.status_code == 201
    assert response.json()["url"].endswith(".png")

    bad = client.post(
        "/api/v1/posts/images",
        content=b"hello",
        headers={**headers, "Content-Type": "text/plain"},
    )
    assert bad.status_code == 422


def test_create_post_sanitizes_html(client):
    headers = _register_org_user(client)
    response = _create_post(
        client,
        headers,
        content="<p>Hello <strong>world</strong><script>alert(1)</script></p>",
    )
    assert response.status_code == 200
    body = response.json()
    assert "<strong>world</strong>" in body["content"]
    assert "<script>" not in body["content"].lower()
    assert "onerror" not in body["content"].lower()


def test_empty_html_story_rejected(client):
    headers = _register_org_user(client)
    response = _create_post(client, headers, content="<p><br></p>")
    assert response.status_code == 422
