from typing import Optional


class CriblHealthCheckError(Exception):
    base_exception = True

    def __init__(
        self, message: str, error_code: Optional[str] = None, context: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class APIConnectionError(CriblHealthCheckError):
    status_code: Optional[int] = None

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        context: Optional[dict] = None,
    ):
        super().__init__(message, error_code="API_CONNECTION_ERROR", context=context)
        self.status_code = status_code


class APITimeoutError(APIConnectionError):
    def __init__(self, endpoint: str, timeout_seconds: float, context: Optional[dict] = None):
        message = f"API request to {endpoint} timed out after {timeout_seconds}s"
        super().__init__(message, context=context)
        self.error_code = "API_TIMEOUT_ERROR"
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds


class APIRateLimitError(APIConnectionError):
    def __init__(
        self, message: str, retry_after: Optional[float] = None, context: Optional[dict] = None
    ):
        super().__init__(message, context=context)
        self.error_code = "API_RATE_LIMIT_ERROR"
        self.retry_after = retry_after


class APIAuthenticationError(APIConnectionError):
    def __init__(self, message: str = "Authentication failed", context: Optional[dict] = None):
        super().__init__(message, status_code=401, context=context)
        self.error_code = "API_AUTH_ERROR"


class APIAuthorizationError(APIConnectionError):
    def __init__(self, message: str = "Authorization failed", context: Optional[dict] = None):
        super().__init__(message, status_code=403, context=context)
        self.error_code = "API_AUTHZ_ERROR"


class AnalyzerError(CriblHealthCheckError):
    def __init__(
        self,
        analyzer_name: str,
        message: str,
        context: Optional[dict] = None,
    ):
        full_message = f"{analyzer_name}: {message}"
        super().__init__(full_message, error_code="ANALYZER_ERROR", context=context)
        self.analyzer_name = analyzer_name


class AnalyzerInitializationError(AnalyzerError):
    def __init__(self, analyzer_name: str, reason: str, context: Optional[dict] = None):
        super().__init__(analyzer_name, f"Initialization failed: {reason}", context=context)
        self.error_code = "ANALYZER_INIT_ERROR"


class AnalyzerExecutionError(AnalyzerError):
    def __init__(self, analyzer_name: str, reason: str, context: Optional[dict] = None):
        super().__init__(analyzer_name, f"Execution failed: {reason}", context=context)
        self.error_code = "ANALYZER_EXEC_ERROR"


class ConfigurationError(CriblHealthCheckError):
    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, error_code="CONFIG_ERROR", context=context)


class InvalidDeploymentError(ConfigurationError):
    def __init__(self, deployment_id: str, reason: str, context: Optional[dict] = None):
        message = f"Invalid deployment '{deployment_id}': {reason}"
        super().__init__(message, context=context)
        self.error_code = "INVALID_DEPLOYMENT_ERROR"
        self.deployment_id = deployment_id


class DeploymentNotFoundError(ConfigurationError):
    def __init__(self, deployment_id: str, context: Optional[dict] = None):
        message = f"Deployment '{deployment_id}' not found"
        super().__init__(message, context=context)
        self.error_code = "DEPLOYMENT_NOT_FOUND_ERROR"
        self.deployment_id = deployment_id


class InvalidCredentialsError(ConfigurationError):
    def __init__(
        self, message: str = "Invalid or missing credentials", context: Optional[dict] = None
    ):
        super().__init__(message, context=context)
        self.error_code = "INVALID_CREDENTIALS_ERROR"


class DataValidationError(CriblHealthCheckError):
    def __init__(self, field: str, value: str, reason: str, context: Optional[dict] = None):
        message = f"Validation failed for {field}: {reason} (value: {value})"
        super().__init__(message, error_code="DATA_VALIDATION_ERROR", context=context)
        self.field = field
        self.value = value


class BudgetExceededError(CriblHealthCheckError):
    def __init__(
        self,
        budget_type: str,
        used: int,
        limit: int,
        context: Optional[dict] = None,
    ):
        message = f"{budget_type} budget exceeded: {used}/{limit}"
        super().__init__(message, error_code="BUDGET_EXCEEDED_ERROR", context=context)
        self.budget_type = budget_type
        self.used = used
        self.limit = limit


class APiBudgetExceededError(BudgetExceededError):
    def __init__(self, api_calls_used: int, api_calls_limit: int, context: Optional[dict] = None):
        super().__init__("API calls", api_calls_used, api_calls_limit, context=context)
        self.error_code = "API_BUDGET_EXCEEDED_ERROR"
