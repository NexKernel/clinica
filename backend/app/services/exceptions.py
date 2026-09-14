class AppError(Exception):
    """Error de negocio con mensaje apto para el usuario final."""

    message = "No se pudo completar la operación"


class AuthError(AppError):
    """Error base de autenticación."""

    message = "Error de autenticación"


class InvalidCredentialsError(AuthError):
    message = "Usuario o contraseña incorrectos"


class InactiveUserError(AuthError):
    message = "El usuario se encuentra inactivo"


class InvalidCurrentPasswordError(AuthError):
    message = "La contraseña actual no es correcta"


class ConflictError(AppError):
    """Un valor único ya está en uso por otro registro."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """El recurso solicitado no existe."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BusinessRuleError(AppError):
    """Regla de negocio incumplida."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
