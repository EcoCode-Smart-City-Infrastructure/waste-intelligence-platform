"""Authentication and role-based authorization for WIN OS.

V1 uses API keys mapped to (role, organization) principals, configured only
through the WIN_OS_KEYS environment variable in the form:
    key:role:org_id,key2:role:org_id
Passwords are never handled here. A future OIDC/JWT adapter can replace
`authenticate` without changing the permission checks (see ADR-007 addendum
in docs/architecture/adr-011-win-os-foundation.md).
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from fastapi import Header, HTTPException

ROLES = ("platform_admin", "org_admin", "operations_manager",
         "analyst", "operator", "viewer", "integration")

PERMISSIONS = {
    "platform_admin": {"*"},
    "org_admin": {"read", "write", "admin", "ingest", "plan", "analyse"},
    "operations_manager": {"read", "write", "plan", "analyse"},
    "analyst": {"read", "analyse"},
    "operator": {"read", "write"},
    "viewer": {"read"},
    "integration": {"ingest", "read"},
}

@dataclass(frozen=True)
class Principal:
    key_id: str
    role: str
    org_id: str

    def can(self, permission: str) -> bool:
        perms = PERMISSIONS.get(self.role, set())
        return "*" in perms or permission in perms

def load_principals() -> dict:
    raw = os.environ.get("WIN_OS_KEYS", "")
    out = {}
    for i, part in enumerate(p for p in raw.split(",") if p.strip()):
        bits = part.strip().split(":")
        if len(bits) != 3 or bits[1] not in ROLES:
            continue  # skip malformed entries; never guess a role
        key, role, org = bits
        out[key] = Principal(key_id=f"key-{i}", role=role, org_id=org)
    return out

def auth_configured() -> bool:
    return bool(load_principals())

def authenticate(x_api_key: str = Header(default="")) -> Principal:
    principals = load_principals()
    principal = principals.get(x_api_key)
    if principal is None:
        raise HTTPException(status_code=401, detail={
            "error": "unauthorized",
            "message": "Missing or invalid API key. Configure WIN_OS_KEYS on the server."})
    return principal

def require(principal: Principal, permission: str) -> Principal:
    if not principal.can(permission):
        raise HTTPException(status_code=403, detail={
            "error": "forbidden",
            "message": f"Role {principal.role} lacks permission '{permission}'."})
    return principal
