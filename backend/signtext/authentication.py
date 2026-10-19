from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class LenientTokenAuthentication(TokenAuthentication):
    """TokenAuthentication that treats a stale/unknown token as anonymous.

    The frontend keeps its token in localStorage and attaches it to every
    request, so a token that no longer exists server-side (deleted on
    logout elsewhere, database restored, user deactivated) would otherwise
    make DRF reject *every* request with "Invalid token." -- including the
    public login, signup and Google sign-in endpoints, locking the user out
    until they clear site data. Falling through to anonymous instead lets
    those endpoints work and issue a fresh token, while views that require
    a login still answer 401 via IsAuthenticated.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
