from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import auth_headers


def test_register_and_login_flow(client: TestClient):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "new.hire@novatech-demo.internal",
            "full_name": "Samira Patel",
            "department": "Finance",
            "password": "StrongPassword!123",
        },
    )
    assert reg.status_code == 201
    data = reg.json()
    assert data["user"]["role"] == "employee"
    assert set(data["user"]["allowed_classifications"]) == {"public", "employee"}

    # Duplicate email returns 409
    dup = client.post(
        "/api/auth/register",
        json={
            "email": "new.hire@novatech-demo.internal",
            "full_name": "Samira Patel",
            "department": "Finance",
            "password": "StrongPassword!123",
        },
    )
    assert dup.status_code == 409

    # Wrong password rejected
    bad = client.post(
        "/api/auth/login",
        json={"email": "new.hire@novatech-demo.internal", "password": "wrong"},
    )
    assert bad.status_code == 401


def test_employee_cannot_access_admin_endpoints(client: TestClient):
    settings = get_settings()
    emp_headers = auth_headers(client, settings.demo_employee_email, settings.demo_employee_password)
    admin_headers = auth_headers(client, settings.demo_admin_email, settings.demo_admin_password)

    assert client.get("/api/documents", headers=emp_headers).status_code == 403
    assert client.get("/api/admin/overview", headers=emp_headers).status_code == 403
    assert client.get("/api/admin/users", headers=emp_headers).status_code == 403
    assert client.get("/api/admin/config", headers=emp_headers).status_code == 403

    assert client.get("/api/admin/overview", headers=admin_headers).status_code == 200
    assert client.get("/api/admin/config", headers=admin_headers).status_code == 200


def test_document_access_isolation_by_role(client: TestClient):
    settings = get_settings()
    admin_headers = auth_headers(client, settings.demo_admin_email, settings.demo_admin_password)
    emp_headers = auth_headers(client, settings.demo_employee_email, settings.demo_employee_password)
    it_headers = auth_headers(client, settings.demo_it_email, settings.demo_it_password)

    # Upload public, it_only, and restricted docs
    docs_to_upload = [
        ("public_guide.md", b"# Public WiFi Guide\nConnect to NovaTech-Corp Wi-Fi.", "public"),
        ("it_playbook.md", b"# IT BitLocker Playbook\nRetrieve 48-digit BitLocker key in Intune.", "it_only"),
        ("secops_vault.md", b"# Restricted Vault\nBreak-glass HSM vault SecOps-Tier0-Alpha.", "restricted"),
    ]
    uploaded_ids = {}
    for fname, content, classification in docs_to_upload:
        resp = client.post(
            "/api/documents/upload",
            headers=admin_headers,
            files={"files": (fname, content, "text/markdown")},
            data={
                "category": "Account and Access",
                "department": "IT",
                "access_classification": classification,
            },
        )
        assert resp.status_code == 201, resp.text
        uploaded_ids[classification] = resp.json()[0]["document"]["id"]

    # Employee sees only public/employee, NEVER it_only or restricted
    emp_docs = client.get("/api/knowledge/documents", headers=emp_headers).json()
    emp_ids = {d["id"] for d in emp_docs}
    assert uploaded_ids["public"] in emp_ids
    assert uploaded_ids["it_only"] not in emp_ids
    assert uploaded_ids["restricted"] not in emp_ids

    # Direct ID fetch on restricted/it_only must return 404 for employee
    assert client.get(f"/api/knowledge/documents/{uploaded_ids['restricted']}", headers=emp_headers).status_code == 404
    assert client.get(f"/api/knowledge/documents/{uploaded_ids['it_only']}", headers=emp_headers).status_code == 404

    # Search must never leak restricted or it_only chunks to employee
    search_hits = client.get(
        "/api/knowledge/search?q=SecOps-Tier0-Alpha+BitLocker+Intune",
        headers=emp_headers,
    ).json()
    hit_doc_ids = {h["document_id"] for h in search_hits}
    assert uploaded_ids["restricted"] not in hit_doc_ids
    assert uploaded_ids["it_only"] not in hit_doc_ids

    # IT staff sees it_only but NOT restricted
    it_docs = client.get("/api/knowledge/documents", headers=it_headers).json()
    it_ids = {d["id"] for d in it_docs}
    assert uploaded_ids["it_only"] in it_ids
    assert uploaded_ids["restricted"] not in it_ids

