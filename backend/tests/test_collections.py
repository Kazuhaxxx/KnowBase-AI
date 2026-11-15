from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.seed_service import ensure_default_collections
from tests.conftest import auth_headers


def test_collections_crud_and_scoping(client: TestClient, test_db) -> None:
    settings = get_settings()
    emp_headers = auth_headers(client, settings.demo_employee_email, settings.demo_employee_password)
    admin_headers = auth_headers(client, settings.demo_admin_email, settings.demo_admin_password)

    # 1. Ensure default collections exist
    ensure_default_collections(test_db)

    # 2. List collections as employee
    resp = client.get("/api/collections", headers=emp_headers)
    assert resp.status_code == 200
    colls = resp.json()
    assert len(colls) >= 2
    slugs = {c["slug"] for c in colls}
    assert "general-knowledge" in slugs
    assert "it-support" in slugs

    # 3. Employee cannot create collections (403 forbidden)
    emp_create = client.post(
        "/api/collections",
        headers=emp_headers,
        json={"name": "HR Handbooks", "slug": "hr-handbooks"},
    )
    assert emp_create.status_code == 403

    # 4. Admin creates new collection
    admin_create = client.post(
        "/api/collections",
        headers=admin_headers,
        json={
            "name": "HR Handbooks & Policies",
            "slug": "hr-handbooks",
            "description": "Standard company benefits and employee onboarding policies.",
            "icon": "book-open",
            "access_classification": "employee",
        },
    )
    assert admin_create.status_code == 201
    created_data = admin_create.json()
    coll_id = created_data["id"]
    assert created_data["slug"] == "hr-handbooks"

    # 5. Admin uploads a document assigned to this collection
    doc_content = b"# Remote Work Policy\nEmployees may work remotely up to 3 days per week with manager approval."
    upload_resp = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        data={
            "title": "Corporate Remote Work Policy 2026",
            "category": "Company Policies",
            "department": "People Operations",
            "access_classification": "employee",
            "collection_id": coll_id,
        },
        files={"files": ("remote_work_policy.md", doc_content, "text/markdown")},
    )
    assert upload_resp.status_code == 201
    uploaded_doc = upload_resp.json()[0]["document"]
    assert uploaded_doc["collection_id"] == coll_id

    # 6. Filter search by this collection_id
    search_resp = client.get(
        f"/api/knowledge/search?q=remote+work&collection_id={coll_id}",
        headers=emp_headers,
    )
    assert search_resp.status_code == 200
    hits = search_resp.json()
    assert len(hits) >= 1
    assert hits[0]["document_id"] == uploaded_doc["id"]
