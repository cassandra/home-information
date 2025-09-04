"""
Constants and enums for attribute response handling.

This module defines all constants used in the client-server communication
for attribute editing operations, ensuring consistency and type safety.
"""
from enum import Enum


class UpdateMode(Enum):
    """DOM update modes for client-side operations."""
    REPLACE = "replace"
    APPEND = "append"
    PREPEND = "prepend"


class ResponseStatus(Enum):
    """Response status types."""
    SUCCESS = "success"
    ERROR = "error"


# JSON Response Field Names
class ResponseFields:
    """Field names used in JSON responses."""
    SUCCESS = "success"
    UPDATES = "updates"
    MESSAGE = "message"
    TARGET = "target"
    HTML = "html"
    MODE = "mode"


# HTTP Headers
class HTTPHeaders:
    """HTTP headers used in AJAX requests/responses."""
    X_REQUESTED_WITH = "X-Requested-With"
    XML_HTTP_REQUEST = "XMLHttpRequest"
    CONTENT_TYPE = "Content-Type"
    APPLICATION_JSON = "application/json"


# Default Messages
class DefaultMessages:
    """Default status messages for common operations."""
    SAVE_SUCCESS = "Changes saved successfully"
    SAVE_ERROR = "Please correct the errors below"
    UPLOAD_SUCCESS = "File uploaded successfully"
    UPLOAD_ERROR = "File upload failed. Please check the file and try again."
    DELETE_PENDING = '"{}" will be deleted when you save'
    DELETE_CANCELLED = 'Deletion of "{}" cancelled'
    RESTORE_SUCCESS = "Value restored from history"
    RESTORE_ERROR = "Value could not be restored from history."
