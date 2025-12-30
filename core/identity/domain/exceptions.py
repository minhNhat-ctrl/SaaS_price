"""
Domain exceptions for Identity module (no Django imports).
"""

class IdentityError(Exception):
    pass


class InvalidEmailError(IdentityError):
    def __init__(self, email: str):
        super().__init__(f"Invalid email: {email}")


class InvalidCredentialError(IdentityError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class IdentityNotFoundError(IdentityError):
    def __init__(self, email: str):
        super().__init__(f"Identity not found for email: {email}")


class IdentityAlreadyExistsError(IdentityError):
    def __init__(self, email: str):
        super().__init__(f"Identity already exists for email: {email}")
