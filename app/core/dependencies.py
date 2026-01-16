from __future__ import annotations

from typing import Callable, Iterable

from fastapi import Depends, HTTPException, Request


def get_current_user(request: Request) -> dict:
	user = request.session.get("user")
	if not user:
		raise HTTPException(status_code=401, detail="Authentication required")
	return user


def resolve_system_role(user: dict) -> str:
	role = str(user.get("role") or "").strip().lower()
	if role == "admin":
		return "admin"
	if role in {"engineer", "manager", "owner", "user"}:
		return "engineer"
	if role == "viewer":
		return "viewer"
	return "viewer"


def require_roles(allowed: Iterable[str]) -> Callable:
	allowed_set = {r.lower() for r in allowed}

	def _guard(user: dict = Depends(get_current_user)) -> dict:
		role = resolve_system_role(user)
		if role not in allowed_set:
			raise HTTPException(status_code=403, detail="Permission denied")
		return user

	return _guard
