# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeDoc is an AI-powered development plan generator that demonstrates Agent application capabilities with MCP (Model Context Protocol) service integration. It transforms product ideas into comprehensive development plans with AI programming assistant prompts.

**Technology Stack:**
- **Backend**: Python 3.11 with Gradio 5.34.1 for web interface
- **AI Integration**: Silicon Flow API with Qwen2.5-72B-Instruct model
- **MCP Services**: DeepWiki, Fetch, and Doubao integrations for external knowledge
- **Architecture**: Agent application with intelligent service routing

## Development Commands

### Basic Operations
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
python app.py

# Check application health
curl http://localhost:3000/
```

### Environment Configuration
Required environment variables:
- `SILICONFLOW_API_KEY` - Primary AI service API key (required)
- `DEEPWIKI_SSE_URL` - DeepWiki MCP service URL (optional)
- `FETCH_SSE_URL` - Fetch MCP service URL (optional) 
- `DOUBAO_SSE_URL` - Doubao MCP service URL (optional)
- `DOUBAO_API_KEY` - Doubao service API key (optional)
- `PORT` - Application port (default: 3000)
- `NODE_ENV` - Environment (development/production)

### Docker Operations
```bash
# Build and run with Docker
docker build -t vibedoc .
docker run -p 3000:3000 --env-file .env vibedoc

# Use Docker Compose for full stack
docker-compose up -d

# View logs
docker-compose logs -f vibedoc

# Stop services
docker-compose down
```

### Testing the Application
```bash
# Test basic functionality
curl -X POST http://localhost:3000/api/generate_plan \
  -H "Content-Type: application/json" \
  -d '{"idea": "test idea"}'

# Check MCP service status
# Access the web interface at http://localhost:3000 to view service status
```

## Code Architecture

### Core Components

**Main Application (`app.py`)**
- Gradio web interface with custom CSS styling
- AI development plan generation with external knowledge integration
- Multiple MCP service coordination and intelligent routing
- Comprehensive error handling and logging

**Configuration Management (`config.py`)**
- Environment-based configuration with validation
- MCP service definitions and health check endpoints
- Feature flags based on available services
- Development/production environment handling

**MCP Service Manager (`mcp_manager.py`)**
- Intelligent service routing based on URL patterns
- Multi-service coordination and result fusion
- Service health monitoring and statistics
- Error handling with fallback mechanisms

### Key Design Patterns

**Agent Application Pattern:**
- The application acts as an intelligent agent that coordinates multiple MCP services
- Implements smart routing to select appropriate services based on input characteristics
- Combines results from multiple knowledge sources for enhanced output

**Service Integration Pattern:**
```python
# Example of MCP service coordination
suitable_services = self.get_service_for_url(url)
for service_type in suitable_services:
    payload = self._build_payload_for_service(service_type, url)
    result = self.call_single_mcp_service(service_type, payload)
```

**Configuration Pattern:**
- Environment-driven configuration with defaults
- Service availability detection and feature flag management
- Validation and error reporting for missing dependencies

### Critical Files

- `app.py:373` - Main development plan generation function
- `mcp_manager.py:52` - URL-based service routing logic
- `config.py:90` - Configuration validation
- `app.py:143` - External knowledge fetching with MCP integration

## Development Guidelines

### Adding New MCP Services
1. Add service configuration to `config.py` in the `mcp_services` dictionary
2. Update `MCPServiceType` enum in `mcp_manager.py`
3. Implement service-specific payload building in `_build_payload_for_service`
4. Add URL routing rules in `get_service_for_url`

### Modifying AI Prompts
- System prompts are defined in `app.py:422-515`
- Prompts include specific formatting requirements for structured output
- Ensure Mermaid diagram syntax compliance for visual elements

### Error Handling
- All MCP service calls include timeout and retry logic
- Graceful degradation when services are unavailable
- Comprehensive logging for debugging service issues

### UI Customization
- Custom CSS is defined in `app.py:860-1874`
- Gradio components use custom classes for styling
- JavaScript integration for copy functionality and theme handling

## Important Notes

- **Security**: Never commit API keys to the repository - use environment variables
- **MCP Services**: The application demonstrates Agent capabilities by intelligently routing between multiple MCP services
- **Graceful Degradation**: The app functions with any subset of MCP services available
- **Logging**: Comprehensive logging helps debug MCP service integration issues
- **Resource Management**: Proper timeout handling prevents hanging requests

## Deployment Considerations

- Set appropriate environment variables for production
- Configure MCP service URLs for your deployment environment  
- Monitor service health through the built-in status dashboard
- Use Docker Compose for full-stack deployments with optional Redis and Nginx
- Ensure adequate timeout values for MCP service calls in production environments