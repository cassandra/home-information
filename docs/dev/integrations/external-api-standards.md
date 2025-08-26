# External API Standards

## HTTP Client Standards

### Request Configuration
- Use session-based clients with connection pooling
- Implement retry logic with exponential backoff
- Set appropriate timeouts (default: 30 seconds)
- Include proper User-Agent headers

### Authentication
- Support Bearer token authentication
- Handle token refresh automatically
- Store credentials securely in integration attributes

### Error Handling
- Use custom exception hierarchy
- Implement circuit breaker patterns for resilience
- Log errors with appropriate detail levels

## API Response Patterns

### Data Validation
- Validate all incoming data against expected schemas
- Handle missing or malformed data gracefully
- Provide meaningful error messages

### Rate Limiting  
- Respect API rate limits
- Implement backoff strategies
- Monitor and log rate limit violations

## WebSocket Standards

### Connection Management
- Implement automatic reconnection
- Handle connection state properly
- Process messages asynchronously

### Message Handling
- Parse messages safely with error handling
- Route messages to appropriate handlers
- Maintain message order when required

## Related Documentation
- Integration guidelines: [Integration Guidelines](integration-guidelines.md)
- Gateway implementation: [Gateway Implementation](gateway-implementation.md)