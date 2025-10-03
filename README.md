# 🚀 VibeDoc: Your AI Product Manager & Architect

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/Gradio-5.34.1-orange)](https://gradio.app/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

<div align="center">

**Transform Ideas into Complete Development Plans in 60-180 Seconds**

AI-powered Product Manager & Software Architect that generates technical documentation, architecture diagrams, and AI coding prompts

[🎬 Demo Video](https://www.bilibili.com/video/BV1ieagzQEAC/) | [🤝 Contributing](./CONTRIBUTING.md) | [💬 Discussions](https://github.com/JasonRobertDestiny/VibeDoc/discussions) | [中文文档](./README.zh.md)

</div>

---

## ✨ Why VibeDoc?

As a developer, product manager, or entrepreneur, you face these challenges:

- 💭 **Great Ideas, No Plan?** You have ideas but don't know how to turn them into actionable development plans
- ⏰ **Documentation Takes Forever?** Writing technical specs and architecture docs consumes massive time
- 🤖 **AI Tools Confusing?** You want AI-assisted coding but struggle with effective prompt engineering
- 📊 **Missing Professional Diagrams?** You need architecture, flow, and Gantt charts but lack design tools expertise

**VibeDoc Solves Everything!**

![VibeDoc Interface](./image/vibedoc.png)

## 🎯 Core Features

### 📋 Intelligent Development Plan Generation

Enter your product idea - AI generates a complete plan in 60-180 seconds:

- **Product Overview** - Background, target users, core value proposition
- **Technical Solution** - Tech stack selection, architecture design, technology comparison
- **Development Plan** - Phased implementation, timeline, resource allocation
- **Deployment Strategy** - Environment setup, CI/CD pipeline, operations monitoring
- **Growth Strategy** - Market positioning, operations advice, growth tactics

### 🤖 AI Coding Prompt Generation

Generate ready-to-use prompts for each feature module, supporting:

- ✅ **Claude** - Code generation, architecture design
- ✅ **GitHub Copilot** - Intelligent code completion
- ✅ **ChatGPT** - Technical consultation, code optimization
- ✅ **Cursor** - AI-assisted programming

![AI Coding Prompts](./image/1.png)

### 📊 Auto-Generated Visual Diagrams

Professional diagrams using Mermaid:

- 🏗️ **System Architecture** - Component relationships visualization
- 📈 **Business Flowcharts** - Business logic visualization
- 📅 **Gantt Charts** - Project timeline at a glance
- 📊 **Tech Comparison Tables** - Technology decision reference

### 📁 Multi-Format Export

One-click export for different scenarios:

- **Markdown** (.md) - Version control friendly, GitHub display
- **Word** (.docx) - Business documents, project reports
- **PDF** (.pdf) - Formal proposals, print archives
- **HTML** (.html) - Web display, online sharing

![Generated Example](./image/2.png)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip package manager
- [SiliconFlow API Key](https://siliconflow.cn) (free to obtain)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/JasonRobertDestiny/VibeDoc.git
cd VibeDoc

# 2. Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env file and add your API Key
```

### Configuration

In `.env` file:

```env
# Required: SiliconFlow API Key (free registration)
SILICONFLOW_API_KEY=your_api_key_here

# Optional: Advanced Configuration
API_TIMEOUT=300
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Run Application

```bash
python app.py
```

Application starts at:
- Local: http://localhost:7860
- Network: http://0.0.0.0:7860

### 🐳 Docker Deployment (Optional)

```bash
# Build image
docker build -t vibedoc .

# Run container
docker run -p 7860:7860 \
  -e SILICONFLOW_API_KEY=your_key \
  vibedoc
```

## 💡 Usage Examples

### Example 1: Web Application

**Input:**
```
Develop an online collaborative document editor with real-time
multi-user editing, version management, and commenting features,
similar to Google Docs
```

**Generated Output:**
- Complete tech stack (React + Node.js + WebSocket)
- 6-month development roadmap with 3 milestones
- 10+ ready-to-use AI coding prompts
- Architecture diagrams, flowcharts, Gantt charts

### Example 2: AI Application

**Input:**
```
Intelligent customer service system: multi-turn dialogue,
sentiment analysis, knowledge base search, automatic ticket
generation, smart reply recommendations
```

**Output:**
- LLM-based dialogue system architecture
- Knowledge base construction and retrieval solution
- Sentiment analysis model integration
- Complete implementation roadmap

## 🏗️ Technical Architecture

Modular architecture design:

```
┌─────────────────────────────────────────┐
│         Gradio Web Interface            │
│   (User Interaction + UI + Export)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Core Processing Engine            │
├─────────────────────────────────────────┤
│  • Input Validation & Optimization      │
│  • AI Generation Coordination           │
│  • Content Quality Control              │
│  • Multi-format Export                  │
└──┬────────┬──────────┬─────────┬────────┘
   │        │          │         │
   ▼        ▼          ▼         ▼
┌──────┐ ┌────────┐ ┌──────┐ ┌──────────┐
│ AI   │ │Prompt  │ │Content│ │Export    │
│Model │ │Optimizer│ │Validator│ │Manager   │
└──────┘ └────────┘ └──────┘ └──────────┘
```

### Technology Stack

- **Frontend**: Gradio 5.34.1 - Fast AI app interface
- **AI Model**: Qwen2.5-72B-Instruct - Alibaba Cloud
- **Chart Rendering**: Mermaid.js - Code-based diagrams
- **Document Export**: python-docx, reportlab
- **Async Processing**: asyncio, aiofiles

## 📊 Performance Metrics

| Metric | Performance |
|--------|-------------|
| **Generation Speed** | 60-180 seconds |
| **Success Rate** | >95% |
| **Content Quality** | 85/100 average |
| **Export Formats** | 4 formats |

## 🎨 Use Cases

### 👨‍💻 Developers
- ✅ Validate technical feasibility quickly
- ✅ Generate project documentation
- ✅ Get AI coding prompts
- ✅ Learn architecture best practices

### 📊 Product Managers
- ✅ Transform requirements into technical solutions
- ✅ Create project planning documents
- ✅ Estimate development cycles
- ✅ Build project proposals

### 🎓 Students & Learners
- ✅ Learn software development best practices
- ✅ Understand architecture design
- ✅ Prepare for technical interviews
- ✅ Plan graduation projects

### 🚀 Entrepreneurs
- ✅ Validate product ideas quickly
- ✅ Generate technical plans for investors
- ✅ Plan MVP development
- ✅ Assess implementation costs

## 🤝 Contributing

We welcome all contributions:

- 🐛 Report Bugs
- 💡 Suggest Features
- 📝 Improve Documentation
- 🔧 Submit Code

### Steps

1. Fork this project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Submit Pull Request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## 📝 Documentation

- [User Guide](./USER_GUIDE.md) - Detailed instructions
- [Technical Docs](./CLAUDE.md) - Architecture & development
- [Deployment Guide](./DEPLOYMENT.md) - Production deployment
- [Security Policy](./SECURITY.md) - Security best practices

## 🎯 Roadmap

### v2.1 (Planned)
- [ ] More AI models (GPT-4, Claude, etc.)
- [ ] Team collaboration features
- [ ] Version management
- [ ] Online editor

### v2.2 (Planned)
- [ ] Mobile support
- [ ] Multi-language (English, Japanese)
- [ ] Template marketplace
- [ ] API interface

## 🙏 Acknowledgments

- **Qwen2.5-72B-Instruct** by Alibaba Cloud
- **Gradio** team
- **SiliconFlow** API services
- All contributors and users ❤️

## 📄 License

[MIT License](LICENSE)

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/JasonRobertDestiny/VibeDoc/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JasonRobertDestiny/VibeDoc/discussions)
- **Email**: johnrobertdestiny@gmail.com
- **Demo**: [Bilibili](https://www.bilibili.com/video/BV1ieagzQEAC/)

## ⭐ Star History

If this project helps you, give us a Star ⭐!

[![Star History Chart](https://api.star-history.com/svg?repos=JasonRobertDestiny/VibeDoc&type=Date)](https://star-history.com/#JasonRobertDestiny/VibeDoc&Date)

---

<div align="center">

**🚀 Empower Every Idea with AI**

Made with ❤️ by the VibeDoc Team

</div>
