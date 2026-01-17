import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import {
  GraduationCap,
  Sparkles,
  Brain,
  BookOpen,
  Beaker,
  Target,
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  ChevronRight,
  ChevronDown,
  Play,
  Clock,
  Award,
  Zap,
  Shield,
  Code,
  Network,
  Bug,
  Server,
  Globe,
  Database,
  Eye,
  Key,
  Wifi,
  Cloud,
  Smartphone,
  FileSearch,
  AlertCircle,
  Search,
  Filter,
  Minimize2,
  Maximize2
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi } from '@/services/api';

interface CourseGenerationState {
  isGenerating: boolean;
  topic: string;
  error: string | null;
  success: { courseId: string; courseSlug: string; labId?: string; labSlug?: string } | null;
  jobId: string | null;
  progress: {
    stage: string;
    percent: number;
    currentLesson: string | null;
    message: string;
  } | null;
}

interface GenerationOptions {
  includeCodeExamples: boolean;
  includeDiagrams: boolean;
  includeVideos: boolean;
  includeWikipedia: boolean;
  includeQuizzes: boolean;
  numModules: number;
  targetLessonLength: number;
}

interface TopicCategory {
  name: string;
  icon: any;
  color: string;
  topics: string[];
}

// Comprehensive cybersecurity topics catalog
const topicCategories: TopicCategory[] = [
  {
    name: 'Web Application Security',
    icon: Globe,
    color: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
    topics: [
      'SQL Injection Attacks',
      'Cross-Site Scripting (XSS)',
      'Cross-Site Request Forgery (CSRF)',
      'Server-Side Request Forgery (SSRF)',
      'XML External Entity (XXE)',
      'Insecure Direct Object References (IDOR)',
      'Authentication Bypass Techniques',
      'Session Hijacking',
      'JWT Token Attacks',
      'OAuth Security Vulnerabilities',
      'API Security Testing',
      'GraphQL Security',
      'WebSocket Security',
      'HTTP Request Smuggling',
      'Web Cache Poisoning',
      'Clickjacking Attacks',
      'DOM-Based Vulnerabilities',
      'File Upload Vulnerabilities',
      'Path Traversal Attacks',
      'Server-Side Template Injection (SSTI)',
      'Prototype Pollution',
      'Deserialization Vulnerabilities',
      'CORS Misconfiguration',
      'Content Security Policy (CSP) Bypass',
      'Subdomain Takeover'
    ]
  },
  {
    name: 'Network Security',
    icon: Network,
    color: 'text-green-400 bg-green-400/10 border-green-400/30',
    topics: [
      'Network Scanning & Enumeration',
      'Port Scanning Techniques',
      'Network Protocol Analysis',
      'TCP/IP Security',
      'DNS Security & Attacks',
      'ARP Spoofing & Poisoning',
      'Man-in-the-Middle Attacks',
      'Network Sniffing',
      'VLAN Hopping',
      'BGP Hijacking',
      'Network Segmentation',
      'Firewall Configuration & Bypass',
      'IDS/IPS Evasion',
      'VPN Security',
      'SSL/TLS Security',
      'Network Access Control (NAC)',
      'Zero Trust Architecture',
      'Software-Defined Networking Security',
      'Network Forensics',
      'DDoS Attack Mitigation',
      'IPv6 Security'
    ]
  },
  {
    name: 'Penetration Testing',
    icon: Target,
    color: 'text-red-400 bg-red-400/10 border-red-400/30',
    topics: [
      'Penetration Testing Methodology',
      'Reconnaissance Techniques',
      'OSINT (Open Source Intelligence)',
      'Social Engineering Attacks',
      'Phishing Campaign Design',
      'Vulnerability Assessment',
      'Exploit Development Basics',
      'Metasploit Framework',
      'Cobalt Strike Fundamentals',
      'Post-Exploitation Techniques',
      'Lateral Movement',
      'Privilege Escalation - Linux',
      'Privilege Escalation - Windows',
      'Active Directory Attacks',
      'Kerberos Attacks (Kerberoasting, Golden Ticket)',
      'Password Cracking & Spraying',
      'Hash Cracking Techniques',
      'Pivoting & Tunneling',
      'Command and Control (C2)',
      'Red Team Operations',
      'Purple Team Exercises',
      'Physical Penetration Testing',
      'Wireless Penetration Testing',
      'Report Writing for Pentesters'
    ]
  },
  {
    name: 'Malware Analysis',
    icon: Bug,
    color: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
    topics: [
      'Introduction to Malware Analysis',
      'Static Malware Analysis',
      'Dynamic Malware Analysis',
      'Reverse Engineering Fundamentals',
      'Assembly Language for Security',
      'PE File Format Analysis',
      'ELF Binary Analysis',
      'Debugging with x64dbg/OllyDbg',
      'IDA Pro Fundamentals',
      'Ghidra Reverse Engineering',
      'Ransomware Analysis',
      'Trojan Analysis',
      'Rootkit Detection & Analysis',
      'Botnet Analysis',
      'APT Malware Analysis',
      'Fileless Malware',
      'Macro Malware Analysis',
      'PowerShell Malware',
      'Android Malware Analysis',
      'iOS Malware Analysis',
      'Malware Unpacking Techniques',
      'Anti-Analysis Techniques',
      'YARA Rules Development',
      'Threat Intelligence Integration',
      'Malware Sandboxing'
    ]
  },
  {
    name: 'Cryptography',
    icon: Key,
    color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
    topics: [
      'Cryptography Fundamentals',
      'Symmetric Encryption (AES, DES)',
      'Asymmetric Encryption (RSA, ECC)',
      'Hash Functions & Collisions',
      'Digital Signatures',
      'Public Key Infrastructure (PKI)',
      'SSL/TLS Protocol Deep Dive',
      'Cryptographic Attacks',
      'Side-Channel Attacks',
      'Padding Oracle Attacks',
      'Birthday Attacks',
      'Rainbow Table Attacks',
      'Quantum Cryptography Basics',
      'Post-Quantum Cryptography',
      'Blockchain Security',
      'Cryptocurrency Security',
      'Smart Contract Security',
      'Key Management Best Practices',
      'Hardware Security Modules (HSM)',
      'Secure Random Number Generation'
    ]
  },
  {
    name: 'Cloud Security',
    icon: Cloud,
    color: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30',
    topics: [
      'Cloud Security Fundamentals',
      'AWS Security',
      'Azure Security',
      'Google Cloud Platform Security',
      'Cloud IAM & Access Control',
      'S3 Bucket Security',
      'Cloud Misconfigurations',
      'Serverless Security',
      'Container Security',
      'Kubernetes Security',
      'Docker Security',
      'Cloud Penetration Testing',
      'Cloud Forensics',
      'Multi-Cloud Security',
      'Cloud Compliance (SOC 2, ISO 27001)',
      'Cloud-Native Security Tools',
      'Infrastructure as Code Security',
      'Terraform Security',
      'CI/CD Pipeline Security',
      'DevSecOps Practices'
    ]
  },
  {
    name: 'Digital Forensics',
    icon: FileSearch,
    color: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
    topics: [
      'Digital Forensics Fundamentals',
      'Evidence Acquisition & Handling',
      'Disk Forensics',
      'Memory Forensics',
      'Windows Forensics',
      'Linux Forensics',
      'macOS Forensics',
      'Mobile Device Forensics',
      'Network Forensics',
      'Email Forensics',
      'Browser Forensics',
      'Registry Analysis',
      'Timeline Analysis',
      'Log Analysis',
      'Volatility Framework',
      'Autopsy & Sleuth Kit',
      'Chain of Custody',
      'Forensic Report Writing',
      'Anti-Forensics Techniques',
      'Cloud Forensics',
      'IoT Forensics'
    ]
  },
  {
    name: 'Incident Response',
    icon: AlertCircle,
    color: 'text-pink-400 bg-pink-400/10 border-pink-400/30',
    topics: [
      'Incident Response Process',
      'Building an IR Team',
      'Incident Detection & Triage',
      'Containment Strategies',
      'Eradication & Recovery',
      'Post-Incident Analysis',
      'SIEM Operations',
      'Splunk for Security',
      'Elastic SIEM',
      'Threat Hunting Fundamentals',
      'MITRE ATT&CK Framework',
      'Indicators of Compromise (IOCs)',
      'Threat Intelligence Platforms',
      'Ransomware Response',
      'Data Breach Response',
      'Business Email Compromise Response',
      'Insider Threat Response',
      'Tabletop Exercises',
      'Incident Response Automation',
      'SOAR Platforms'
    ]
  },
  {
    name: 'Wireless & IoT Security',
    icon: Wifi,
    color: 'text-indigo-400 bg-indigo-400/10 border-indigo-400/30',
    topics: [
      'WiFi Security Fundamentals',
      'WPA/WPA2/WPA3 Security',
      'WiFi Hacking Techniques',
      'Evil Twin Attacks',
      'Bluetooth Security',
      'RFID/NFC Security',
      'Zigbee Security',
      'LoRaWAN Security',
      'IoT Device Security',
      'Smart Home Security',
      'Industrial IoT (IIoT) Security',
      'Firmware Analysis',
      'Hardware Hacking Basics',
      'JTAG/SWD Debugging',
      'Bus Pirate & Logic Analyzers',
      'Embedded Systems Security',
      '5G Security',
      'Cellular Network Security',
      'Software Defined Radio (SDR)',
      'Drone Security'
    ]
  },
  {
    name: 'Mobile Security',
    icon: Smartphone,
    color: 'text-lime-400 bg-lime-400/10 border-lime-400/30',
    topics: [
      'Android Security Architecture',
      'iOS Security Architecture',
      'Mobile App Penetration Testing',
      'Android App Reverse Engineering',
      'iOS App Reverse Engineering',
      'Mobile Malware Analysis',
      'Frida for Mobile Security',
      'Objection Framework',
      'Mobile API Security Testing',
      'OWASP Mobile Top 10',
      'SSL Pinning Bypass',
      'Root/Jailbreak Detection Bypass',
      'Mobile Device Management (MDM)',
      'Mobile Threat Defense',
      'SMS & Call Security',
      'SIM Swapping Attacks',
      'Mobile Banking Security',
      'Mobile Payment Security'
    ]
  },
  {
    name: 'Security Operations',
    icon: Eye,
    color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    topics: [
      'Security Operations Center (SOC)',
      'SOC Analyst Skills',
      'Log Management & Analysis',
      'Security Monitoring',
      'Alert Triage & Investigation',
      'Threat Detection Rules',
      'YARA Rules for Detection',
      'Sigma Rules',
      'Snort/Suricata Rules',
      'Endpoint Detection & Response (EDR)',
      'Extended Detection & Response (XDR)',
      'Security Orchestration & Automation',
      'Playbook Development',
      'Security Metrics & KPIs',
      'Vulnerability Management',
      'Patch Management',
      'Configuration Management',
      'Asset Inventory',
      'Risk Assessment',
      'Compliance Monitoring'
    ]
  },
  {
    name: 'Application Security',
    icon: Code,
    color: 'text-rose-400 bg-rose-400/10 border-rose-400/30',
    topics: [
      'Secure Coding Practices',
      'OWASP Top 10',
      'SAST (Static Analysis)',
      'DAST (Dynamic Analysis)',
      'IAST (Interactive Analysis)',
      'Software Composition Analysis',
      'Dependency Vulnerability Management',
      'Code Review for Security',
      'Threat Modeling',
      'STRIDE Methodology',
      'Security Requirements',
      'Security Design Patterns',
      'Input Validation',
      'Output Encoding',
      'Error Handling & Logging',
      'Security Testing in CI/CD',
      'Bug Bounty Programs',
      'Responsible Disclosure',
      'Security Champions Program',
      'Application Security Program'
    ]
  },
  {
    name: 'Operating System Security',
    icon: Server,
    color: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
    topics: [
      'Windows Security Fundamentals',
      'Linux Security Fundamentals',
      'macOS Security',
      'Windows Hardening',
      'Linux Hardening',
      'Group Policy Security',
      'Windows Event Logging',
      'Linux Audit Framework',
      'User Account Control (UAC)',
      'AppLocker & WDAC',
      'SELinux & AppArmor',
      'File System Permissions',
      'Process Security',
      'Memory Protection',
      'Kernel Security',
      'Boot Security (UEFI, Secure Boot)',
      'BitLocker & LUKS Encryption',
      'Antivirus & EDR Evasion',
      'Windows Defender Configuration',
      'System Administration Security'
    ]
  },
  {
    name: 'Database Security',
    icon: Database,
    color: 'text-violet-400 bg-violet-400/10 border-violet-400/30',
    topics: [
      'Database Security Fundamentals',
      'SQL Server Security',
      'MySQL/MariaDB Security',
      'PostgreSQL Security',
      'Oracle Database Security',
      'MongoDB Security',
      'Redis Security',
      'Database Access Control',
      'Database Encryption',
      'Transparent Data Encryption (TDE)',
      'Database Activity Monitoring',
      'Database Auditing',
      'SQL Injection Prevention',
      'NoSQL Injection',
      'Database Backup Security',
      'Database Forensics',
      'Data Masking',
      'Data Loss Prevention (DLP)',
      'Database Compliance',
      'Privileged Access Management'
    ]
  },
  {
    name: 'Governance & Compliance',
    icon: Shield,
    color: 'text-teal-400 bg-teal-400/10 border-teal-400/30',
    topics: [
      'Information Security Governance',
      'Security Policies & Procedures',
      'Risk Management Frameworks',
      'NIST Cybersecurity Framework',
      'ISO 27001 Implementation',
      'SOC 2 Compliance',
      'PCI DSS Compliance',
      'HIPAA Security',
      'GDPR Compliance',
      'CCPA Privacy',
      'Security Awareness Training',
      'Third-Party Risk Management',
      'Vendor Security Assessment',
      'Business Continuity Planning',
      'Disaster Recovery Planning',
      'Security Audit Preparation',
      'Control Assessment',
      'Security Metrics & Reporting',
      'Executive Security Briefings',
      'Cyber Insurance'
    ]
  }
];

export default function LearningPath() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [courseTopic, setCourseTopic] = useState('');
  const [courseDifficulty, setCourseDifficulty] = useState<'beginner' | 'intermediate' | 'advanced'>('beginner');
  const [courseGeneration, setCourseGeneration] = useState<CourseGenerationState>({
    isGenerating: false,
    topic: '',
    error: null,
    success: null,
    jobId: null,
    progress: null,
  });
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [generationOptions, setGenerationOptions] = useState<GenerationOptions>({
    includeCodeExamples: true,
    includeDiagrams: true,
    includeVideos: true,
    includeWikipedia: true,
    includeQuizzes: true,
    numModules: 5,
    targetLessonLength: 2000,
  });

  // Poll for generation status
  useEffect(() => {
    if (!courseGeneration.jobId || !courseGeneration.isGenerating) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await coursesApi.getGenerationStatus(courseGeneration.jobId!);

        setCourseGeneration((prev) => ({
          ...prev,
          progress: {
            stage: status.current_stage,
            percent: status.progress_percent,
            currentLesson: status.current_lesson_title,
            message: getStageMessage(status.current_stage),
          },
        }));

        if (status.current_stage === 'COMPLETED') {
          clearInterval(pollInterval);
          setCourseGeneration((prev) => ({
            ...prev,
            isGenerating: false,
            success: {
              courseId: status.course_id,
              courseSlug: status.course_id,
            },
          }));
        } else if (status.current_stage === 'FAILED') {
          clearInterval(pollInterval);
          setCourseGeneration((prev) => ({
            ...prev,
            isGenerating: false,
            error: status.error_message || 'Generation failed',
          }));
        }
      } catch (err) {
        console.error('Failed to poll status:', err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [courseGeneration.jobId, courseGeneration.isGenerating]);

  const getStageMessage = (stage: string): string => {
    const messages: Record<string, string> = {
      QUEUED: 'Preparing generation...',
      STRUCTURE: 'Creating course structure...',
      CONTENT: 'Generating lesson content...',
      LABS: 'Generating labs...',
      CODE_EXAMPLES: 'Adding code examples...',
      DIAGRAMS: 'Creating diagrams...',
      IMAGES: 'Finding images...',
      WIKIPEDIA: 'Fetching Wikipedia content...',
      QUIZZES: 'Generating quizzes...',
      REVIEW: 'Final review...',
      COMPLETED: 'Complete!',
      FAILED: 'Generation failed',
    };
    return messages[stage] || 'Processing...';
  };

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Fetch recent courses
  const { data: recentCourses } = useQuery({
    queryKey: ['recentCourses'],
    queryFn: () => coursesApi.list({ limit: 4 }),
    enabled: isAuthenticated,
  });

  const handleGenerateCourse = async (useAdvanced: boolean = true) => {
    if (!courseTopic.trim()) return;

    setCourseGeneration({
      isGenerating: true,
      topic: courseTopic,
      error: null,
      success: null,
      jobId: null,
      progress: { stage: 'QUEUED', percent: 0, currentLesson: null, message: 'Starting...' },
    });

    try {
      if (useAdvanced) {
        // Use advanced generation with progress tracking
        const result = await coursesApi.generateAdvanced({
          topic: courseTopic,
          difficulty: courseDifficulty,
          num_modules: generationOptions.numModules,
          include_code_examples: generationOptions.includeCodeExamples,
          include_diagrams: generationOptions.includeDiagrams,
          include_videos: generationOptions.includeVideos,
          include_wikipedia: generationOptions.includeWikipedia,
          include_quizzes: generationOptions.includeQuizzes,
          target_lesson_length: generationOptions.targetLessonLength,
        });

        setCourseGeneration((prev) => ({
          ...prev,
          jobId: result.id,
          progress: {
            stage: result.current_stage,
            percent: result.progress_percent,
            currentLesson: null,
            message: getStageMessage(result.current_stage),
          },
        }));
      } else {
        // Use simple generation (legacy)
        const result = await coursesApi.generate(courseTopic, courseDifficulty, 5);
        setCourseGeneration({
          isGenerating: false,
          topic: courseTopic,
          error: null,
          success: {
            courseId: result.id,
            courseSlug: result.slug,
          },
          jobId: null,
          progress: null,
        });
        setCourseTopic('');
      }
    } catch (err: any) {
      setCourseGeneration({
        isGenerating: false,
        topic: courseTopic,
        error: err.response?.data?.detail || 'Failed to generate course. Please try again.',
        success: null,
        jobId: null,
        progress: null,
      });
    }
  };

  const handleTopicClick = (topic: string) => {
    setCourseTopic(topic);
    // Scroll to top where the generator is
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev =>
      prev.includes(categoryName)
        ? prev.filter(c => c !== categoryName)
        : [...prev, categoryName]
    );
  };

  // Filter topics based on search
  const filteredCategories = topicCategories.map(category => ({
    ...category,
    topics: category.topics.filter(topic =>
      topic.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(category =>
    (selectedCategory === null || category.name === selectedCategory) &&
    (searchQuery === '' || category.topics.length > 0)
  );

  // Count total topics
  const totalTopics = topicCategories.reduce((acc, cat) => acc + cat.topics.length, 0);

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Generating Overlay with Progress - Minimizable */}
      {courseGeneration.isGenerating && (
        isMinimized ? (
          // Minimized floating indicator (bottom-right corner)
          <div className="fixed bottom-4 right-4 z-50">
            <button
              onClick={() => setIsMinimized(false)}
              className="bg-cyber-dark border border-cyber-accent/30 rounded-xl p-4 shadow-lg hover:border-cyber-accent/50 transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 relative">
                  {/* Mini circular progress */}
                  <svg className="w-12 h-12 -rotate-90">
                    <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(0,255,159,0.2)" strokeWidth="4"/>
                    <circle
                      cx="24" cy="24" r="20" fill="none" stroke="#00ff9f" strokeWidth="4"
                      strokeLinecap="round"
                      strokeDasharray={`${(courseGeneration.progress?.percent || 0) * 1.26} 126`}
                      className="transition-all duration-500"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-cyber-accent">
                    {Math.round(courseGeneration.progress?.percent || 0)}%
                  </span>
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-white">Generating Course</p>
                  <p className="text-xs text-gray-400 truncate max-w-[150px]">
                    {courseGeneration.progress?.message || 'Processing...'}
                  </p>
                </div>
                <Maximize2 className="w-4 h-4 text-gray-400 group-hover:text-cyber-accent transition-colors ml-2" />
              </div>
            </button>
          </div>
        ) : (
          // Full modal with minimize button
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-8 max-w-lg text-center relative">
              {/* Minimize button */}
              <button
                onClick={() => setIsMinimized(true)}
                className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title="Minimize to continue browsing"
              >
                <Minimize2 className="w-5 h-5" />
              </button>

              <div className="relative w-20 h-20 mx-auto mb-6">
                <svg className="w-20 h-20 -rotate-90">
                  <circle
                    cx="40"
                    cy="40"
                    r="36"
                    fill="none"
                    stroke="rgba(0, 255, 159, 0.2)"
                    strokeWidth="8"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r="36"
                    fill="none"
                    stroke="#00ff9f"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${(courseGeneration.progress?.percent || 0) * 2.26} 226`}
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold text-cyber-accent">
                    {(courseGeneration.progress?.percent || 0).toFixed(1)}%
                  </span>
                </div>
              </div>

              <h3 className="text-xl font-bold text-white mb-2">Generating Your Course</h3>
              <p className="text-gray-400 mb-4">
                Creating <span className="text-cyber-accent font-medium">"{courseGeneration.topic}"</span>
              </p>

              {/* Stage Progress */}
              <div className="bg-cyber-darker rounded-xl p-4 mb-4">
                <p className="text-cyber-accent font-medium mb-2">
                  {courseGeneration.progress?.message || 'Starting...'}
                </p>
                {courseGeneration.progress?.currentLesson && (
                  <p className="text-sm text-gray-500">
                    Current: {courseGeneration.progress.currentLesson}
                  </p>
                )}
              </div>

              {/* Stage Indicators */}
              <div className="flex flex-wrap gap-2 justify-center">
                {['STRUCTURE', 'CONTENT', 'CODE_EXAMPLES', 'DIAGRAMS', 'WIKIPEDIA', 'QUIZZES'].map((stage) => {
                  const currentStage = courseGeneration.progress?.stage || '';
                  const stageOrder = ['QUEUED', 'STRUCTURE', 'CONTENT', 'LABS', 'CODE_EXAMPLES', 'DIAGRAMS', 'IMAGES', 'WIKIPEDIA', 'QUIZZES', 'REVIEW', 'COMPLETED'];
                  const currentIdx = stageOrder.indexOf(currentStage);
                  const stageIdx = stageOrder.indexOf(stage);
                  const isCompleted = currentIdx > stageIdx;
                  const isCurrent = currentStage === stage;

                  return (
                    <div
                      key={stage}
                      className={`px-2 py-1 rounded text-xs ${
                        isCompleted
                          ? 'bg-green-500/20 text-green-400'
                          : isCurrent
                          ? 'bg-cyber-accent/20 text-cyber-accent animate-pulse'
                          : 'bg-gray-800 text-gray-500'
                      }`}
                    >
                      {stage.replace('_', ' ')}
                    </div>
                  );
                })}
              </div>

              <p className="text-xs text-gray-600 mt-4">
                This may take a few minutes for comprehensive content
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Click the minimize button to continue browsing while generating
              </p>
            </div>
          </div>
        )
      )}

      {/* Success Toast */}
      {courseGeneration.success && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-4 animate-in slide-in-from-bottom-5">
          <CheckCircle className="w-8 h-8" />
          <div>
            <p className="font-bold">Course Created Successfully!</p>
            <p className="text-sm opacity-90">Your learning path is ready</p>
          </div>
          <button
            onClick={() => router.push(`/courses`)}
            className="ml-4 px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 transition-colors font-medium"
          >
            View Course
          </button>
          <button
            onClick={() => setCourseGeneration(g => ({ ...g, success: null }))}
            className="p-1 hover:bg-white/20 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Error Toast */}
      {courseGeneration.error && (
        <div className="fixed bottom-6 right-6 z-50 bg-red-500 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center gap-4">
          <AlertTriangle className="w-8 h-8" />
          <div>
            <p className="font-bold">Generation Failed</p>
            <p className="text-sm opacity-90">{courseGeneration.error}</p>
          </div>
          <button
            onClick={() => setCourseGeneration(g => ({ ...g, error: null }))}
            className="p-1 hover:bg-white/20 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-xl">
            <Sparkles className="w-8 h-8 text-purple-400" />
          </div>
          AI Course Creator
        </h1>
        <p className="text-gray-400 mt-2">
          Browse {totalTopics}+ cybersecurity topics and generate personalized courses with hands-on labs
        </p>
      </div>

      {/* Course Generator Card */}
      <div className="bg-cyber-dark rounded-2xl border border-purple-500/30 p-6 mb-8 sticky top-4 z-40">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Topic Input */}
          <div className="flex-1 min-w-[300px]">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Selected Topic
            </label>
            <input
              type="text"
              value={courseTopic}
              onChange={(e) => setCourseTopic(e.target.value)}
              placeholder="Select a topic below or type your own..."
              className="w-full px-4 py-3 bg-cyber-darker border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors"
              disabled={courseGeneration.isGenerating}
            />
          </div>

          {/* Difficulty Selection */}
          <div className="min-w-[150px]">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Difficulty
            </label>
            <select
              value={courseDifficulty}
              onChange={(e) => setCourseDifficulty(e.target.value as any)}
              className="w-full px-4 py-3 bg-cyber-darker border border-gray-700 rounded-xl text-white focus:outline-none focus:border-purple-500"
              disabled={courseGeneration.isGenerating}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          {/* Advanced Options Toggle */}
          <button
            onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
            className="flex items-center gap-2 px-4 py-3 bg-cyber-darker border border-gray-700 rounded-xl text-gray-400 hover:text-white hover:border-purple-500 transition-colors"
          >
            <Filter className="w-4 h-4" />
            <span className="text-sm">Options</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showAdvancedOptions ? 'rotate-180' : ''}`} />
          </button>

          {/* Generate Button */}
          <button
            onClick={() => handleGenerateCourse(true)}
            disabled={!courseTopic.trim() || courseGeneration.isGenerating}
            className="flex items-center justify-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-xl hover:from-purple-600 hover:to-pink-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/25 whitespace-nowrap"
          >
            {courseGeneration.isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Zap className="w-5 h-5" />
                Generate Course
              </>
            )}
          </button>
        </div>

        {/* Advanced Options Panel */}
        {showAdvancedOptions && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {/* Toggle Options */}
              <label className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg cursor-pointer hover:bg-cyber-darker/80">
                <input
                  type="checkbox"
                  checked={generationOptions.includeCodeExamples}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, includeCodeExamples: e.target.checked }))}
                  className="w-4 h-4 accent-purple-500"
                />
                <div>
                  <span className="text-white text-sm">Code Examples</span>
                  <p className="text-xs text-gray-500">Practical snippets</p>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg cursor-pointer hover:bg-cyber-darker/80">
                <input
                  type="checkbox"
                  checked={generationOptions.includeDiagrams}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, includeDiagrams: e.target.checked }))}
                  className="w-4 h-4 accent-purple-500"
                />
                <div>
                  <span className="text-white text-sm">Diagrams</span>
                  <p className="text-xs text-gray-500">Mermaid flowcharts</p>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg cursor-pointer hover:bg-cyber-darker/80">
                <input
                  type="checkbox"
                  checked={generationOptions.includeWikipedia}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, includeWikipedia: e.target.checked }))}
                  className="w-4 h-4 accent-purple-500"
                />
                <div>
                  <span className="text-white text-sm">Wikipedia</span>
                  <p className="text-xs text-gray-500">Reference content</p>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg cursor-pointer hover:bg-cyber-darker/80">
                <input
                  type="checkbox"
                  checked={generationOptions.includeQuizzes}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, includeQuizzes: e.target.checked }))}
                  className="w-4 h-4 accent-purple-500"
                />
                <div>
                  <span className="text-white text-sm">Quizzes</span>
                  <p className="text-xs text-gray-500">Knowledge checks</p>
                </div>
              </label>
            </div>

            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[150px]">
                <label className="block text-xs text-gray-400 mb-1">Modules</label>
                <select
                  value={generationOptions.numModules}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, numModules: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white text-sm"
                >
                  <option value={3}>3 modules (Quick)</option>
                  <option value={5}>5 modules (Standard)</option>
                  <option value={7}>7 modules (Comprehensive)</option>
                  <option value={10}>10 modules (In-depth)</option>
                </select>
              </div>

              <div className="flex-1 min-w-[150px]">
                <label className="block text-xs text-gray-400 mb-1">Lesson Length</label>
                <select
                  value={generationOptions.targetLessonLength}
                  onChange={(e) => setGenerationOptions(o => ({ ...o, targetLessonLength: parseInt(e.target.value) }))}
                  className="w-full px-3 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white text-sm"
                >
                  <option value={200}>200 words (Brief)</option>
                  <option value={500}>500 words (Concise)</option>
                  <option value={1000}>1000 words (Standard)</option>
                  <option value={2000}>2000 words (Detailed)</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Search and Filter */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex-1 min-w-[250px] relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search topics..."
            className="w-full pl-12 pr-4 py-3 bg-cyber-dark border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <select
            value={selectedCategory || ''}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
            className="px-4 py-3 bg-cyber-dark border border-gray-700 rounded-xl text-white focus:outline-none focus:border-cyber-accent"
          >
            <option value="">All Categories</option>
            {topicCategories.map(cat => (
              <option key={cat.name} value={cat.name}>{cat.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Topic Categories */}
      <div className="space-y-4 mb-8">
        {filteredCategories.map((category) => {
          const Icon = category.icon;
          const isExpanded = expandedCategories.includes(category.name) || searchQuery !== '';

          return (
            <div
              key={category.name}
              className="bg-cyber-dark rounded-xl border border-gray-800 overflow-hidden"
            >
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(category.name)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg border ${category.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-white">{category.name}</h3>
                    <p className="text-sm text-gray-500">{category.topics.length} topics</p>
                  </div>
                </div>
                <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
              </button>

              {/* Topics Grid */}
              {isExpanded && (
                <div className="px-4 pb-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
                    {category.topics.map((topic) => (
                      <button
                        key={topic}
                        onClick={() => handleTopicClick(topic)}
                        className={`flex items-center gap-2 p-3 rounded-lg text-left transition-all ${
                          courseTopic === topic
                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                            : 'bg-cyber-darker text-gray-400 hover:text-white hover:bg-cyber-darker/80 border border-transparent hover:border-gray-700'
                        }`}
                      >
                        <Play className="w-3 h-3 flex-shrink-0 opacity-60" />
                        <span className="text-sm truncate">{topic}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Recent Courses */}
      {recentCourses?.length > 0 && (
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-white flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-cyber-accent" />
              Your Recent Courses
            </h3>
            <button
              onClick={() => router.push('/courses')}
              className="text-sm text-cyber-accent hover:text-cyber-accent/80 flex items-center gap-1"
            >
              View All
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentCourses.map((course: any) => (
              <button
                key={course.id}
                onClick={() => router.push(`/courses`)}
                className="flex items-center gap-3 p-4 bg-cyber-darker rounded-lg hover:bg-cyber-darker/80 transition-colors text-left group"
              >
                <div className="p-2 bg-cyber-accent/10 rounded-lg">
                  <GraduationCap className="w-5 h-5 text-cyber-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate group-hover:text-cyber-accent transition-colors">
                    {course.title}
                  </p>
                  <p className="text-xs text-gray-500">
                    {course.difficulty} • {course.estimated_hours}h
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Features Info */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="bg-cyber-dark rounded-xl border border-gray-800 p-6 text-center">
          <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Brain className="w-6 h-6 text-purple-400" />
          </div>
          <h4 className="font-medium text-white mb-2">AI-Powered Content</h4>
          <p className="text-sm text-gray-500">
            Courses are generated using advanced AI, tailored to your chosen topic and difficulty
          </p>
        </div>
        <div className="bg-cyber-dark rounded-xl border border-gray-800 p-6 text-center">
          <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Beaker className="w-6 h-6 text-green-400" />
          </div>
          <h4 className="font-medium text-white mb-2">Hands-On Labs</h4>
          <p className="text-sm text-gray-500">
            Each course includes a practical lab environment to apply what you've learned
          </p>
        </div>
        <div className="bg-cyber-dark rounded-xl border border-gray-800 p-6 text-center">
          <div className="w-12 h-12 bg-yellow-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Award className="w-6 h-6 text-yellow-400" />
          </div>
          <h4 className="font-medium text-white mb-2">Track Progress</h4>
          <p className="text-sm text-gray-500">
            Earn points, complete challenges, and track your learning journey
          </p>
        </div>
      </div>
    </div>
  );
}
