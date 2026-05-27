"""
Shared fixtures for all tests.

Uses an in-memory SQLite database so tests are fast and fully isolated.
Each test function gets a fresh database via function-scoped fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.models.role import Role, RoleKey
from app.models.user import User, UserStatus
from app.core.security import hash_password, create_access_token

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def db(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def client(db):
    """TestClient with the DB dependency overridden to use the test DB."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def seeded_roles(db):
    """Create the two default roles and return them as a dict."""
    user_role = Role(name="User", key=RoleKey.USER)
    admin_role = Role(name="Super Admin", key=RoleKey.SUPER_ADMIN)
    db.add_all([user_role, admin_role])
    db.commit()
    db.refresh(user_role)
    db.refresh(admin_role)
    return {RoleKey.USER: user_role, RoleKey.SUPER_ADMIN: admin_role}


@pytest.fixture(scope="function")
def regular_user(db, seeded_roles):
    """An active, verified regular user."""
    user = User(
        name="Test User",
        email="user@example.com",
        hashed_password=hash_password("password123"),
        status=UserStatus.ACTIVE,
        role_id=seeded_roles[RoleKey.USER].id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(db, seeded_roles):
    """An active super admin user."""
    user = User(
        name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("adminpass123"),
        status=UserStatus.ACTIVE,
        role_id=seeded_roles[RoleKey.SUPER_ADMIN].id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def user_token(regular_user):
    return create_access_token(subject=regular_user.id)


@pytest.fixture(scope="function")
def admin_token(admin_user):
    return create_access_token(subject=admin_user.id)


@pytest.fixture(scope="function")
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="function")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
