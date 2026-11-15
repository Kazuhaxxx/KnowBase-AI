from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, limiter
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_allowed_classifications,
    hash_password,
    verify_password,
)
from app.models.user import Role, User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _serialize_user(user: User) -> UserResponse:
    role_name = user.role.name if user.role else "employee"
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=role_name,
        is_active=user.is_active,
        allowed_classifications=get_allowed_classifications(role_name),
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_auth)
def register(
    request: Request,
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new employee account (always assigned 'employee' role server-side)."""
    normalized_email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    employee_role = db.query(Role).filter(Role.name == "employee").first()
    if employee_role is None:
        employee_role = Role(
            name="employee",
            description="Standard employee access (public and employee documents).",
        )
        db.add(employee_role)
        db.flush()

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        department=payload.department.strip(),
        password_hash=hash_password(payload.password),
        role_id=employee_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    user_loaded = (
        db.query(User).options(joinedload(User.role)).filter(User.id == user.id).one()
    )
    token = create_access_token(
        subject=user_loaded.id,
        role=user_loaded.role.name,
        email=user_loaded.email,
    )
    return TokenResponse(access_token=token, user=_serialize_user(user_loaded))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
def login(
    request: Request,
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate an existing user and issue a signed JWT bearer token."""
    normalized_email = payload.email.strip().lower()
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == normalized_email)
        .first()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator.",
        )

    token = create_access_token(
        subject=user.id,
        role=user.role.name,
        email=user.email,
    )
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile and permitted document classifications."""
    return _serialize_user(current_user)

