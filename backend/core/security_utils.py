
import logging
from fastapi import HTTPException
from functools import wraps

logger = logging.getLogger(__name__)

def safe_error_response(e: Exception, context: str = "Operation failed"):
    """
    Log the full error with traceback but return a generic message to the client.
    This prevents leaking sensitive internal details like stack traces or secrets.
    """
    logger.error(f"{context}: {e}", exc_info=True)
    # Return a generic error message
    raise HTTPException(status_code=500, detail="Internal Server Error")
