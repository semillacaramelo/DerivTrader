# Deriv API Trading Bot Development Prompt

## Project Overview
We are building a modular Python trading bot with a custom WebSocket implementation for connecting to Deriv.com's API. The goal is to create a robust API connection module that supports both demo and real accounts, with comprehensive error handling and connection management.

## Current Implementation Status
- Created a custom WebSocket-based API client for Deriv.com using Python's websockets library
- Implemented simulation mode that allows testing without valid API tokens
- Added comprehensive error handling and logging
- Built helper methods for common API operations (get_ticks, get_candles, etc.)
- Implemented subscription support with callback functionality 
- Created testing utilities to validate API connections

## Current Issues
- The API connection is being rejected with HTTP 401 errors when using real API tokens
- The token validation may need adjustment to match Deriv's exact specifications (observed tokens are ~15 characters)
- Connection and authentication flow might need to be aligned with official API requirements
- The WebSocket implementation needs to be validated against the official API documentation
- Current token diagnostic shows: "Token length: 15 chars, Composition: 13 letters, 2 digits, 0 special chars"

## Repository Structure
- `modules/api_connection.py`: Core API connection functionality
- `modules/logger.py`: Logging configuration
- `utils/helpers.py`: Helper functions
- `utils/validators.py`: Input validation
- `config.py`: Configuration loading from environment variables
- `__main__.py`: Entry point and demo functionality
- `test_api_connection.py`: Testing utilities

## Environment Variables
The bot is configured to use the following environment variables:
- `DERIV_API_TOKEN_DEMO`: API token for demo account
- `DERIV_API_TOKEN_REAL`: API token for real account
- `APP_ID`: Application ID for Deriv API (default: 1089)
- `DEFAULT_ACCOUNT_TYPE`: Which account type to use (demo or real)
- `ENABLE_SIMULATION`: Whether to use simulation mode for testing
- `LOG_LEVEL` and `LOG_FILE`: Logging configuration

## Reference Resources
1. Official Deriv API documentation: https://deriv-com.github.io/python-deriv-api/
2. API Explorer: https://api.deriv.com/api-explorer
3. Getting Started Guide: https://developers.deriv.com/docs/getting-started
4. Python Deriv API Package: https://pypi.org/project/python-deriv-api/
5. Deriv Community: https://community.deriv.com
6. GitHub Repository for official Python client: https://github.com/deriv-com/python-deriv-api
7. API Token Documentation: https://api.deriv.com/api-explorer#api_token

## Next Steps
1. Fix the API token handling and authentication flow based on official documentation:
   - Update token validation to accept Deriv's 15-character token format
   - Review the WebSocket connection parameters against the official specification
   - Check if additional headers or parameters are required for authentication
   - Verify the endpoint URLs are correct and use appropriate protocol versions

2. Enhance the error handling and diagnostics:
   - Add better error identification for HTTP 401 rejections
   - Implement more informative logging when authentication fails
   - Include connection parameter diagnostics to troubleshoot issues

3. Fix implementation bugs:
   - Fix the typo in the subscribe_candles method (awaitself.subscribe should be await self.subscribe)
   - Review and fix any other potential syntax or logic errors

4. Test and validate all functionality:
   - Run comprehensive connection tests with both demo and real accounts
   - Validate subscription methods and callback handling
   - Test reconnection logic under various failure scenarios

5. Add documentation and examples:
   - Document the differences between our custom implementation and the official client
   - Provide usage examples for key functionality
   - Add inline references to official documentation for future maintenance

## Notes
- The API tokens need to be properly configured in environment variables
- The observed tokens are approximately 15 characters long, not matching our original validation pattern
- HTTP 401 errors indicate authentication issues with the provided tokens
- The simulation mode allows development and testing without valid API tokens
- Based on our testing, it seems the token format or authentication method might differ from our initial implementation