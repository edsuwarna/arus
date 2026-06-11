class ArusError(Exception):
    code = "INTERNAL_ERROR"
    status_code = 500


class AuthError(ArusError):
    code = "AUTH_FAILED"
    status_code = 401


class ForbiddenError(ArusError):
    code = "FORBIDDEN"
    status_code = 403


class NotFoundError(ArusError):
    code = "NOT_FOUND"
    status_code = 404


class ValidationError(ArusError):
    code = "VALIDATION_ERROR"
    status_code = 422


class ConnectionFailedError(ArusError):
    code = "CONNECTION_FAILED"
    status_code = 502


class DiscoveryFailedError(ArusError):
    code = "DISCOVERY_FAILED"
    status_code = 500
