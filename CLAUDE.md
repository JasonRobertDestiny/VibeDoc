# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibeDoc is an AI-driven development plan generator designed for the Magic Tower MCP & Agent Challenge 2025. It's a sophisticated Agent application that converts creative ideas into comprehensive development plans within 60 seconds using intelligent MCP service orchestration.

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

# Test individual components
python -c "from streaming_manager import StreamingManager; print('StreamingManager OK')"
```

## Architecture Overview

### MCP Agent System
This is an **Agent application** that orchestrates multiple MCP servers with intelligent routing:
- **DeepWiki MCP**: Handles deepwiki.org content extraction and technical documentation
- **Fetch MCP**: Processes general web content (GitHub, educational sites, blogs)
- **Doubao MCP**: Provides image generation capabilities for logos/visuals

### Core Components
1. **app.py**: Main Gradio application with UI and business logic (~3800 lines)
2. **config.py**: Centralized configuration management with environment-based settings
3. **mcp_manager.py**: Intelligent MCP service router and manager with health monitoring
4. **streaming_manager.py**: Progress tracking and real-time feedback for AI generation
5. **prompt_optimizer.py**: AI-driven user input optimization and enhancement
6. **explanation_manager.py**: AI explainability and processing transparency system  
7. **plan_editor.py**: Interactive plan editing and prompt customization
8. **requirements.txt**: Python dependencies

### Key Files Structure
```
├── app.py                 # Main application entry point
├── config.py             # Configuration management
├── mcp_manager.py        # MCP service orchestration
├── streaming_manager.py  # Progress tracking & streaming
├── prompt_optimizer.py   # User input optimization
├── explanation_manager.py # AI explainability system
├── plan_editor.py        # Interactive editing features
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Multi-container setup
└── README.md           # Project documentation
```

### Core Architecture Pattern
The application follows a modular Agent architecture:
- **Configuration Layer**: `config.py` manages all environment-based settings
- **Service Layer**: `mcp_manager.py` handles MCP service discovery and routing
- **Business Layer**: `app.py` contains the main generation logic at `generate_development_plan()`
- **Enhancement Layer**: `prompt_optimizer.py`, `explanation_manager.py`, `plan_editor.py` for UX features
- **Presentation Layer**: Gradio UI with embedded CSS and JavaScript

## Configuration Management

### Environment Variables
- `SILICONFLOW_API_KEY` (required): API key for AI model access
- `DEEPWIKI_SSE_URL` (optional): DeepWiki MCP service endpoint
- `FETCH_SSE_URL` (optional): Fetch MCP service endpoint
- `DOUBAO_SSE_URL` (optional): Doubao MCP service endpoint
- `DOUBAO_API_KEY` (optional): Doubao service API key
- `PORT`: Application port (default: 3000)
- `NODE_ENV`: Environment mode (development/production)
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `MCP_TIMEOUT`: MCP service timeout in seconds (default: 30)

### Service Configuration
The application uses a sophisticated configuration system in `config.py`:
- Automatic MCP service discovery and health checking
- Feature toggles based on available services
- Environment-specific optimizations
- Service statistics and call history tracking

## MCP Integration Patterns

### Service Selection Logic
The system intelligently routes requests to appropriate MCP services via `mcp_manager.py`:
- **DeepWiki**: For `deepwiki.org` URLs
- **Fetch**: For GitHub, educational sites, and general web content
- **Multi-service**: For complex content requiring multiple knowledge sources
- **Doubao**: For image generation when enabled

### Error Handling & Fallbacks
- Graceful degradation when MCP services are unavailable
- Comprehensive error logging and user feedback
- Automatic service health monitoring with retry mechanisms
- Fallback to non-MCP generation when all services fail

## Development Guidelines

### Adding New MCP Services
1. Update `MCPServiceType` enum in `mcp_manager.py`
2. Add service configuration to `config.py` in `mcp_services` dict
3. Implement payload builder in `_build_payload_for_service()`
4. Update service selection logic in `get_service_for_url()`
5. Add health check support in service configuration

### Modifying AI Prompts
- System prompts are defined in `generate_development_plan()` function at app.py:626
- Includes strict requirements for Mermaid diagram generation
- Emphasizes security and prevents malicious link generation
- Quality scoring system implemented in `calculate_quality_score()`

### UI Customization
- Custom CSS is embedded in `app.py` starting at line ~1900
- Responsive design with dark mode support
- Progress tracking system with JavaScript integration
- Gradio Blocks interface defined at app.py:3127

### Working with Streaming
- `StreamingManager` class handles real-time progress updates
- Progress stages: validation → knowledge → analysis → generation → formatting → finalization
- Six-stage workflow with detailed progress feedback

### Enhanced Features Implementation
- **Prompt Optimization**: `prompt_optimizer.py` uses AI to enhance user input descriptions
- **AI Explainability**: `explanation_manager.py` provides transparent processing insights with SOP compliance
- **Interactive Editing**: `plan_editor.py` enables inline editing of generated prompts and plans
- **Copy Functionality**: Individual copy buttons for each generated prompt section
- **Link Handling**: Target="_blank" for external links to prevent navigation issues

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
- URL validation before MCP service calls via `validate_url()`
- User input sanitization for AI prompts
- Prevention of malicious link injection with quality scoring

### API Security
- Proper API key management through environment variables
- Request timeout configurations (30s MCP, 120s AI)
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
5. **Mermaid Rendering Issues**: Check for proper Mermaid syntax in generated content
6. **JavaScript Errors**: Check browser console, functions are registered to window object

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
- **AI Explainability**: Complete processing transparency with SOP compliance reporting
- **Interactive Enhancement**: Real-time prompt optimization and editing capabilities

The application showcases Agent capabilities by automatically determining the best combination of MCP services for each request and presenting unified, comprehensive results to users while maintaining full transparency in the AI decision-making process.