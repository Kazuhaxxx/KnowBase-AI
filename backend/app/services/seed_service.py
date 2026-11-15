import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.collection import Collection
from app.models.document import Document
from app.models.user import Role, User
from app.services.embeddings.provider import EmbeddingService
from app.services.ingestion.pipeline import ingest_uploaded_document

logger = logging.getLogger("helpdesk_ai.seed")

SAMPLE_DOCS_MANIFEST = [
    {
        "filename": "m365_troubleshooting_guide.md",
        "title": "Microsoft 365 & Teams Troubleshooting Guide",
        "category": "Microsoft 365",
        "department": "End User Computing",
        "access_classification": "employee",
    },
    {
        "filename": "outlook_configuration_and_sync.md",
        "title": "Outlook Profile Configuration & OST Sync Repair",
        "category": "Microsoft 365",
        "department": "Messaging & Collaboration",
        "access_classification": "employee",
    },
    {
        "filename": "vpn_connection_troubleshooting.md",
        "title": "NovaPulse Enterprise VPN Connection Guide",
        "category": "VPN",
        "department": "Network Engineering",
        "access_classification": "employee",
    },
    {
        "filename": "windows_os_support_procedures.md",
        "title": "Windows 11 Enterprise Support & Recovery Procedures",
        "category": "Troubleshooting",
        "department": "End User Computing",
        "access_classification": "employee",
    },
    {
        "filename": "printer_troubleshooting_manual.md",
        "title": "Follow-Me Print & Office Printer Troubleshooting",
        "category": "Hardware",
        "department": "Workplace Services",
        "access_classification": "public",
    },
    {
        "filename": "network_connectivity_and_wifi.md",
        "title": "Corporate Wi-Fi, Ethernet & DNS Connectivity Guide",
        "category": "Network",
        "department": "Network Engineering",
        "access_classification": "employee",
    },
    {
        "filename": "password_and_mfa_access.md",
        "title": "Account Unlock, Password Reset & MFA Enrollment",
        "category": "Account and Access",
        "department": "Identity & Access Management",
        "access_classification": "public",
    },
    {
        "filename": "software_installation_guidelines.md",
        "title": "Approved Software Catalog & Installation Guidelines",
        "category": "Software",
        "department": "IT Security & Compliance",
        "access_classification": "employee",
    },
    {
        "filename": "hardware_troubleshooting_and_rma.md",
        "title": "Laptop Docking Station, Battery & Hardware RMA Guide",
        "category": "Hardware",
        "department": "Workplace Services",
        "access_classification": "employee",
    },
    {
        "filename": "general_it_support_policies.md",
        "title": "NovaTech General IT Support & SLA Policy",
        "category": "IT Policies",
        "department": "IT Service Desk",
        "access_classification": "public",
    },
    {
        "filename": "restricted_incident_response_runbook.md",
        "title": "RESTRICTED: Privileged AD & Security Incident Runbook",
        "category": "Account and Access",
        "department": "SecOps & Infrastructure",
        "access_classification": "restricted",
    },
    {
        "filename": "it_only_intune_autopilot_playbook.md",
        "title": "IT Staff Playbook: Intune Autopilot & BitLocker Recovery",
        "category": "General IT Support",
        "department": "IT Operations",
        "access_classification": "it_only",
    },
    {
        "filename": "unrelated_office_cafeteria_menu.md",
        "title": "Campus Bistro Weekly Menu & Catering Schedule",
        "category": "General IT Support",
        "department": "Facilities",
        "access_classification": "public",
    },
    {
        "filename": "unrelated_sustainability_commute_program.md",
        "title": "Green Commute Bike & Transit Subsidy Program",
        "category": "General IT Support",
        "department": "People Operations",
        "access_classification": "public",
    },
]


DEFAULT_COLLECTIONS = [
    {
        "name": "IT Support & Troubleshooting",
        "slug": "it-support",
        "description": "Technical troubleshooting guides, network configurations, M365, and IT support playbooks.",
        "icon": "wrench",
        "access_classification": "employee",
    },
    {
        "name": "Policies & Procedures",
        "slug": "company-policies",
        "description": "Company policies, standard operating procedures, remote work guidelines, and compliance.",
        "icon": "book-open",
        "access_classification": "employee",
    },
    {
        "name": "General Knowledge",
        "slug": "general-knowledge",
        "description": "Cross-functional resources, workplace guidelines, facilities, and general employee information.",
        "icon": "folder",
        "access_classification": "public",
    },
]


def ensure_default_collections(db: Session) -> dict[str, Collection]:
    """Ensure standard initial collections exist and return lookup dict by slug."""
    collections: dict[str, Collection] = {}
    for item in DEFAULT_COLLECTIONS:
        coll = db.query(Collection).filter(Collection.slug == item["slug"]).first()
        if coll is None:
            coll = Collection(
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                icon=item["icon"],
                access_classification=item["access_classification"],
            )
            db.add(coll)
            db.flush()
        collections[item["slug"]] = coll
    db.commit()
    return collections


def ensure_roles_and_demo_users(db: Session) -> dict[str, User]:
    """Create default roles and demo user accounts idempotently."""
    settings = get_settings()
    role_defs = {
        "employee": "Standard employee access (public and employee documents).",
        "it_staff": "IT Service Desk technician (public, employee, and it_only documents).",
        "admin": "System administrator (full document and platform management).",
    }
    roles: dict[str, Role] = {}
    for name, desc in role_defs.items():
        role = db.query(Role).filter(Role.name == name).first()
        if role is None:
            role = Role(name=name, description=desc)
            db.add(role)
            db.flush()
        roles[name] = role

    demo_accounts = [
        (
            "admin",
            settings.demo_admin_email,
            "Morgan Vance (IT Admin)",
            "IT Operations",
            settings.demo_admin_password,
        ),
        (
            "it_staff",
            settings.demo_it_email,
            "Jordan Lee (IT Specialist)",
            "IT Service Desk",
            settings.demo_it_password,
        ),
        (
            "employee",
            settings.demo_employee_email,
            "Alex Rivera (Employee)",
            "Product Engineering",
            settings.demo_employee_password,
        ),
    ]

    users: dict[str, User] = {}
    for role_name, email, full_name, dept, password in demo_accounts:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                department=dept,
                password_hash=hash_password(password),
                role_id=roles[role_name].id,
                is_active=True,
            )
            db.add(user)
            db.flush()
        users[role_name] = user

    db.commit()
    return users


def seed_sample_documents(
    db: Session,
    admin_user_id: Optional[str],
    sample_dir: Optional[Path] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> int:
    """Ingest synthetic knowledge base documents if not already indexed."""
    collections = ensure_default_collections(db)

    # Backfill collection_id on existing documents if null
    unassigned_docs = db.query(Document).filter(Document.collection_id.is_(None)).all()
    if unassigned_docs:
        it_coll = collections.get("it-support")
        gen_coll = collections.get("general-knowledge")
        for d in unassigned_docs:
            if "unrelated" in d.original_filename or d.department in ["Facilities", "People Operations"]:
                d.collection_id = gen_coll.id if gen_coll else None
            else:
                d.collection_id = it_coll.id if it_coll else None
        db.commit()

    docs_dir = sample_dir or (Path(__file__).resolve().parents[3] / "data" / "sample_documents")
    if not docs_dir.exists():
        logger.warning("Sample documents directory not found at %s", docs_dir)
        return 0

    existing_count = db.query(Document).count()
    if existing_count >= len(SAMPLE_DOCS_MANIFEST):
        return 0

    ingested = 0
    for item in SAMPLE_DOCS_MANIFEST:
        file_path = docs_dir / item["filename"]
        if not file_path.exists():
            logger.warning("Missing sample doc: %s", file_path)
            continue
        existing = (
            db.query(Document)
            .filter(Document.original_filename == item["filename"])
            .first()
        )
        if existing is not None:
            continue

        coll_slug = "it-support"
        if "unrelated" in item["filename"] or item.get("department") in ["Facilities", "People Operations"]:
            coll_slug = "general-knowledge"
        elif item.get("category") == "IT Policies":
            coll_slug = "company-policies"
        coll = collections.get(coll_slug)
        coll_id = coll.id if coll else None

        content = file_path.read_bytes()
        ingest_uploaded_document(
            db=db,
            filename=item["filename"],
            content=content,
            title=item["title"],
            category=item["category"],
            department=item["department"],
            access_classification=item["access_classification"],
            uploaded_by_user_id=admin_user_id,
            embedding_service=embedding_service,
            collection_id=coll_id,
        )
        ingested += 1

    logger.info("Seeded %d synthetic IT knowledge documents.", ingested)
    return ingested

