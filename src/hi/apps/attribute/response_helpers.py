"""
Response helper classes for attribute editing operations.

This module provides a reusable builder pattern for constructing
consistent JSON responses across all attribute editing views.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.http import HttpResponse

from .response_constants import (
    DefaultMessages,
    HTTPHeaders,
    ResponseFields,
    UpdateMode,
)


@dataclass
class DOMUpdate:
    """Represents a single DOM update instruction."""
    target: str  # jQuery selector (e.g., "#element-id")
    html: str  # HTML content to insert
    mode: UpdateMode = UpdateMode.REPLACE
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            ResponseFields.TARGET: self.target,
            ResponseFields.HTML: self.html,
            ResponseFields.MODE: self.mode.value,
        }


@dataclass
class AttributeResponse:
    """Represents a complete attribute operation response."""
    success: bool
    updates: List[DOMUpdate] = field(default_factory=list)
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            ResponseFields.SUCCESS: self.success,
            ResponseFields.UPDATES: [update.to_dict() for update in self.updates],
        }
        if self.message:
            result[ResponseFields.MESSAGE] = self.message
        return result
    
    def to_http_response(self, status_code: int = 200) -> HttpResponse:
        """Convert to Django HttpResponse with proper JSON formatting."""
        return HttpResponse(
            json.dumps(self.to_dict()),
            content_type=HTTPHeaders.APPLICATION_JSON,
            status=status_code,
        )


class AttributeResponseBuilder:
    """
    Builder pattern for constructing attribute responses.
    
    Usage:
        response = (AttributeResponseBuilder()
            .success()
            .add_update("#content", html_content)
            .with_message("Saved successfully")
            .build())
    """
    
    def __init__(self):
        self._success: bool = True
        self._updates: List[DOMUpdate] = []
        self._message: Optional[str] = None
    
    def success(self, message: Optional[str] = None) -> "AttributeResponseBuilder":
        """Set response as successful."""
        self._success = True
        if message:
            self._message = message
        return self
    
    def error(self, message: Optional[str] = None) -> "AttributeResponseBuilder":
        """Set response as error."""
        self._success = False
        if message:
            self._message = message
        return self
    
    def add_update(
        self,
        target: str,
        html: str,
        mode: UpdateMode = UpdateMode.REPLACE
    ) -> "AttributeResponseBuilder":
        """Add a DOM update instruction."""
        self._updates.append( DOMUpdate(target=target, html=html, mode=mode) )
        return self
    
    def with_message(self, message: str) -> "AttributeResponseBuilder":
        """Set the response message."""
        self._message = message
        return self
    
    def build(self) -> AttributeResponse:
        """Build the final AttributeResponse object."""
        return AttributeResponse(
            success=self._success,
            updates=self._updates,
            message=self._message,
        )
    
    def build_http_response(self, status_code: Optional[int] = None) -> HttpResponse:
        """Build and return as Django HttpResponse."""
        if status_code is None:
            status_code = 200 if self._success else 400
        return self.build().to_http_response(status_code)
    
    # Convenience class methods for common patterns
    
    @classmethod
    def create_success_response(
        cls,
        updates: List[DOMUpdate],
        message: str = DefaultMessages.SAVE_SUCCESS,
        status_code: int = 200
    ) -> HttpResponse:
        """Create a standard success response."""
        builder = cls().success().with_message(message)
        for update in updates:
            builder._updates.append(update)
        return builder.build_http_response(status_code)
    
    @classmethod
    def create_error_response(
        cls,
        updates: List[DOMUpdate],
        message: str = DefaultMessages.SAVE_ERROR,
        status_code: int = 400
    ) -> HttpResponse:
        """Create a standard error response."""
        builder = cls().error().with_message(message)
        for update in updates:
            builder._updates.append(update)
        return builder.build_http_response(status_code)
    
    @classmethod
    def create_upload_success_response(
        cls,
        target_selector: str,
        file_card_html: str,
        message: str = DefaultMessages.UPLOAD_SUCCESS
    ) -> HttpResponse:
        """Create a response for successful file upload."""
        return (cls()
                .success()
                .add_update(target_selector, file_card_html, UpdateMode.APPEND)
                .with_message(message)
                .build_http_response())
