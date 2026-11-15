import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.security import get_allowed_classifications
from app.models.collection import Collection
from app.models.document import Document
from app.models.user import User
from app.schemas.collections import CollectionCreate, CollectionRead, CollectionUpdate

router = APIRouter(prefix="/collections", tags=["Collections"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-")


def _to_collection_read(coll: Collection, doc_count: int = 0) -> CollectionRead:
    return CollectionRead(
        id=coll.id,
        name=coll.name,
        slug=coll.slug,
        description=coll.description,
        icon=coll.icon,
        access_classification=coll.access_classification,
        document_count=doc_count,
        created_at=coll.created_at,
        updated_at=coll.updated_at,
    )


@router.get("", response_model=list[CollectionRead])
def list_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollectionRead]:
    """List collections accessible to the current user with document counts."""
    allowed = get_allowed_classifications(current_user.role.name)

    # Subquery for document counts filtered by user classification
    doc_counts = (
        db.query(
            Document.collection_id,
            func.count(Document.id).label("doc_count"),
        )
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .group_by(Document.collection_id)
        .all()
    )
    counts_map = {cid: cnt for cid, cnt in doc_counts if cid}

    colls = (
        db.query(Collection)
        .filter(Collection.access_classification.in_(allowed))
        .order_by(Collection.name.asc())
        .all()
    )
    return [_to_collection_read(c, counts_map.get(c.id, 0)) for c in colls]


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollectionRead:
    """Retrieve details for a single collection."""
    allowed = get_allowed_classifications(current_user.role.name)
    coll = (
        db.query(Collection)
        .filter(
            Collection.id == collection_id,
            Collection.access_classification.in_(allowed),
        )
        .first()
    )
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found or access denied.")

    doc_count = (
        db.query(func.count(Document.id))
        .filter(
            Document.collection_id == coll.id,
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .scalar()
        or 0
    )
    return _to_collection_read(coll, doc_count)


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CollectionRead:
    """Create a new collection (Admin only)."""
    slug = payload.slug or _slugify(payload.name)
    existing = db.query(Collection).filter(Collection.slug == slug).first()
    if existing is not None:
        raise HTTPException(
            status_code=400,
            detail=f"A collection with slug '{slug}' already exists.",
        )

    coll = Collection(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description.strip() if payload.description else None,
        icon=payload.icon or "folder",
        access_classification=payload.access_classification or "employee",
    )
    db.add(coll)
    db.commit()
    db.refresh(coll)
    return _to_collection_read(coll, 0)


@router.patch("/{collection_id}", response_model=CollectionRead)
def update_collection(
    collection_id: str,
    payload: CollectionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> CollectionRead:
    """Update a collection (Admin only)."""
    coll = db.query(Collection).filter(Collection.id == collection_id).first()
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    if payload.name is not None:
        coll.name = payload.name.strip()
    if payload.description is not None:
        coll.description = payload.description.strip()
    if payload.icon is not None:
        coll.icon = payload.icon.strip()
    if payload.access_classification is not None:
        coll.access_classification = payload.access_classification

    db.commit()
    db.refresh(coll)

    doc_count = (
        db.query(func.count(Document.id))
        .filter(Document.collection_id == coll.id)
        .scalar()
        or 0
    )
    return _to_collection_read(coll, doc_count)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Delete a collection; associated documents become unassigned (collection_id = NULL)."""
    coll = db.query(Collection).filter(Collection.id == collection_id).first()
    if coll is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    db.delete(coll)
    db.commit()

