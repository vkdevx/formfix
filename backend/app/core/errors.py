from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.redaction import mask_text

class FormFixException(Exception):
    def __init__(self, code: str, message: str, hint: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.hint = hint
        self.status_code = status_code
        super().__init__(self.message)

# Backwards compatibility alias
FormSaathiException = FormFixException

class AuthenticationError(FormFixException):
    def __init__(self, message: str = "Invalid or expired session", hint: str = "Please log in again"):
        super().__init__(code="AUTH_INVALID_SESSION", message=message, hint=hint, status_code=401)

class ConsentRequiredError(FormFixException):
    def __init__(self, message: str = "Consent must be accepted before performing this action", hint: str = "Accept DPDP consent via POST /api/v1/consent"):
        super().__init__(code="CONSENT_REQUIRED", message=message, hint=hint, status_code=403)

class NotFoundError(FormFixException):
    def __init__(self, message: str = "Resource not found", hint: str = "Check the requested identifier"):
        super().__init__(code="RESOURCE_NOT_FOUND", message=message, hint=hint, status_code=404)

class ValidationError(FormFixException):
    def __init__(self, message: str, hint: str = "Verify input format"):
        super().__init__(code="VALIDATION_FAILED", message=message, hint=hint, status_code=422)

class RateLimitError(FormFixException):
    def __init__(self, message: str = "Too many requests. Please try again later.", hint: str = "Wait for cooldown to expire"):
        super().__init__(code="RATE_LIMIT_EXCEEDED", message=message, hint=hint, status_code=429)

class ForbiddenError(FormFixException):
    def __init__(self, message: str = "Access denied", hint: str = "Insufficient permissions for this action"):
        super().__init__(code="FORBIDDEN", message=message, hint=hint, status_code=403)


async def formfix_exception_handler(request: Request, exc: FormFixException) -> JSONResponse:
    # Ensure error messages never leak raw sensitive data
    safe_message = mask_text(exc.message)
    safe_hint = mask_text(exc.hint)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": safe_message,
            "hint": safe_hint
        }
    )

formsaathi_exception_handler = formfix_exception_handler

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    safe_detail = mask_text(str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": safe_detail,
            "hint": "Check the API documentation or retry"
        }
    )
