import os
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PDFPlumberLoader,
    UnstructuredMarkdownLoader,
    JSONLoader,
)

from app.core.config import settings

logger = structlog.get_logger()


class DocumentProcessor:
    """Process documents for the RAG knowledge base."""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        self.loaders = {
            ".txt": TextLoader,
            ".md": UnstructuredMarkdownLoader,
            ".pdf": PDFPlumberLoader,
            ".json": JSONLoader,
        }

    def load_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Load a document from file path."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self.loaders:
            logger.warning(f"Unsupported file type: {extension}")
            return []

        try:
            loader_class = self.loaders[extension]
            if extension == ".json":
                loader = loader_class(file_path, jq_schema=".", text_content=False)
            else:
                loader = loader_class(file_path)

            documents = loader.load()
            return [
                {
                    "content": doc.page_content,
                    "metadata": {
                        **doc.metadata,
                        "source": file_path,
                        "file_type": extension,
                    },
                }
                for doc in documents
            ]
        except Exception as e:
            logger.error(f"Failed to load document: {file_path}", error=str(e))
            return []

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Split text into chunks."""
        chunks = self.text_splitter.split_text(text)

        return [
            {
                "content": chunk,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": i,
                    "chunk_id": self._generate_chunk_id(chunk),
                },
            }
            for i, chunk in enumerate(chunks)
        ]

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and chunk a document."""
        documents = self.load_document(file_path)
        all_chunks = []

        for doc in documents:
            chunks = self.chunk_text(doc["content"], doc["metadata"])
            all_chunks.extend(chunks)

        logger.info(f"Processed document: {file_path}", chunks=len(all_chunks))
        return all_chunks

    def process_text(
        self,
        text: str,
        source: str = "direct_input",
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Process raw text into chunks."""
        metadata = {
            "source": source,
            "title": title,
            "category": category,
        }
        return self.chunk_text(text, metadata)

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all documents in a directory."""
        all_chunks = []
        path = Path(directory_path)

        if not path.exists():
            logger.error(f"Directory not found: {directory_path}")
            return []

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.loaders:
                chunks = self.process_document(str(file_path))
                all_chunks.extend(chunks)

        logger.info(f"Processed directory: {directory_path}", total_chunks=len(all_chunks))
        return all_chunks

    def _generate_chunk_id(self, content: str) -> str:
        """Generate a unique ID for a chunk."""
        return hashlib.md5(content.encode()).hexdigest()[:12]


# Cybersecurity knowledge sources
CYBERSECURITY_SOURCES = {
    "owasp": {
        "title": "OWASP Top 10",
        "category": "web_security",
        "content": """
# OWASP Top 10 Web Application Security Risks

## A01:2021 - Broken Access Control
Access control enforces policy such that users cannot act outside of their intended permissions.
Failures typically lead to unauthorized information disclosure, modification, or destruction of data.

Common vulnerabilities:
- Violation of the principle of least privilege
- Bypassing access control checks by modifying the URL
- Insecure direct object references (IDOR)
- Missing access controls for POST, PUT and DELETE

## A02:2021 - Cryptographic Failures
Previously known as Sensitive Data Exposure. Focus on failures related to cryptography.
- Is any data transmitted in clear text?
- Are deprecated cryptographic algorithms used?
- Are default crypto keys in use?

## A03:2021 - Injection
SQL, NoSQL, OS command, ORM, LDAP, and Expression Language injection.
User-supplied data is not validated, filtered, or sanitized by the application.
Prevention: Use parameterized queries and ORMs.

## A04:2021 - Insecure Design
A new category focusing on risks related to design and architectural flaws.
Secure design patterns and threat modeling are essential.

## A05:2021 - Security Misconfiguration
- Missing appropriate security hardening
- Unnecessary features enabled
- Default accounts and passwords unchanged
- Error handling reveals stack traces

## A06:2021 - Vulnerable and Outdated Components
Using components with known vulnerabilities.
Requires continuous inventory and monitoring of dependencies.

## A07:2021 - Identification and Authentication Failures
Session management and authentication weaknesses.
- Permits brute force attacks
- Weak password policies
- Missing multi-factor authentication

## A08:2021 - Software and Data Integrity Failures
Code and infrastructure that does not protect against integrity violations.
CI/CD pipeline security and software supply chain attacks.

## A09:2021 - Security Logging and Monitoring Failures
Without logging and monitoring, breaches cannot be detected.
Ensure auditable events are logged with appropriate context.

## A10:2021 - Server-Side Request Forgery (SSRF)
SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.
""",
    },
    "mitre_attack": {
        "title": "MITRE ATT&CK Framework",
        "category": "threat_intelligence",
        "content": """
# MITRE ATT&CK Framework

## Overview
ATT&CK (Adversarial Tactics, Techniques, and Common Knowledge) is a knowledge base of adversary behavior.

## Tactics (The "Why")
1. **Reconnaissance** - Gathering information for planning
2. **Resource Development** - Establishing resources for operations
3. **Initial Access** - Getting into the network
4. **Execution** - Running malicious code
5. **Persistence** - Maintaining foothold
6. **Privilege Escalation** - Gaining higher-level permissions
7. **Defense Evasion** - Avoiding detection
8. **Credential Access** - Stealing credentials
9. **Discovery** - Learning about the environment
10. **Lateral Movement** - Moving through the network
11. **Collection** - Gathering data of interest
12. **Command and Control** - Communicating with compromised systems
13. **Exfiltration** - Stealing data
14. **Impact** - Manipulating, interrupting, or destroying systems

## Common Techniques

### Initial Access
- T1566: Phishing
- T1190: Exploit Public-Facing Application
- T1078: Valid Accounts
- T1133: External Remote Services

### Persistence
- T1547: Boot or Logon Autostart Execution
- T1053: Scheduled Task/Job
- T1136: Create Account
- T1543: Create or Modify System Process

### Privilege Escalation
- T1068: Exploitation for Privilege Escalation
- T1055: Process Injection
- T1548: Abuse Elevation Control Mechanism

### Defense Evasion
- T1070: Indicator Removal
- T1036: Masquerading
- T1027: Obfuscated Files or Information

### Credential Access
- T1110: Brute Force
- T1003: OS Credential Dumping
- T1555: Credentials from Password Stores
""",
    },
    "penetration_testing": {
        "title": "Penetration Testing Methodology",
        "category": "pentesting",
        "content": """
# Penetration Testing Methodology

## Phase 1: Planning and Reconnaissance

### Passive Reconnaissance
- OSINT gathering
- WHOIS lookups
- DNS enumeration
- Social media analysis
- Google dorking

### Active Reconnaissance
- Port scanning (Nmap)
- Service enumeration
- Banner grabbing
- Vulnerability scanning

## Phase 2: Scanning and Enumeration

### Network Scanning
```bash
# Full TCP port scan
nmap -sS -p- -T4 target

# Service version detection
nmap -sV -sC -p 22,80,443 target

# UDP scan
nmap -sU --top-ports 100 target
```

### Web Application Scanning
- Directory enumeration (gobuster, dirb)
- Technology fingerprinting (Wappalyzer)
- Vulnerability scanning (Nikto, OWASP ZAP)

## Phase 3: Exploitation

### Common Attack Vectors
- SQL Injection
- Cross-Site Scripting (XSS)
- Remote Code Execution
- Authentication bypass
- File upload vulnerabilities

### Tools
- Metasploit Framework
- Burp Suite
- SQLMap
- Hydra (brute force)

## Phase 4: Post-Exploitation

### Privilege Escalation
- Linux: SUID binaries, kernel exploits, sudo misconfigs
- Windows: Unquoted service paths, AlwaysInstallElevated

### Lateral Movement
- Pass-the-hash
- Token impersonation
- RDP hijacking

### Maintaining Access
- Backdoors
- Scheduled tasks
- SSH keys

## Phase 5: Reporting

### Report Structure
1. Executive Summary
2. Methodology
3. Findings (sorted by risk)
4. Remediation recommendations
5. Technical appendix
""",
    },
    "linux_security": {
        "title": "Linux Security Fundamentals",
        "category": "system_security",
        "content": """
# Linux Security Fundamentals

## File Permissions

### Understanding Permissions
- r (read) = 4
- w (write) = 2
- x (execute) = 1

```bash
# View permissions
ls -la

# Change permissions
chmod 755 file.sh
chmod u+x script.sh

# Change ownership
chown user:group file
```

### Special Permissions
- SUID (4): Execute as file owner
- SGID (2): Execute as group owner
- Sticky bit (1): Only owner can delete

## User Management

```bash
# Add user
useradd -m -s /bin/bash username

# Add to sudo group
usermod -aG sudo username

# Lock account
passwd -l username

# Check user info
id username
```

## Service Hardening

### SSH Hardening
```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
MaxAuthTries 3
Protocol 2
```

### Firewall (iptables/nftables)
```bash
# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Drop all other incoming
iptables -P INPUT DROP
```

## Log Analysis

### Important Log Files
- /var/log/auth.log - Authentication logs
- /var/log/syslog - System logs
- /var/log/apache2/ - Web server logs
- /var/log/secure - Security events (RHEL)

### Log Analysis Commands
```bash
# Find failed SSH attempts
grep "Failed password" /var/log/auth.log

# Find successful logins
grep "Accepted" /var/log/auth.log

# Watch logs in real-time
tail -f /var/log/syslog
```

## Security Tools

### System Auditing
- Lynis: Security auditing tool
- AIDE: File integrity monitoring
- ClamAV: Antivirus scanner

### Network Security
- fail2ban: Brute force protection
- ufw: Uncomplicated firewall
- tcpdump: Packet capture
""",
    },
}


def get_initial_knowledge_base() -> List[Dict[str, Any]]:
    """Get initial cybersecurity knowledge base documents."""
    processor = DocumentProcessor()
    all_chunks = []

    for source_id, source_data in CYBERSECURITY_SOURCES.items():
        chunks = processor.process_text(
            text=source_data["content"],
            source=source_id,
            title=source_data["title"],
            category=source_data["category"],
        )
        all_chunks.extend(chunks)

    return all_chunks
