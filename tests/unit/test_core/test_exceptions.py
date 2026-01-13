"""
Unit tests for core exception classes.
"""

from cribl_hc.core.exceptions import (
    AnalyzerError,
    AnalyzerExecutionError,
    AnalyzerInitializationError,
    APIAuthenticationError,
    APIAuthorizationError,
    APiBudgetExceededError,
    APIConnectionError,
    APIRateLimitError,
    APITimeoutError,
    BudgetExceededError,
    ConfigurationError,
    CriblHealthCheckError,
    DataValidationError,
    DeploymentNotFoundError,
    InvalidCredentialsError,
    InvalidDeploymentError,
)


class TestCriblHealthCheckError:
    """Test base CriblHealthCheckError class."""

    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = CriblHealthCheckError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "CriblHealthCheckError"
        assert error.context == {}

    def test_initialization_with_error_code(self):
        """Test error initialization with custom error code."""
        error = CriblHealthCheckError("Test error", error_code="CUSTOM_ERROR")

        assert error.message == "Test error"
        assert error.error_code == "CUSTOM_ERROR"

    def test_initialization_with_context(self):
        """Test error initialization with context."""
        context = {"deployment": "prod", "endpoint": "/api/v1/status"}
        error = CriblHealthCheckError("Test error", context=context)

        assert error.context == context
        assert "deployment=prod" in str(error)
        assert "endpoint=/api/v1/status" in str(error)

    def test_str_representation_with_context(self):
        """Test string representation includes context."""
        context = {"key1": "value1", "key2": "value2"}
        error = CriblHealthCheckError("Test message", context=context)

        error_str = str(error)
        assert "Test message" in error_str
        assert "key1=value1" in error_str
        assert "key2=value2" in error_str

    def test_str_representation_without_context(self):
        """Test string representation without context."""
        error = CriblHealthCheckError("Simple message")
        assert str(error) == "Simple message"

    def test_base_exception_attribute(self):
        """Test base_exception class attribute."""
        assert CriblHealthCheckError.base_exception is True


class TestAPIConnectionError:
    """Test APIConnectionError class."""

    def test_basic_initialization(self):
        """Test basic API connection error initialization."""
        error = APIConnectionError("Connection failed")

        assert error.message == "Connection failed"
        assert error.error_code == "API_CONNECTION_ERROR"
        assert error.status_code is None

    def test_initialization_with_status_code(self):
        """Test initialization with HTTP status code."""
        error = APIConnectionError("Server error", status_code=500)

        assert error.status_code == 500
        assert error.error_code == "API_CONNECTION_ERROR"

    def test_initialization_with_context(self):
        """Test initialization with context."""
        context = {"url": "https://api.example.com", "method": "GET"}
        error = APIConnectionError("Request failed", context=context)

        assert error.context == context


class TestAPITimeoutError:
    """Test APITimeoutError class."""

    def test_initialization(self):
        """Test timeout error initialization."""
        error = APITimeoutError("/api/v1/status", 30.0)

        assert "API request to /api/v1/status timed out after 30.0s" in error.message
        assert error.error_code == "API_TIMEOUT_ERROR"
        assert error.endpoint == "/api/v1/status"
        assert error.timeout_seconds == 30.0

    def test_initialization_with_context(self):
        """Test timeout error with context."""
        context = {"retry_count": 3}
        error = APITimeoutError("/api/v1/workers", 15.5, context=context)

        assert error.context == context
        assert error.endpoint == "/api/v1/workers"
        assert error.timeout_seconds == 15.5


class TestAPIRateLimitError:
    """Test APIRateLimitError class."""

    def test_basic_initialization(self):
        """Test basic rate limit error initialization."""
        error = APIRateLimitError("Rate limit exceeded")

        assert error.message == "Rate limit exceeded"
        assert error.error_code == "API_RATE_LIMIT_ERROR"
        assert error.retry_after is None

    def test_initialization_with_retry_after(self):
        """Test initialization with retry_after value."""
        error = APIRateLimitError("Too many requests", retry_after=60.0)

        assert error.retry_after == 60.0

    def test_initialization_with_context(self):
        """Test initialization with context."""
        context = {"requests_per_minute": 100}
        error = APIRateLimitError("Rate limit hit", context=context)

        assert error.context == context


class TestAPIAuthenticationError:
    """Test APIAuthenticationError class."""

    def test_default_initialization(self):
        """Test default authentication error initialization."""
        error = APIAuthenticationError()

        assert error.message == "Authentication failed"
        assert error.error_code == "API_AUTH_ERROR"
        assert error.status_code == 401

    def test_custom_message_initialization(self):
        """Test authentication error with custom message."""
        error = APIAuthenticationError("Invalid token")

        assert error.message == "Invalid token"
        assert error.status_code == 401

    def test_initialization_with_context(self):
        """Test authentication error with context."""
        context = {"token_type": "bearer"}
        error = APIAuthenticationError("Token expired", context=context)

        assert error.context == context


class TestAPIAuthorizationError:
    """Test APIAuthorizationError class."""

    def test_default_initialization(self):
        """Test default authorization error initialization."""
        error = APIAuthorizationError()

        assert error.message == "Authorization failed"
        assert error.error_code == "API_AUTHZ_ERROR"
        assert error.status_code == 403

    def test_custom_message_initialization(self):
        """Test authorization error with custom message."""
        error = APIAuthorizationError("Insufficient permissions")

        assert error.message == "Insufficient permissions"
        assert error.status_code == 403

    def test_initialization_with_context(self):
        """Test authorization error with context."""
        context = {"required_role": "admin"}
        error = APIAuthorizationError("Access denied", context=context)

        assert error.context == context


class TestAnalyzerError:
    """Test AnalyzerError class."""

    def test_initialization(self):
        """Test analyzer error initialization."""
        error = AnalyzerError("HealthAnalyzer", "Analysis failed")

        assert "HealthAnalyzer: Analysis failed" in error.message
        assert error.error_code == "ANALYZER_ERROR"
        assert error.analyzer_name == "HealthAnalyzer"

    def test_initialization_with_context(self):
        """Test analyzer error with context."""
        context = {"worker_count": 5}
        error = AnalyzerError("ResourceAnalyzer", "Memory check failed", context=context)

        assert error.analyzer_name == "ResourceAnalyzer"
        assert error.context == context


class TestAnalyzerInitializationError:
    """Test AnalyzerInitializationError class."""

    def test_initialization(self):
        """Test analyzer initialization error."""
        error = AnalyzerInitializationError("ConfigAnalyzer", "Missing required config")

        assert "ConfigAnalyzer: Initialization failed: Missing required config" in error.message
        assert error.error_code == "ANALYZER_INIT_ERROR"
        assert error.analyzer_name == "ConfigAnalyzer"

    def test_initialization_with_context(self):
        """Test analyzer initialization error with context."""
        context = {"config_file": "/etc/config.yaml"}
        error = AnalyzerInitializationError("SecurityAnalyzer", "Config not found", context=context)

        assert error.context == context


class TestAnalyzerExecutionError:
    """Test AnalyzerExecutionError class."""

    def test_initialization(self):
        """Test analyzer execution error."""
        error = AnalyzerExecutionError("PipelineAnalyzer", "Pipeline data unavailable")

        assert "PipelineAnalyzer: Execution failed: Pipeline data unavailable" in error.message
        assert error.error_code == "ANALYZER_EXEC_ERROR"
        assert error.analyzer_name == "PipelineAnalyzer"

    def test_initialization_with_context(self):
        """Test analyzer execution error with context."""
        context = {"pipeline_id": "main-pipeline"}
        error = AnalyzerExecutionError(
            "BackpressureAnalyzer", "Metrics unavailable", context=context
        )

        assert error.context == context


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_initialization(self):
        """Test configuration error initialization."""
        error = ConfigurationError("Invalid configuration")

        assert error.message == "Invalid configuration"
        assert error.error_code == "CONFIG_ERROR"

    def test_initialization_with_context(self):
        """Test configuration error with context."""
        context = {"section": "database"}
        error = ConfigurationError("Missing required field", context=context)

        assert error.context == context


class TestInvalidDeploymentError:
    """Test InvalidDeploymentError class."""

    def test_initialization(self):
        """Test invalid deployment error initialization."""
        error = InvalidDeploymentError("prod-cluster", "URL is malformed")

        assert "Invalid deployment 'prod-cluster': URL is malformed" in error.message
        assert error.error_code == "INVALID_DEPLOYMENT_ERROR"
        assert error.deployment_id == "prod-cluster"

    def test_initialization_with_context(self):
        """Test invalid deployment error with context."""
        context = {"url": "invalid-url"}
        error = InvalidDeploymentError("test-env", "Invalid URL format", context=context)

        assert error.deployment_id == "test-env"
        assert error.context == context


class TestDeploymentNotFoundError:
    """Test DeploymentNotFoundError class."""

    def test_initialization(self):
        """Test deployment not found error initialization."""
        error = DeploymentNotFoundError("missing-deployment")

        assert "Deployment 'missing-deployment' not found" in error.message
        assert error.error_code == "DEPLOYMENT_NOT_FOUND_ERROR"
        assert error.deployment_id == "missing-deployment"

    def test_initialization_with_context(self):
        """Test deployment not found error with context."""
        context = {"available_deployments": ["prod", "staging"]}
        error = DeploymentNotFoundError("dev", context=context)

        assert error.deployment_id == "dev"
        assert error.context == context


class TestInvalidCredentialsError:
    """Test InvalidCredentialsError class."""

    def test_default_initialization(self):
        """Test default invalid credentials error initialization."""
        error = InvalidCredentialsError()

        assert error.message == "Invalid or missing credentials"
        assert error.error_code == "INVALID_CREDENTIALS_ERROR"

    def test_custom_message_initialization(self):
        """Test invalid credentials error with custom message."""
        error = InvalidCredentialsError("Token has expired")

        assert error.message == "Token has expired"

    def test_initialization_with_context(self):
        """Test invalid credentials error with context."""
        context = {"credential_type": "api_token"}
        error = InvalidCredentialsError("Credential validation failed", context=context)

        assert error.context == context


class TestDataValidationError:
    """Test DataValidationError class."""

    def test_initialization(self):
        """Test data validation error initialization."""
        error = DataValidationError("email", "invalid-email", "Must be valid email format")

        assert (
            "Validation failed for email: Must be valid email format (value: invalid-email)"
            in error.message
        )
        assert error.error_code == "DATA_VALIDATION_ERROR"
        assert error.field == "email"
        assert error.value == "invalid-email"

    def test_initialization_with_context(self):
        """Test data validation error with context."""
        context = {"validator": "email_regex"}
        error = DataValidationError("user_email", "bad@", "Invalid format", context=context)

        assert error.field == "user_email"
        assert error.value == "bad@"
        assert error.context == context


class TestBudgetExceededError:
    """Test BudgetExceededError class."""

    def test_initialization(self):
        """Test budget exceeded error initialization."""
        error = BudgetExceededError("Memory", 1024, 512)

        assert "Memory budget exceeded: 1024/512" in error.message
        assert error.error_code == "BUDGET_EXCEEDED_ERROR"
        assert error.budget_type == "Memory"
        assert error.used == 1024
        assert error.limit == 512

    def test_initialization_with_context(self):
        """Test budget exceeded error with context."""
        context = {"unit": "MB"}
        error = BudgetExceededError("Disk", 2048, 1024, context=context)

        assert error.budget_type == "Disk"
        assert error.used == 2048
        assert error.limit == 1024
        assert error.context == context


class TestAPiBudgetExceededError:
    """Test APiBudgetExceededError class."""

    def test_initialization(self):
        """Test API budget exceeded error initialization."""
        error = APiBudgetExceededError(150, 100)

        assert "API calls budget exceeded: 150/100" in error.message
        assert error.error_code == "API_BUDGET_EXCEEDED_ERROR"
        assert error.budget_type == "API calls"
        assert error.used == 150
        assert error.limit == 100

    def test_initialization_with_context(self):
        """Test API budget exceeded error with context."""
        context = {"analyzer": "HealthAnalyzer"}
        error = APiBudgetExceededError(75, 50, context=context)

        assert error.used == 75
        assert error.limit == 50
        assert error.context == context


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_cribl_health_check_error_is_exception(self):
        """Test that CriblHealthCheckError inherits from Exception."""
        error = CriblHealthCheckError("test")
        assert isinstance(error, Exception)

    def test_api_connection_error_inheritance(self):
        """Test APIConnectionError inheritance."""
        error = APIConnectionError("test")
        assert isinstance(error, CriblHealthCheckError)
        assert isinstance(error, Exception)

    def test_api_timeout_error_inheritance(self):
        """Test APITimeoutError inheritance."""
        error = APITimeoutError("/test", 30.0)
        assert isinstance(error, APIConnectionError)
        assert isinstance(error, CriblHealthCheckError)

    def test_analyzer_error_inheritance(self):
        """Test AnalyzerError inheritance."""
        error = AnalyzerError("TestAnalyzer", "test")
        assert isinstance(error, CriblHealthCheckError)
        assert isinstance(error, Exception)

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inheritance."""
        error = ConfigurationError("test")
        assert isinstance(error, CriblHealthCheckError)
        assert isinstance(error, Exception)

    def test_budget_exceeded_error_inheritance(self):
        """Test BudgetExceededError inheritance."""
        error = BudgetExceededError("test", 10, 5)
        assert isinstance(error, CriblHealthCheckError)
        assert isinstance(error, Exception)

    def test_api_budget_exceeded_error_inheritance(self):
        """Test APiBudgetExceededError inheritance."""
        error = APiBudgetExceededError(10, 5)
        assert isinstance(error, BudgetExceededError)
        assert isinstance(error, CriblHealthCheckError)
