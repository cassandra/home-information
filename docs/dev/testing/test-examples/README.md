# Django Test Pattern Examples

This directory contains concrete examples of well-structured Django tests derived from extensive refactoring work in the HI application.

## Files

### `django-test-patterns-examples.py`
Comprehensive examples showing:
- **CRUD Testing**: Real database objects vs mocking
- **AJAX/JSON Views**: Testing modern async responses
- **Form Validation**: Complete field requirements and file uploads
- **Complex Business Logic**: Entity pairings, many-to-many through models
- **Session Dependencies**: Middleware state requirements
- **Synthetic Data**: Consistent test data generation
- **Error Handling**: 404s, validation errors without mocking

## Usage

When working on Django tests, refer to these examples to:

1. **Avoid anti-patterns** like over-mocking database operations
2. **Follow established patterns** for session setup and form validation
3. **Use proper assertions** for JSON vs HTML responses
4. **Structure test data** consistently with synthetic generators
5. **Test integration flows** rather than just method calls

## Key Principles

- ✅ **Test real behavior** with actual database transactions
- ✅ **Use Django's test framework** as designed (isolated DB transactions)  
- ✅ **Test business outcomes** not implementation details
- ✅ **Follow application patterns** for enums, sessions, relationships
- ❌ **Don't mock** basic CRUD, model relationships, or form processing
- ❌ **Don't assume** direct relationships - verify through models/admin

## Context

These patterns were discovered while converting heavily mocked tests to use real objects, resulting in:
- More reliable tests that catch real bugs
- Better documentation of application architecture  
- Easier maintenance and debugging
- Higher confidence in system behavior

Use these examples as templates when writing new tests or refactoring existing ones.