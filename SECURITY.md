# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :x:                |
| 1.0.x   | :x:                |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow responsible disclosure:

### How to Report

**Do NOT open a public issue.** Instead, please:

1. Email the maintainers directly at [INSERT SECURITY EMAIL]
2. Include "Security Vulnerability" in the subject line
3. Provide detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Development**: Depends on severity and complexity
- **Disclosure**: After fix is released, we'll publish a security advisory

### Responsible Disclosure Guidelines

- Give us reasonable time to fix the issue before public disclosure
- Do not access or modify other users' data
- Do not perform testing on production systems without permission
- Provide enough detail to reproduce and verify the issue

## Security Best Practices

When using Media Downloader:

### Dependencies

We regularly update dependencies to address known vulnerabilities. Keep your installation updated:

```bash
# Using uv
uv sync

# Using pip
pip install -r requirements.txt --upgrade
```

### Cookies and Authentication

Media Downloader handles authentication tokens and cookies:

- **Never share** your cookie files or session tokens
- **Be cautious** when sharing logs that might contain sensitive data
- **Use the app** only on trusted networks
- **Report** any suspicious behavior immediately

### Downloaded Content

- Scan downloaded files with antivirus software
- Be cautious of executable files from untrusted sources
- Media Downloader downloads from third-party platforms - verify content safety

### Network Security

- The app makes network requests to download media
- Avoid using on public/unsecured networks for sensitive content
- Proxy settings are supported for enhanced privacy

## Known Security Considerations

### Third-Party Platforms

Media Downloader interacts with third-party platforms (YouTube, Spotify, etc.):

- These platforms have their own security and privacy policies
- Authentication credentials are stored locally
- Network traffic goes through these platforms' APIs

### Local Storage

Configuration and credentials are stored in:
- `~/.media_downloader/` (config, cookies, sessions)
- These files contain sensitive information - protect them
- Do not share these directories or commit them to version control

### Browser Integration

Cookie extraction reads from your browser's cookie storage:
- This requires appropriate permissions
- Cookies are used only for authentication with respective platforms
- No data is transmitted to third parties

## Security Updates

Security updates are released as patch versions (e.g., 1.2.1 → 1.2.2) and are announced via:

- GitHub Security Advisories
- Release notes
- GitHub Releases page

We recommend enabling GitHub Watch notifications for security updates.

## Contact

For security concerns:
- **Security Issues**: [INSERT SECURITY EMAIL]
- **General Questions**: Open a GitHub Discussion
- **Bug Reports**: Open a GitHub Issue (non-security only)

Thank you for helping keep Media Downloader secure! 🛡️
