import pytest
from fastapi import HTTPException
from unittest.mock import patch
from backend.core.security_utils import safe_error_response


def test_safe_error_response_raises_http_exception():
    """Test that safe_error_response raises an HTTPException."""
    test_exception = Exception("Super secret internal database error")
    context_msg = "Failed during sensitive operation"

    with pytest.raises(HTTPException) as exc_info:
        safe_error_response(test_exception, context_msg)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal Server Error"
    # Ensure sensitive info is NOT in the response
    secret_msg = "Super secret internal database error"
    assert secret_msg not in str(exc_info.value.detail)


@patch("backend.core.security_utils.logger")
def test_safe_error_response_logs_error(mock_logger):
    """Test that safe_error_response logs the exception internally."""
    test_exception = Exception("Database timeout")
    context_msg = "Database connection failed"

    try:
        safe_error_response(test_exception, context_msg)
    except HTTPException:
        pass

    mock_logger.error.assert_called_once_with(
        f"{context_msg}: {test_exception}", exc_info=True
    )
