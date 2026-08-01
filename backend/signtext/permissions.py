from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .models import UserProfile


def session_exception_handler(exc, context):
    """Wrap DRF's default exception handler to give 401/403 a consistent,
    predictable JSON shape so the frontend can distinguish "please log back
    in" (401) from "you're logged in but not allowed" (403) from any
    endpoint, not just /auth/me/.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        response.data = {"authenticated": False, "error": str(exc.detail)}
        response.status_code = 401
    elif isinstance(exc, PermissionDenied):
        response.data = {"authenticated": True, "error": str(exc.detail)}

    return response


def get_profile_or_403(user) -> UserProfile:
    """Resolve the UserProfile for an authenticated request.user.

    Raises the same DRF exceptions the permission classes below use, so
    callers get consistent 401/403 semantics whether the check happens in
    has_permission() or inline in a view body.
    """
    if not user or not user.is_authenticated:
        raise AuthenticationFailed("Authentication required")
    profile = getattr(user, "profile", None)
    if profile is None:
        profile = UserProfile.objects.create(
            user=user,
            full_name=user.first_name or user.username.split("@")[0],
            role="student",
        )
    return profile


class HasRole(BasePermission):
    """Base permission: require an authenticated, active session user whose
    UserProfile.role is one of `allowed_roles`. Subclass and set
    `allowed_roles` (or use the concrete IsStudent/IsInstructor/IsAdmin/
    IsInstructorOrAdmin classes below).
    """

    allowed_roles: frozenset[str] = frozenset()
    message = "You do not have permission to access this resource."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed("Authentication required")

        profile = getattr(request.user, "profile", None)
        if profile is None:
            profile = UserProfile.objects.create(
                user=request.user,
                full_name=request.user.first_name or request.user.username.split("@")[0],
                role="student",
            )

        role = str(profile.role or "").lower()
        if role not in self.allowed_roles:
            raise PermissionDenied("You do not have permission to access this resource.")

        # 0 = active, 1 = inactive (see UserProfile.active)
        if getattr(profile, "active", 0) == 1:
            raise PermissionDenied("Account is inactive")

        return True


class IsStudent(HasRole):
    allowed_roles = frozenset({"student"})


class IsInstructor(HasRole):
    allowed_roles = frozenset({"instructor"})


class IsAdmin(HasRole):
    allowed_roles = frozenset({"admin"})


class IsInstructorOrAdmin(HasRole):
    allowed_roles = frozenset({"instructor", "admin"})
