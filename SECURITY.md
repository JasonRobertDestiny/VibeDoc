# Security Policy

## 🔒 Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.5.x   | :white_check_mark: |
| < 1.5   | :x:                |

## 🐛 Reporting a Vulnerability

We take the security of VibeDoc seriously. If you discover a security vulnerability, please follow these steps:

### 1. **Do Not** Open a Public Issue

Security vulnerabilities should not be disclosed publicly until a fix is available.

### 2. Report Privately

Please report security vulnerabilities by emailing:

**johnrobertdestinv@gmail.com**

Include the following information:
- Type of vulnerability
- Affected component(s)
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Varies by severity

## 🛡️ Security Measures

### Application Security

- **Input Validation**: All user inputs are sanitized
- **API Key Protection**: Environment variables only
- **HTTPS**: Enforced for all external communications
- **Rate Limiting**: Protection against abuse
- **Error Handling**: No sensitive data in error messages

### Data Privacy

- **No Storage**: We don't store user data permanently
- **Temporary Files**: Auto-deleted after session
- **API Keys**: Never logged or exposed
- **External Services**: Minimal data sharing

### Dependencies

- **Regular Updates**: Dependencies updated monthly
- **Security Scanning**: Automated vulnerability checks
- **License Compliance**: All dependencies vetted

## 🔐 Best Practices for Users

### API Key Security

```bash
# ✅ Good: Use environment variables
export SILICONFLOW_API_KEY=your_key_here

# ❌ Bad: Never commit API keys
SILICONFLOW_API_KEY=sk-xxxxx  # Don't do this!
```

### Deployment Security

```bash
# Use strong passwords for production deployments
# Regularly update the application
# Monitor logs for suspicious activity
# Use HTTPS in production
```

### Docker Security

```dockerfile
# Run as non-root user
USER nonroot

# Use specific versions
FROM python:3.11-slim

# Scan images regularly
docker scan vibedoc:latest
```

## 📋 Security Checklist

Before deploying to production:

- [ ] API keys stored securely (environment variables)
- [ ] HTTPS enabled
- [ ] Rate limiting configured
- [ ] Logging enabled and monitored
- [ ] Dependencies updated
- [ ] Security headers configured
- [ ] Access controls in place
- [ ] Backup strategy implemented

## 🔄 Security Updates

We announce security updates through:

- **GitHub Security Advisories**
- **Release Notes**
- **Email Notifications** (for critical issues)

Subscribe to releases to stay informed: [Watch Repository → Releases](https://github.com/JasonRobertDestiny/VibeDoc/releases)

## 📞 Contact

For security concerns:
- **Email**: johnrobertdestinv@gmail.com (Security Team)
- **PGP Key**: Available on request

For general inquiries:
- **Email**: johnrobertdestinv@gmail.com
- **GitHub Issues**: For non-security bugs
- **Demo Video**: [Watch on Bilibili](https://www.bilibili.com/video/BV1ieagzQEAC/)

## 🙏 Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged (with permission) in our security advisories.

---

**Thank you for helping keep VibeDoc secure!** 🛡️
