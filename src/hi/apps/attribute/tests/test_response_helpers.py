"""
Tests for AttributeResponse and AttributeResponseBuilder classes.

Focuses on high-value business logic: response data structure creation,
JSON serialization, HTTP response generation, and builder pattern functionality.
These are critical for client-server communication consistency.
"""
import json
import logging
from django.http import HttpResponse
from django.test import TestCase

from hi.apps.attribute.response_helpers import (
    AttributeResponse,
    AttributeResponseBuilder,
    DOMUpdate,
)
from hi.apps.attribute.response_constants import (
    DefaultMessages,
    HTTPHeaders,
    ResponseFields,
    UpdateMode,
)

logging.disable(logging.CRITICAL)


class TestDOMUpdate(TestCase):
    """Test DOMUpdate dataclass - critical for DOM manipulation instructions."""

    def test_dom_update_basic_creation(self):
        """Test basic DOMUpdate creation and property access."""
        update = DOMUpdate(
            target="#test-element",
            html="<div>Test Content</div>",
            mode=UpdateMode.REPLACE
        )
        
        self.assertEqual(update.target, "#test-element")
        self.assertEqual(update.html, "<div>Test Content</div>")
        self.assertEqual(update.mode, UpdateMode.REPLACE)

    def test_dom_update_default_mode(self):
        """Test DOMUpdate uses REPLACE as default mode."""
        update = DOMUpdate(
            target="#test-element",
            html="<div>Test Content</div>"
        )
        
        self.assertEqual(update.mode, UpdateMode.REPLACE)

    def test_dom_update_to_dict_conversion(self):
        """Test DOMUpdate serialization to dictionary - critical for JSON response."""
        update = DOMUpdate(
            target="#test-element",
            html="<div>Test Content</div>",
            mode=UpdateMode.APPEND
        )
        
        result = update.to_dict()
        expected = {
            ResponseFields.TARGET: "#test-element",
            ResponseFields.HTML: "<div>Test Content</div>",
            ResponseFields.MODE: "append",
        }
        
        self.assertEqual(result, expected)

    def test_dom_update_all_mode_types(self):
        """Test DOMUpdate works with all update modes - enum consistency."""
        modes_and_values = [
            (UpdateMode.REPLACE, "replace"),
            (UpdateMode.APPEND, "append"), 
            (UpdateMode.PREPEND, "prepend"),
        ]
        
        for mode_enum, mode_value in modes_and_values:
            update = DOMUpdate(
                target="#test", 
                html="<div>test</div>", 
                mode=mode_enum
            )
            result = update.to_dict()
            self.assertEqual(result[ResponseFields.MODE], mode_value)


class TestAttributeResponse(TestCase):
    """Test AttributeResponse dataclass - critical for response structure."""

    def test_attribute_response_success_basic(self):
        """Test basic successful AttributeResponse creation."""
        response = AttributeResponse(
            success=True,
            message="Operation completed"
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Operation completed")
        self.assertEqual(len(response.updates), 0)

    def test_attribute_response_error_basic(self):
        """Test basic error AttributeResponse creation."""
        response = AttributeResponse(
            success=False,
            message="Validation failed"
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Validation failed")

    def test_attribute_response_with_updates(self):
        """Test AttributeResponse with DOM updates - complex data structure."""
        update1 = DOMUpdate("#element1", "<div>Content 1</div>", UpdateMode.REPLACE)
        update2 = DOMUpdate("#element2", "<div>Content 2</div>", UpdateMode.APPEND)
        
        response = AttributeResponse(
            success=True,
            updates=[update1, update2],
            message="Multiple updates applied"
        )
        
        self.assertTrue(response.success)
        self.assertEqual(len(response.updates), 2)
        self.assertEqual(response.updates[0], update1)
        self.assertEqual(response.updates[1], update2)

    def test_attribute_response_to_dict_complete(self):
        """Test complete AttributeResponse dictionary serialization."""
        update = DOMUpdate("#test-element", "<div>Test</div>", UpdateMode.REPLACE)
        response = AttributeResponse(
            success=True,
            updates=[update],
            message="Test message"
        )
        
        result = response.to_dict()
        expected = {
            ResponseFields.SUCCESS: True,
            ResponseFields.UPDATES: [
                {
                    ResponseFields.TARGET: "#test-element",
                    ResponseFields.HTML: "<div>Test</div>",
                    ResponseFields.MODE: "replace"
                }
            ],
            ResponseFields.MESSAGE: "Test message"
        }
        
        self.assertEqual(result, expected)

    def test_attribute_response_to_dict_no_message(self):
        """Test AttributeResponse serialization without message - optional field handling."""
        response = AttributeResponse(success=True, updates=[])
        result = response.to_dict()
        
        self.assertIn(ResponseFields.SUCCESS, result)
        self.assertIn(ResponseFields.UPDATES, result)
        self.assertNotIn(ResponseFields.MESSAGE, result)

    def test_attribute_response_to_http_response_success(self):
        """Test HTTP response generation - critical for Django integration."""
        response = AttributeResponse(
            success=True,
            message="Success"
        )
        
        http_response = response.to_http_response()
        
        self.assertIsInstance(http_response, HttpResponse)
        self.assertEqual(http_response.status_code, 200)
        self.assertEqual(http_response['Content-Type'], HTTPHeaders.APPLICATION_JSON)
        
        # Verify JSON content
        response_data = json.loads(http_response.content)
        self.assertTrue(response_data[ResponseFields.SUCCESS])
        self.assertEqual(response_data[ResponseFields.MESSAGE], "Success")

    def test_attribute_response_to_http_response_custom_status(self):
        """Test HTTP response with custom status code."""
        response = AttributeResponse(success=False)
        http_response = response.to_http_response(status_code=400)
        
        self.assertEqual(http_response.status_code, 400)

    def test_attribute_response_json_serialization_edge_cases(self):
        """Test JSON serialization handles edge cases - robustness testing."""
        # Empty updates list
        response = AttributeResponse(success=True, updates=[])
        result = response.to_dict()
        self.assertEqual(result[ResponseFields.UPDATES], [])
        
        # Special characters in HTML
        update = DOMUpdate("#test", "<div class=\"special-class\">Content</div>")
        response = AttributeResponse(success=True, updates=[update])
        result = response.to_dict()
        expected_html = "<div class=\"special-class\">Content</div>"
        self.assertEqual(result[ResponseFields.UPDATES][0][ResponseFields.HTML], expected_html)


class TestAttributeResponseBuilder(TestCase):
    """Test AttributeResponseBuilder - critical for fluent API pattern."""

    def test_builder_success_basic(self):
        """Test basic success response building."""
        builder = AttributeResponseBuilder()
        response = builder.success().build()
        
        self.assertIsInstance(response, AttributeResponse)
        self.assertTrue(response.success)
        self.assertEqual(len(response.updates), 0)
        self.assertIsNone(response.message)

    def test_builder_error_basic(self):
        """Test basic error response building."""
        builder = AttributeResponseBuilder()
        response = builder.error().build()
        
        self.assertIsInstance(response, AttributeResponse)
        self.assertFalse(response.success)

    def test_builder_fluent_interface_chaining(self):
        """Test builder method chaining - fluent interface functionality."""
        builder = AttributeResponseBuilder()
        result = (builder
                  .success()
                  .with_message("Test message")
                  .add_update("#element", "<div>content</div>", UpdateMode.REPLACE))
        
        # Verify chaining returns the same builder instance
        self.assertIs(result, builder)
        
        response = result.build()
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Test message")
        self.assertEqual(len(response.updates), 1)

    def test_builder_add_multiple_updates(self):
        """Test builder can accumulate multiple updates."""
        response = (AttributeResponseBuilder()
                    .success()
                    .add_update("#element1", "<div>Content 1</div>", UpdateMode.REPLACE)
                    .add_update("#element2", "<div>Content 2</div>", UpdateMode.APPEND)
                    .add_update("#element3", "<div>Content 3</div>", UpdateMode.PREPEND)
                    .build())
        
        self.assertEqual(len(response.updates), 3)
        self.assertEqual(response.updates[0].target, "#element1")
        self.assertEqual(response.updates[0].mode, UpdateMode.REPLACE)
        self.assertEqual(response.updates[1].target, "#element2")
        self.assertEqual(response.updates[1].mode, UpdateMode.APPEND)
        self.assertEqual(response.updates[2].target, "#element3")
        self.assertEqual(response.updates[2].mode, UpdateMode.PREPEND)

    def test_builder_message_override_behavior(self):
        """Test builder message can be set and overridden."""
        response = (AttributeResponseBuilder()
                    .success("First message")
                    .with_message("Second message")
                    .build())
        
        self.assertEqual(response.message, "Second message")

    def test_builder_success_error_state_switching(self):
        """Test builder can switch between success and error states."""
        builder = AttributeResponseBuilder()
        
        # Start as success, switch to error
        response1 = builder.success().error().build()
        self.assertFalse(response1.success)
        
        # Switch back to success
        response2 = builder.success().build()
        self.assertTrue(response2.success)

    def test_builder_build_http_response_default_status(self):
        """Test builder HTTP response generation with default status codes."""
        # Success response defaults to 200
        success_response = (AttributeResponseBuilder()
                            .success()
                            .build_http_response())
        self.assertEqual(success_response.status_code, 200)
        
        # Error response defaults to 400
        error_response = (AttributeResponseBuilder()
                          .error()
                          .build_http_response())
        self.assertEqual(error_response.status_code, 400)

    def test_builder_build_http_response_custom_status(self):
        """Test builder HTTP response with custom status code."""
        response = (AttributeResponseBuilder()
                    .success()
                    .build_http_response(status_code=201))
        
        self.assertEqual(response.status_code, 201)

    def test_builder_build_http_response_json_content(self):
        """Test builder HTTP response contains valid JSON - integration testing."""
        http_response = (AttributeResponseBuilder()
                         .success()
                         .add_update("#test", "<div>Test</div>")
                         .with_message("Test message")
                         .build_http_response())
        
        # Verify response structure
        self.assertEqual(http_response['Content-Type'], HTTPHeaders.APPLICATION_JSON)
        
        # Verify JSON parsing and content
        response_data = json.loads(http_response.content)
        self.assertTrue(response_data[ResponseFields.SUCCESS])
        self.assertEqual(response_data[ResponseFields.MESSAGE], "Test message")
        self.assertEqual(len(response_data[ResponseFields.UPDATES]), 1)
        self.assertEqual(response_data[ResponseFields.UPDATES][0][ResponseFields.TARGET], "#test")

    def test_builder_create_success_response_class_method(self):
        """Test convenience class method for success responses."""
        update1 = DOMUpdate("#element1", "<div>Content 1</div>", UpdateMode.REPLACE)
        update2 = DOMUpdate("#element2", "<div>Content 2</div>", UpdateMode.APPEND)
        
        http_response = AttributeResponseBuilder.create_success_response(
            updates=[update1, update2],
            message="Custom success message",
            status_code=201
        )
        
        self.assertIsInstance(http_response, HttpResponse)
        self.assertEqual(http_response.status_code, 201)
        
        response_data = json.loads(http_response.content)
        self.assertTrue(response_data[ResponseFields.SUCCESS])
        self.assertEqual(response_data[ResponseFields.MESSAGE], "Custom success message")
        self.assertEqual(len(response_data[ResponseFields.UPDATES]), 2)

    def test_builder_create_success_response_default_message(self):
        """Test success response class method uses default message."""
        http_response = AttributeResponseBuilder.create_success_response(updates=[])
        
        response_data = json.loads(http_response.content)
        self.assertEqual(response_data[ResponseFields.MESSAGE], DefaultMessages.SAVE_SUCCESS)

    def test_builder_create_error_response_class_method(self):
        """Test convenience class method for error responses."""
        update = DOMUpdate("#error-element", "<div>Error content</div>", UpdateMode.REPLACE)
        
        http_response = AttributeResponseBuilder.create_error_response(
            updates=[update],
            message="Custom error message",
            status_code=422
        )
        
        self.assertIsInstance(http_response, HttpResponse)
        self.assertEqual(http_response.status_code, 422)
        
        response_data = json.loads(http_response.content)
        self.assertFalse(response_data[ResponseFields.SUCCESS])
        self.assertEqual(response_data[ResponseFields.MESSAGE], "Custom error message")

    def test_builder_create_error_response_default_message(self):
        """Test error response class method uses default message."""
        http_response = AttributeResponseBuilder.create_error_response(updates=[])
        
        response_data = json.loads(http_response.content)
        self.assertEqual(response_data[ResponseFields.MESSAGE], DefaultMessages.SAVE_ERROR)

    def test_builder_create_upload_success_response_class_method(self):
        """Test convenience class method for file upload success."""
        http_response = AttributeResponseBuilder.create_upload_success_response(
            target_selector="#file-grid",
            file_card_html="<div class='file-card'>New File</div>",
            message="Custom upload message"
        )
        
        self.assertIsInstance(http_response, HttpResponse)
        self.assertEqual(http_response.status_code, 200)
        
        response_data = json.loads(http_response.content)
        self.assertTrue(response_data[ResponseFields.SUCCESS])
        self.assertEqual(response_data[ResponseFields.MESSAGE], "Custom upload message")
        self.assertEqual(len(response_data[ResponseFields.UPDATES]), 1)
        self.assertEqual(response_data[ResponseFields.UPDATES][0][ResponseFields.TARGET], "#file-grid")
        self.assertEqual(response_data[ResponseFields.UPDATES][0][ResponseFields.MODE], "append")

    def test_builder_create_upload_success_response_default_message(self):
        """Test upload success response uses default message."""
        http_response = AttributeResponseBuilder.create_upload_success_response(
            target_selector="#file-grid",
            file_card_html="<div class='file-card'>File</div>"
        )
        
        response_data = json.loads(http_response.content)
        self.assertEqual(response_data[ResponseFields.MESSAGE], DefaultMessages.UPLOAD_SUCCESS)


class TestResponseHelpersEdgeCases(TestCase):
    """Test edge cases and error conditions - robustness testing."""

    def test_dom_update_empty_strings(self):
        """Test DOMUpdate handles empty strings gracefully."""
        update = DOMUpdate(target="", html="", mode=UpdateMode.REPLACE)
        result = update.to_dict()
        
        self.assertEqual(result[ResponseFields.TARGET], "")
        self.assertEqual(result[ResponseFields.HTML], "")

    def test_attribute_response_empty_message_serialization(self):
        """Test AttributeResponse handles empty message correctly."""
        response = AttributeResponse(success=True, message="")
        result = response.to_dict()
        
        # Empty message should be excluded (falsy values are filtered out)
        self.assertNotIn(ResponseFields.MESSAGE, result)

    def test_builder_multiple_build_calls_isolation(self):
        """Test builder builds independent response objects."""
        builder = AttributeResponseBuilder().success().with_message("Test")
        
        response1 = builder.build()
        response2 = builder.build()
        
        # Should be different objects
        self.assertIsNot(response1, response2)
        # But with same content
        self.assertEqual(response1.success, response2.success)
        self.assertEqual(response1.message, response2.message)

    def test_builder_state_persistence_across_builds(self):
        """Test builder state persists across multiple builds."""
        builder = (AttributeResponseBuilder()
                   .success()
                   .add_update("#element", "<div>content</div>")
                   .with_message("Persistent message"))
        
        response1 = builder.build()
        response2 = builder.build()
        
        # Both responses should have the same configuration
        self.assertTrue(response1.success)
        self.assertTrue(response2.success)
        self.assertEqual(response1.message, response2.message)
        self.assertEqual(len(response1.updates), 1)
        self.assertEqual(len(response2.updates), 1)

    def test_response_json_special_characters(self):
        """Test response handles JSON special characters correctly."""
        update = DOMUpdate(
            target="#test-element", 
            html="<div>Content with \"quotes\" and 'apostrophes' and \\ backslashes</div>"
        )
        response = AttributeResponse(success=True, updates=[update])
        
        # Should not raise exception during serialization
        http_response = response.to_http_response()
        
        # Should be valid JSON
        response_data = json.loads(http_response.content)
        expected_html = "<div>Content with \"quotes\" and 'apostrophes' and \\ backslashes</div>"
        self.assertEqual(
            response_data[ResponseFields.UPDATES][0][ResponseFields.HTML], 
            expected_html
        )
