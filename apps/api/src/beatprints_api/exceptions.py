class AppError(Exception):
    """可安全返回给 API 调用方的应用异常。"""

    def __init__(self, status_code: int, message: str, code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code if code is not None else status_code
        self.message = message


class InvalidInputError(AppError):
    def __init__(self, message: str):
        super().__init__(status_code=422, code=42200, message=message)


class UpstreamServiceError(AppError):
    def __init__(self, message: str, *, unavailable: bool = False):
        status_code = 503 if unavailable else 502
        super().__init__(
            status_code=status_code,
            code=status_code * 100,
            message=message,
        )


class UpstreamError(RuntimeError):
    """Raised when an upstream catalog, lyrics, or artwork service fails."""


class PlatformLinkNoMatchError(UpstreamError):
    """Raised when a public destination link cannot be resolved."""


class UnsupportedDestinationError(ValueError):
    """Raised when a disabled or unknown destination is requested."""
