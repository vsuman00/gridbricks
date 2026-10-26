class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}
