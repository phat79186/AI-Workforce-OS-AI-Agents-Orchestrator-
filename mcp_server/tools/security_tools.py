"""Security scanning MCP tools for vulnerability detection."""

import logging
import re
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)


async def scan_secrets(
    ctx: Context, directory: str, include_patterns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Scan directory for potential secrets and credentials.

    Args:
        ctx: MCP context
        directory: Directory to scan
        include_patterns: File patterns to include (default: common code files)

    Returns:
        Found potential secrets with file locations and recommendations.
    """
    if include_patterns is None:
        include_patterns = [
            "*.py",
            "*.js",
            "*.ts",
            "*.json",
            "*.yaml",
            "*.yml",
            "*.env*",
            "*.conf",
            "*.cfg",
        ]

    secret_patterns = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', "API Key"),
        (
            r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
            "Secret Key",
        ),
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', "Password"),
        (r'(?i)(token)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', "Token"),
        (r"(?i)bearer\s+([a-zA-Z0-9_\-\.]+)", "Bearer Token"),
        (
            r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[=:]\s*["\']?([A-Z0-9]{20})["\']?',
            "AWS Access Key",
        ),
        (
            r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?',
            "AWS Secret Key",
        ),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Token"),
        (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
        (r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----", "Private Key"),
    ]

    findings: List[Dict[str, Any]] = []

    import glob

    for pattern in include_patterns:
        for file_path in glob.glob(f"{directory}/**/{pattern}", recursive=True):
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                for secret_pattern, secret_type in secret_patterns:
                    for i, line in enumerate(lines, 1):
                        if re.search(secret_pattern, line):
                            # Mask the actual secret
                            masked = re.sub(
                                secret_pattern, lambda m: f"{m.group(1)}=***REDACTED***", line
                            )
                            findings.append(
                                {
                                    "file": file_path,
                                    "line": i,
                                    "type": secret_type,
                                    "masked_content": masked[:100],
                                    "severity": "HIGH",
                                }
                            )
            except Exception as e:  # noqa: B112
                # Skip files that cannot be parsed, log and continue
                logger.warning("Could not parse %s: %s", file_path, e)
                continue

    # Group by type
    by_type: Dict[str, int] = {}
    for finding in findings:
        t = finding["type"]
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "by_type": by_type,
            "high_severity": sum(1 for f in findings if f["severity"] == "HIGH"),
        },
        "recommendations": [
            "Use environment variables for sensitive values",
            "Add .env files to .gitignore",
            "Consider using a secrets manager (AWS Secrets Manager, HashiCorp Vault)",
            "Rotate any exposed credentials immediately",
        ],
    }


async def detect_injection_vulnerabilities(ctx: Context, file_path: str) -> Dict[str, Any]:
    """Detect potential injection vulnerabilities in code.

    Args:
        ctx: MCP context
        file_path: Path to file to analyze

    Returns:
        Found injection vulnerabilities with severity and recommendations.
    """
    vulnerabilities: List[Dict[str, Any]] = []

    injection_patterns = [
        # SQL Injection
        (
            r'execute\s*\(\s*["\'].*%s|execute\s*\(\s*f["\']|\.format\s*\(.*\)\s*\)',
            "SQL Injection",
            "HIGH",
            "Use parameterized queries",
        ),
        (
            r'cursor\.execute\s*\(\s*[f"\'].*\{',
            "SQL Injection (f-string)",
            "HIGH",
            "Use parameterized queries instead of f-strings",
        ),
        # Command Injection
        (
            r"subprocess\.(run|call|Popen)\s*\(.*shell\s*=\s*True",
            "Command Injection",
            "HIGH",
            "Avoid shell=True, use list arguments",
        ),
        (
            r"os\.system\s*\(",
            "Command Injection",
            "HIGH",
            "Use subprocess with shell=False instead",
        ),
        (r"eval\s*\(", "Code Injection", "CRITICAL", "Never use eval with user input"),
        (r"exec\s*\(", "Code Injection", "CRITICAL", "Never use exec with user input"),
        # XSS
        (
            r"innerHTML\s*=|document\.write\s*\(",
            "XSS",
            "MEDIUM",
            "Use textContent or sanitize input",
        ),
        # Path Traversal
        (
            r"open\s*\(\s*[^\)]*\+|os\.path\.join\s*\([^,]+,\s*[a-zA-Z_]+\s*\)",
            "Path Traversal",
            "MEDIUM",
            "Validate and sanitize file paths",
        ),
        # LDAP Injection
        (
            r"ldap\.search\s*\(.*%|ldap\.search\s*\(.*\.format",
            "LDAP Injection",
            "HIGH",
            "Use parameterized LDAP queries",
        ),
        # XML Injection
        (
            r"etree\.parse\s*\(|xml\.parse\s*\(",
            "XXE",
            "MEDIUM",
            "Disable external entity processing",
        ),
    ]

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

        for pattern, vuln_type, severity, recommendation in injection_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    vulnerabilities.append(
                        {
                            "file": file_path,
                            "line": i,
                            "type": vuln_type,
                            "severity": severity,
                            "content": line.strip()[:80],
                            "recommendation": recommendation,
                        }
                    )

    except Exception as e:
        return {"error": str(e), "file": file_path}

    return {
        "vulnerabilities": vulnerabilities,
        "summary": {
            "total": len(vulnerabilities),
            "critical": sum(1 for v in vulnerabilities if v["severity"] == "CRITICAL"),
            "high": sum(1 for v in vulnerabilities if v["severity"] == "HIGH"),
            "medium": sum(1 for v in vulnerabilities if v["severity"] == "MEDIUM"),
        },
    }


async def check_security_headers(ctx: Context, code_path: str) -> Dict[str, Any]:
    """Check for security header configurations in web application code.

    Args:
        ctx: MCP context
        code_path: Path to web application code

    Returns:
        Analysis of security headers and recommendations.
    """
    security_headers = {
        "Content-Security-Policy": {
            "patterns": [r"Content-Security-Policy", r"csp", r"contentSecurityPolicy"],
            "importance": "HIGH",
            "description": "Prevents XSS and injection attacks",
        },
        "X-Frame-Options": {
            "patterns": [r"X-Frame-Options", r"xFrameOptions", r"frame.*options"],
            "importance": "HIGH",
            "description": "Prevents clickjacking attacks",
        },
        "X-Content-Type-Options": {
            "patterns": [r"X-Content-Type-Options", r"nosniff"],
            "importance": "MEDIUM",
            "description": "Prevents MIME type sniffing",
        },
        "Strict-Transport-Security": {
            "patterns": [r"Strict-Transport-Security", r"hsts"],
            "importance": "HIGH",
            "description": "Enforces HTTPS",
        },
        "X-XSS-Protection": {
            "patterns": [r"X-XSS-Protection", r"xssProtection"],
            "importance": "LOW",
            "description": "Legacy XSS filter (deprecated in favor of CSP)",
        },
        "Referrer-Policy": {
            "patterns": [r"Referrer-Policy", r"referrerPolicy"],
            "importance": "MEDIUM",
            "description": "Controls referrer information",
        },
        "Permissions-Policy": {
            "patterns": [r"Permissions-Policy", r"Feature-Policy", r"permissionsPolicy"],
            "importance": "MEDIUM",
            "description": "Controls browser features",
        },
    }

    found_headers: List[str] = []
    missing_headers: List[str] = []

    import glob

    py_files = glob.glob(f"{code_path}/**/*.py", recursive=True)
    js_files = glob.glob(f"{code_path}/**/*.js", recursive=True)
    config_files = (
        glob.glob(f"{code_path}/**/*.json", recursive=True)
        + glob.glob(f"{code_path}/**/*.yaml", recursive=True)
        + glob.glob(f"{code_path}/**/*.yml", recursive=True)
        + glob.glob(f"{code_path}/**/*.conf", recursive=True)
    )

    all_files = py_files + js_files + config_files

    for header, info in security_headers.items():
        found = False
        for file_path in all_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                for pattern in info["patterns"]:
                    if re.search(pattern, content, re.IGNORECASE):
                        found = True
                        break
                if found:
                    break
            except Exception as e:  # noqa: B112
                # Skip files that cannot be parsed, log and continue
                logger.warning("Could not parse file: %s", e)
                continue

        if found:
            found_headers.append(header)
        else:
            missing_headers.append(header)

    return {
        "found_headers": found_headers,
        "missing_headers": missing_headers,
        "recommendations": [
            {
                "header": h,
                "importance": security_headers[h]["importance"],
                "description": security_headers[h]["description"],
            }
            for h in missing_headers
        ],
        "score": len(found_headers) / len(security_headers) * 100 if security_headers else 0,
    }


async def run_security_audit(ctx: Context, directory: str) -> Dict[str, Any]:
    """Run comprehensive security audit on codebase.

    Args:
        ctx: MCP context
        directory: Directory to audit

    Returns:
        Comprehensive security audit results.
    """
    audit_results: Dict[str, Any] = {
        "directory": directory,
        "checks": [],
        "summary": {"total_issues": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
    }

    # Check for common security issues
    checks = [
        {
            "name": "Debug Mode",
            "pattern": r'DEBUG\s*=\s*True|"debug"\s*:\s*true',
            "severity": "HIGH",
            "message": "Debug mode enabled",
        },
        {
            "name": "Hardcoded Credentials",
            "pattern": r'(password|secret|key)\s*=\s*["\'][^"\']+["\']',
            "severity": "CRITICAL",
            "message": "Possible hardcoded credentials",
        },
        {
            "name": "Insecure Protocol",
            "pattern": r"http://(?!localhost|127\.0\.0\.1)",
            "severity": "MEDIUM",
            "message": "HTTP used instead of HTTPS",
        },
        {
            "name": "Weak Crypto",
            "pattern": r"md5|sha1(?!ng)|DES|RC4",
            "severity": "HIGH",
            "message": "Weak cryptographic algorithm",
        },
        {
            "name": "CORS Wildcard",
            "pattern": r"Access-Control-Allow-Origin.*\*|cors.*origin.*\*",
            "severity": "MEDIUM",
            "message": "CORS allows all origins",
        },
        {
            "name": "No Input Validation",
            "pattern": r"request\.(args|form|json)\[|request\.get\(",
            "severity": "MEDIUM",
            "message": "Direct request data access without validation",
        },
    ]

    import glob

    py_files = glob.glob(f"{directory}/**/*.py", recursive=True)
    issues: List[Dict[str, Any]] = []

    for file_path in py_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            for check in checks:
                for i, line in enumerate(lines, 1):
                    if re.search(check["pattern"], line, re.IGNORECASE):
                        issues.append(
                            {
                                "file": file_path,
                                "line": i,
                                "check": check["name"],
                                "severity": check["severity"],
                                "message": check["message"],
                                "content": line.strip()[:80],
                            }
                        )
        except Exception as e:  # noqa: B112
            # Skip files that cannot be parsed, log and continue
            logger.warning("Could not parse %s: %s", file_path, e)
            continue

    audit_results["issues"] = issues
    audit_results["summary"]["total_issues"] = len(issues)

    for issue in issues:
        sev = issue["severity"].lower()
        audit_results["summary"][sev] = audit_results["summary"].get(sev, 0) + 1

    return audit_results


def register_security_tools(mcp: Any) -> None:
    """Register security tools with MCP server."""
    mcp.tool()(scan_secrets)
    mcp.tool()(detect_injection_vulnerabilities)
    mcp.tool()(check_security_headers)
    mcp.tool()(run_security_audit)


# Aliases for backward compatibility
scan_injection_risks = detect_injection_vulnerabilities
audit_dependencies_security = run_security_audit
