"""
Tests for AuthService — token creation/verification, authenticate_user,
refresh, logout, session management, RBAC permission enforcement.
"""
import secrets
import sys
import pytest
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, call

_ussop_dir = Path(__file__).parent.parent
_project_root = _ussop_dir.parent
for _p in (_ussop_dir, _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_user(active=True, superuser=False, permissions="inspect,view_history"):
    u = MagicMock()
    u.id = "user-abc"
    u.username = "testuser"
    u.email = "test@factory.com"
    u.is_active = active
    u.is_superuser = superuser
    u.verify_password = MagicMock(return_value=True)
    u.login_count = 0
    u.last_login = None
    u.to_dict = MagicMock(return_value={"id": "user-abc", "username": "testuser"})
    # has_permission checks roles
    role = MagicMock()
    role.permissions = permissions
    u.roles = [role]
    u.has_permission = MagicMock(
        side_effect=lambda p: (superuser or p in permissions.split(","))
    )
    return u


def _make_session(user_id="user-abc", active=True):
    s = MagicMock()
    s.id = "sess-xyz"
    s.user_id = user_id
    s.is_active = active
    s.is_valid = MagicMock(return_value=active)
    s.user = _make_user()
    s.access_token_jti = ""
    s.refresh_token_jti = ""
    s.revoke = MagicMock()
    return s


def _auth():
    from services.auth_service import AuthService
    return AuthService()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Token creation & verification
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenCreation:
    def test_create_access_token_returns_tuple(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        assert isinstance(token, str) and len(token) > 10
        assert isinstance(jti, str) and len(jti) > 0

    def test_access_token_verifies(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        payload = svc.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"

    def test_access_token_type_is_access(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        payload = svc.verify_token(token)
        assert payload["type"] == "access"

    def test_access_token_has_jti(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        payload = svc.verify_token(token)
        assert payload["jti"] == jti

    def test_access_token_has_sid(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        payload = svc.verify_token(token)
        assert payload["sid"] == "sess-1"

    def test_expired_token_returns_none(self):
        svc = _auth()
        token, _ = svc.create_access_token(
            "user-1", "sess-1", expires_delta=timedelta(seconds=-1)
        )
        assert svc.verify_token(token) is None

    def test_garbage_token_returns_none(self):
        svc = _auth()
        assert svc.verify_token("not.a.valid.token") is None

    def test_empty_token_returns_none(self):
        svc = _auth()
        assert svc.verify_token("") is None

    def test_create_refresh_token_type_is_refresh(self):
        svc = _auth()
        token, _ = svc.create_refresh_token("user-1", "sess-1")
        payload = svc.verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_refresh_token_rejected_as_access(self):
        svc = _auth()
        token, _ = svc.create_refresh_token("user-1", "sess-1")
        assert svc.verify_token(token, token_type="access") is None

    def test_access_token_rejected_as_refresh(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        assert svc.verify_token(token, token_type="refresh") is None

    def test_tokens_are_unique(self):
        svc = _auth()
        t1, j1 = svc.create_access_token("user-1", "sess-1")
        t2, j2 = svc.create_access_token("user-1", "sess-1")
        assert t1 != t2
        assert j1 != j2


# ══════════════════════════════════════════════════════════════════════════════
# 2. authenticate_user
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthenticateUser:
    def _db_with_user(self, user):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        db.add = MagicMock()
        db.flush = MagicMock()
        db.commit = MagicMock()
        return db

    def test_valid_credentials_returns_tokens(self):
        svc = _auth()
        db = self._db_with_user(_make_user())
        result = svc.authenticate_user(db, "testuser", "correct")
        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    def test_wrong_password_returns_none(self):
        svc = _auth()
        user = _make_user()
        user.verify_password.return_value = False
        db = self._db_with_user(user)
        assert svc.authenticate_user(db, "testuser", "wrong") is None

    def test_unknown_user_returns_none(self):
        svc = _auth()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert svc.authenticate_user(db, "ghost", "pass") is None

    def test_inactive_user_returns_none(self):
        svc = _auth()
        db = self._db_with_user(_make_user(active=False))
        assert svc.authenticate_user(db, "testuser", "pass") is None

    def test_login_increments_login_count(self):
        svc = _auth()
        user = _make_user()
        user.login_count = 5
        db = self._db_with_user(user)
        svc.authenticate_user(db, "testuser", "pass")
        assert user.login_count == 6

    def test_login_updates_last_login(self):
        svc = _auth()
        user = _make_user()
        user.last_login = None
        db = self._db_with_user(user)
        svc.authenticate_user(db, "testuser", "pass")
        assert user.last_login is not None

    def test_login_commits_db(self):
        svc = _auth()
        db = self._db_with_user(_make_user())
        svc.authenticate_user(db, "testuser", "pass")
        db.commit.assert_called()

    def test_result_contains_user_dict(self):
        svc = _auth()
        db = self._db_with_user(_make_user())
        result = svc.authenticate_user(db, "testuser", "pass")
        assert "user" in result
        assert result["user"]["username"] == "testuser"

    def test_result_contains_expires_in(self):
        svc = _auth()
        db = self._db_with_user(_make_user())
        result = svc.authenticate_user(db, "testuser", "pass")
        assert "expires_in" in result
        assert result["expires_in"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. refresh_access_token
# ══════════════════════════════════════════════════════════════════════════════

class TestRefreshToken:
    def test_valid_refresh_returns_new_access_token(self):
        svc = _auth()
        refresh_token, refresh_jti = svc.create_refresh_token("user-1", "sess-1")

        session = _make_session()
        session.refresh_token_jti = refresh_jti
        session.user_id = "user-1"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session

        result = svc.refresh_access_token(db, refresh_token)
        assert result is not None
        assert "access_token" in result

    def test_invalid_refresh_token_returns_none(self):
        svc = _auth()
        db = MagicMock()
        assert svc.refresh_access_token(db, "garbage.token.here") is None

    def test_expired_refresh_token_returns_none(self):
        svc = _auth()
        token, _ = svc.create_refresh_token.__func__(
            svc, "user-1", "sess-1"
        ) if False else (None, None)
        # Directly create expired refresh token via jose
        from jose import jwt
        from datetime import datetime, timezone
        import services.auth_service as auth_mod
        payload = {
            "sub": "user-1", "jti": "test-jti", "sid": "sess-1",
            "exp": datetime(2000, 1, 1),
            "iat": datetime(2000, 1, 1),
            "type": "refresh"
        }
        expired = jwt.encode(payload, auth_mod.SECRET_KEY, algorithm=auth_mod.ALGORITHM)
        db = MagicMock()
        result = svc.refresh_access_token(db, expired)
        assert result is None

    def test_no_matching_session_returns_none(self):
        svc = _auth()
        refresh_token, _ = svc.create_refresh_token("user-1", "sess-1")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert svc.refresh_access_token(db, refresh_token) is None

    def test_revoked_session_returns_none(self):
        svc = _auth()
        refresh_token, refresh_jti = svc.create_refresh_token("user-1", "sess-1")
        session = _make_session(active=False)
        session.refresh_token_jti = refresh_jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        assert svc.refresh_access_token(db, refresh_token) is None


# ══════════════════════════════════════════════════════════════════════════════
# 4. logout / session revocation
# ══════════════════════════════════════════════════════════════════════════════

class TestLogout:
    def test_logout_valid_token_returns_true(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")

        session = _make_session()
        session.access_token_jti = jti

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session

        result = svc.logout(db, token)
        assert result is True

    def test_logout_calls_revoke(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        session = _make_session()
        session.access_token_jti = jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        svc.logout(db, token)
        session.revoke.assert_called_once()

    def test_logout_invalid_token_returns_false(self):
        svc = _auth()
        db = MagicMock()
        assert svc.logout(db, "bad.token") is False

    def test_logout_no_session_returns_false(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert svc.logout(db, token) is False

    def test_logout_commits_db(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        session = _make_session()
        session.access_token_jti = jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        svc.logout(db, token)
        db.commit.assert_called()


# ══════════════════════════════════════════════════════════════════════════════
# 5. get_current_user
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCurrentUser:
    def test_valid_token_returns_user(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        session = _make_session()
        session.access_token_jti = jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        user = svc.get_current_user(db, token)
        assert user is session.user

    def test_invalid_token_returns_none(self):
        svc = _auth()
        db = MagicMock()
        assert svc.get_current_user(db, "garbage") is None

    def test_no_session_returns_none(self):
        svc = _auth()
        token, _ = svc.create_access_token("user-1", "sess-1")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        assert svc.get_current_user(db, token) is None

    def test_revoked_session_returns_none(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        session = _make_session(active=False)
        session.access_token_jti = jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        assert svc.get_current_user(db, token) is None

    def test_updates_last_used(self):
        svc = _auth()
        token, jti = svc.create_access_token("user-1", "sess-1")
        session = _make_session()
        session.access_token_jti = jti
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = session
        svc.get_current_user(db, token)
        assert session.last_used_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# 6. RBAC — has_permission
# ══════════════════════════════════════════════════════════════════════════════

class TestRBAC:
    def test_user_with_permission_passes(self):
        user = _make_user(permissions="inspect,view_history")
        assert user.has_permission("inspect") is True

    def test_user_without_permission_fails(self):
        user = _make_user(permissions="inspect")
        assert user.has_permission("manage_users") is False

    def test_superuser_passes_all_permissions(self):
        user = _make_user(superuser=True, permissions="")
        assert user.has_permission("manage_users") is True
        assert user.has_permission("configure") is True

    def test_multiple_permissions(self):
        user = _make_user(permissions="inspect,configure,view_history")
        assert user.has_permission("inspect") is True
        assert user.has_permission("configure") is True
        assert user.has_permission("manage_users") is False

    def test_viewer_has_no_inspect(self):
        user = _make_user(permissions="view_history")
        assert user.has_permission("inspect") is False

    def test_require_permission_raises_403_on_missing(self):
        from fastapi import HTTPException
        from services.auth_service import require_permission

        user = _make_user(permissions="inspect")
        dep_fn = require_permission("manage_users")

        with pytest.raises(HTTPException) as exc_info:
            dep_fn(current_user=user)
        assert exc_info.value.status_code == 403

    def test_require_permission_returns_user_on_match(self):
        from services.auth_service import require_permission

        user = _make_user(permissions="inspect,configure")
        dep_fn = require_permission("configure")
        result = dep_fn(current_user=user)
        assert result is user


# ══════════════════════════════════════════════════════════════════════════════
# 7. RBAC role definitions (source-level check)
# ══════════════════════════════════════════════════════════════════════════════

class TestRoleDefinitions:
    _SRC = (Path(__file__).parent.parent / "models" / "auth.py").read_text()

    def test_four_default_roles_defined(self):
        for role in ("admin", "operator", "viewer", "engineer"):
            assert f'"{role}"' in self._SRC

    def test_inspect_permission_defined(self):
        assert '"inspect"' in self._SRC

    def test_configure_permission_defined(self):
        assert '"configure"' in self._SRC

    def test_manage_users_permission_defined(self):
        assert '"manage_users"' in self._SRC

    def test_viewer_lacks_manage_users(self):
        viewer_idx = self._SRC.find('"viewer"')
        engineer_idx = self._SRC.find('"engineer"')
        section = self._SRC[viewer_idx:engineer_idx] if viewer_idx < engineer_idx else self._SRC[viewer_idx:]
        assert "manage_users" not in section

    def test_admin_defined_before_operator(self):
        assert self._SRC.find('"admin"') < self._SRC.find('"operator"')
