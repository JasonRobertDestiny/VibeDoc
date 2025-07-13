# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeDoc is an AI-driven development plan generator designed for the Magic Tower MCP & Agent Challenge 2025. It's a sophisticated Agent application that converts creative ideas into comprehensive development plans within 30 seconds.

### Core Technology Stack
- **Backend**: Python 3.11 + Gradio 5.34.1
- **AI Model**: Qwen2.5-72B-Instruct via Silicon Flow API
- **Architecture**: MCP (Model Context Protocol) multi-service integration
- **Deployment**: Docker containerization with ModelScope platform support

## Development Commands

### Running the Application
```bash
# Start development server
python app.py

# Using Docker
docker-compose up -d

# Build Docker image
docker build -t vibedoc-app .
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export SILICONFLOW_API_KEY="your_api_key_here"
export PORT=3000
export NODE_ENV=development
```

### Testing & Validation
```bash
# Test MCP service connections
python -c "from mcp_manager import mcp_manager; print(mcp_manager.get_health_status())"

# Validate configuration
python -c "from config import config; print(config.validate_config())"

# Test AI API connection
python -c "import requests; print(requests.get('https://api.siliconflow.cn/v1/models').status_code)"
```

## Architecture Overview

### MCP Agent System
This is an **Agent application** that orchestrates multiple MCP servers:
- **DeepWiki MCP**: Handles deepwiki.org content extraction
- **Fetch MCP**: Processes general web content
- **Doubao MCP**: Provides image generation capabilities

### Core Components
1. **app.py**: Main Gradio application with UI and business logic
2. **config.py**: Centralized configuration management with environment-based settings
3. **mcp_manager.py**: Intelligent MCP service router and manager
4. **requirements.txt**: Python dependencies

### Key Files Structure
```
├── app.py                 # Main application entry point
├── config.py             # Configuration management
├── mcp_manager.py        # MCP service orchestration
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Multi-container setup
└── README.md           # Project documentation
```

## Configuration Management

### Environment Variables
- `SILICONFLOW_API_KEY` (required): API key for AI model access
- `DEEPWIKI_SSE_URL` (optional): DeepWiki MCP service endpoint
- `FETCH_SSE_URL` (optional): Fetch MCP service endpoint
- `DOUBAO_SSE_URL` (optional): Doubao MCP service endpoint
- `DOUBAO_API_KEY` (optional): Doubao service API key
- `PORT`: Application port (default: 3000)
- `NODE_ENV`: Environment mode (development/production)

### Service Configuration
The application uses a sophisticated configuration system in `config.py`:
- Automatic MCP service discovery and health checking
- Feature toggles based on available services
- Environment-specific optimizations

## MCP Integration Patterns

### Service Selection Logic
The system intelligently routes requests to appropriate MCP services:
```python
# DeepWiki for deepwiki.org URLs
# Fetch for GitHub, educational, and general web content
# Multiple services for complex content types
```

### Error Handling & Fallbacks
- Graceful degradation when MCP services are unavailable
- Comprehensive error logging and user feedback
- Automatic service health monitoring

## Development Guidelines

### Adding New MCP Services
1. Update `MCPServiceType` enum in `mcp_manager.py`
2. Add service configuration to `config.py`
3. Implement payload builder in `_build_payload_for_service()`
4. Update service selection logic in `get_service_for_url()`

### Modifying AI Prompts
- System prompts are defined in `generate_development_plan_with_progress()`
- Includes strict requirements for Mermaid diagram generation
- Emphasizes security and prevents malicious link generation

### UI Customization
- Custom CSS is embedded in `app.py` starting at line ~1046
- Responsive design with dark mode support
- Progress tracking system with JavaScript integration

## Deployment

### ModelScope Platform
The application is specifically configured for ModelScope deployment:
- Gradio SDK with Docker runtime
- Proper port configuration (3000)
- Environment variable handling
- Health check endpoints

### Docker Configuration
- Multi-stage build for optimization
- Non-root user for security
- Health checks and graceful shutdown
- Volume mounting for persistent data

## Security Considerations

### Input Validation
- URL validation before MCP service calls
- User input sanitization for AI prompts
- Prevention of malicious link injection

### API Security
- Proper API key management
- Request timeout configurations
- Error message sanitization

## Performance Optimization

### Response Time Targets
- 30-second total generation time
- MCP service timeout: 30 seconds
- AI model response: 90 seconds maximum

### Caching Strategy
- MCP service response caching (15-minute TTL)
- Static content optimization
- Progressive loading for large responses

## Troubleshooting

### Common Issues
1. **API Key Not Found**: Ensure `SILICONFLOW_API_KEY` is set
2. **MCP Service Unavailable**: Check service URLs and network connectivity
3. **Generation Timeout**: Increase timeout values in config
4. **Docker Build Failures**: Verify requirements.txt and Python version

### Debug Mode
Enable debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Health Monitoring
Access service status: Check MCP service status in the application UI or via `mcp_manager.get_health_status()`

## Agent Application Features

This is a sophisticated Agent application that demonstrates:
- **Multi-service orchestration**: Intelligent routing between MCP services
- **Knowledge fusion**: Combining external knowledge sources with AI reasoning
- **Adaptive workflows**: Dynamic service selection based on input types
- **Error resilience**: Comprehensive fallback mechanisms
- **User experience**: Progress tracking and real-time feedback

The application showcases Agent capabilities by automatically determining the best combination of MCP services for each request and presenting unified, comprehensive results to users.