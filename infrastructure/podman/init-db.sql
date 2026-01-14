-- AI CyberX Database Initialization Script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial skill domains
INSERT INTO skill_domains (id, name, description, icon, color, "order") VALUES
(uuid_generate_v4(), 'Network Security', 'Understanding and securing computer networks', 'network', '#00d4ff', 1),
(uuid_generate_v4(), 'Web Security', 'Web application security and OWASP vulnerabilities', 'globe', '#ff6b6b', 2),
(uuid_generate_v4(), 'System Security', 'Operating system hardening and security', 'server', '#4ecdc4', 3),
(uuid_generate_v4(), 'Cryptography', 'Encryption, hashing, and secure communications', 'lock', '#a855f7', 4),
(uuid_generate_v4(), 'Digital Forensics', 'Investigation and evidence analysis', 'search', '#f59e0b', 5),
(uuid_generate_v4(), 'Malware Analysis', 'Analysis and reverse engineering of malware', 'bug', '#ef4444', 6),
(uuid_generate_v4(), 'Cloud Security', 'Securing cloud infrastructure and services', 'cloud', '#3b82f6', 7),
(uuid_generate_v4(), 'SOC Operations', 'Security operations and threat monitoring', 'shield', '#10b981', 8)
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cyberx;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cyberx;
