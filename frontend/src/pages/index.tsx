import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Head from 'next/head';
import {
  Shield, Terminal, BookOpen, Brain, Zap, Users,
  ChevronRight, Play, Award, Target, Lock, Cpu,
  Globe, Code, Database, Server, Wifi, Eye,
  ArrowRight, Check, Star, TrendingUp
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [scrollY, setScrollY] = useState(0);
  const [isVisible, setIsVisible] = useState<{[key: string]: boolean}>({});
  const statsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasHydrated) return;
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [hasHydrated, isAuthenticated, router]);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(prev => ({ ...prev, [entry.target.id]: true }));
          }
        });
      },
      { threshold: 0.1 }
    );

    document.querySelectorAll('[data-animate]').forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <>
      <Head>
        <title>CyyberAIx - AI-Powered Cybersecurity Training Platform</title>
        <meta name="description" content="Master cybersecurity with AI-powered personalized learning. From beginner to expert, at your own pace." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-cyber-darker overflow-hidden">
        {/* Animated Background */}
        <div className="fixed inset-0 pointer-events-none">
          {/* Grid Pattern */}
          <div className="absolute inset-0 bg-cyber-grid bg-grid opacity-30" />

          {/* Gradient Orbs */}
          <div className="absolute top-1/4 -left-32 w-96 h-96 bg-cyber-accent/20 rounded-full blur-[128px] animate-pulse-slow" />
          <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-cyber-blue/20 rounded-full blur-[128px] animate-pulse-slow" style={{ animationDelay: '1s' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyber-purple/10 rounded-full blur-[150px] animate-pulse-slow" style={{ animationDelay: '2s' }} />

          {/* Floating Particles */}
          <div className="absolute top-20 left-[10%] w-2 h-2 bg-cyber-accent rounded-full animate-particle-1 opacity-60" />
          <div className="absolute top-40 right-[20%] w-3 h-3 bg-cyber-blue rounded-full animate-particle-2 opacity-40" />
          <div className="absolute bottom-40 left-[30%] w-2 h-2 bg-cyber-purple rounded-full animate-particle-3 opacity-50" />
          <div className="absolute top-60 right-[40%] w-1 h-1 bg-cyber-accent rounded-full animate-particle-1 opacity-70" style={{ animationDelay: '2s' }} />
          <div className="absolute bottom-60 right-[10%] w-2 h-2 bg-cyber-blue rounded-full animate-particle-2 opacity-50" style={{ animationDelay: '3s' }} />
        </div>

        {/* Navigation */}
        <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrollY > 50 ? 'bg-cyber-darker/90 backdrop-blur-lg shadow-lg shadow-cyber-accent/5' : ''}`}>
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center gap-3 group">
                <div className="relative">
                  <Shield className="w-10 h-10 text-cyber-accent transition-transform group-hover:scale-110" />
                  <div className="absolute inset-0 bg-cyber-accent/20 rounded-full blur-xl group-hover:blur-2xl transition-all" />
                </div>
                <span className="text-2xl font-bold text-white">
                  Cyyber<span className="text-cyber-accent">AIx</span>
                </span>
              </Link>

              <div className="hidden md:flex items-center gap-8">
                <a href="#features" className="text-gray-400 hover:text-cyber-accent transition-colors">Features</a>
                <a href="#paths" className="text-gray-400 hover:text-cyber-accent transition-colors">Learning Paths</a>
                <a href="#stats" className="text-gray-400 hover:text-cyber-accent transition-colors">Why Us</a>
              </div>

              <div className="flex items-center gap-4">
                <Link href="/login" className="text-gray-300 hover:text-white transition-colors px-4 py-2">
                  Sign In
                </Link>
                <Link href="/register" className="relative group px-6 py-2.5 overflow-hidden rounded-lg">
                  <div className="absolute inset-0 bg-gradient-to-r from-cyber-accent to-cyber-blue transition-transform group-hover:scale-105" />
                  <span className="relative text-cyber-dark font-semibold">Get Started</span>
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative min-h-screen flex items-center justify-center pt-20">
          <div className="max-w-7xl mx-auto px-6 py-20">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              {/* Left Content */}
              <div className="text-center lg:text-left">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyber-accent/10 border border-cyber-accent/20 mb-8 animate-fade-in">
                  <Zap className="w-4 h-4 text-cyber-accent" />
                  <span className="text-cyber-accent text-sm font-medium">AI-Powered Learning Platform</span>
                </div>

                <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight animate-slide-up">
                  Master{' '}
                  <span className="relative">
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-accent via-cyber-blue to-cyber-purple animate-gradient bg-[length:200%_auto]">
                      Cybersecurity
                    </span>
                    <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 300 12" fill="none">
                      <path d="M2 10C50 4 100 2 150 6C200 10 250 8 298 4" stroke="url(#gradient)" strokeWidth="3" strokeLinecap="round"/>
                      <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#00ff9d" />
                          <stop offset="50%" stopColor="#00d4ff" />
                          <stop offset="100%" stopColor="#a855f7" />
                        </linearGradient>
                      </defs>
                    </svg>
                  </span>
                  <br />
                  <span className="text-gray-300">With AI</span>
                </h1>

                <p className="text-xl text-gray-400 mb-10 max-w-xl mx-auto lg:mx-0 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                  Personalized learning paths, hands-on labs, and real-time AI tutoring.
                  From beginner to expert, learn at your own pace.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start animate-slide-up" style={{ animationDelay: '0.2s' }}>
                  <Link href="/register" className="group relative inline-flex items-center justify-center gap-2 px-8 py-4 overflow-hidden rounded-xl">
                    <div className="absolute inset-0 bg-gradient-to-r from-cyber-accent to-cyber-blue" />
                    <div className="absolute inset-0 bg-gradient-to-r from-cyber-blue to-cyber-accent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <span className="relative text-cyber-dark font-bold text-lg">Start Learning Free</span>
                    <ArrowRight className="relative w-5 h-5 text-cyber-dark group-hover:translate-x-1 transition-transform" />
                  </Link>

                  <button className="group inline-flex items-center justify-center gap-3 px-8 py-4 rounded-xl border border-gray-700 hover:border-cyber-accent/50 transition-colors bg-cyber-dark/50 backdrop-blur-sm">
                    <div className="w-10 h-10 rounded-full bg-cyber-accent/20 flex items-center justify-center group-hover:bg-cyber-accent/30 transition-colors">
                      <Play className="w-4 h-4 text-cyber-accent ml-0.5" />
                    </div>
                    <span className="text-white font-medium">Watch Demo</span>
                  </button>
                </div>

                {/* Trust Badges */}
                <div className="flex flex-wrap items-center gap-6 mt-12 justify-center lg:justify-start animate-fade-in" style={{ animationDelay: '0.3s' }}>
                  <div className="flex items-center gap-2 text-gray-500">
                    <Check className="w-5 h-5 text-cyber-accent" />
                    <span>Free to Start</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-500">
                    <Check className="w-5 h-5 text-cyber-accent" />
                    <span>No Credit Card</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-500">
                    <Check className="w-5 h-5 text-cyber-accent" />
                    <span>24/7 AI Support</span>
                  </div>
                </div>
              </div>

              {/* Right Content - 3D Hero Visual */}
              <div className="relative hidden lg:block">
                <div className="relative w-full aspect-square max-w-lg mx-auto">
                  {/* Outer Ring */}
                  <div className="absolute inset-0 rounded-full border border-cyber-accent/20 animate-spin-slow" />
                  <div className="absolute inset-4 rounded-full border border-cyber-blue/20 animate-spin-slow" style={{ animationDirection: 'reverse', animationDuration: '12s' }} />
                  <div className="absolute inset-8 rounded-full border border-cyber-purple/20 animate-spin-slow" style={{ animationDuration: '16s' }} />

                  {/* Center Shield */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative">
                      <div className="absolute inset-0 bg-cyber-accent/30 rounded-full blur-3xl animate-pulse-slow" />
                      <Shield className="w-32 h-32 text-cyber-accent animate-float" />
                    </div>
                  </div>

                  {/* Floating Icons */}
                  <div className="absolute top-12 left-12 p-4 bg-cyber-dark/80 backdrop-blur-sm rounded-2xl border border-cyber-accent/20 animate-float shadow-lg shadow-cyber-accent/10">
                    <Terminal className="w-8 h-8 text-cyber-accent" />
                  </div>
                  <div className="absolute top-20 right-8 p-4 bg-cyber-dark/80 backdrop-blur-sm rounded-2xl border border-cyber-blue/20 animate-float-delayed shadow-lg shadow-cyber-blue/10">
                    <Code className="w-8 h-8 text-cyber-blue" />
                  </div>
                  <div className="absolute bottom-20 left-8 p-4 bg-cyber-dark/80 backdrop-blur-sm rounded-2xl border border-cyber-purple/20 animate-float shadow-lg shadow-cyber-purple/10" style={{ animationDelay: '1s' }}>
                    <Lock className="w-8 h-8 text-cyber-purple" />
                  </div>
                  <div className="absolute bottom-12 right-12 p-4 bg-cyber-dark/80 backdrop-blur-sm rounded-2xl border border-cyber-accent/20 animate-float-delayed shadow-lg shadow-cyber-accent/10">
                    <Brain className="w-8 h-8 text-cyber-accent" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Scroll Indicator */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce">
            <div className="w-6 h-10 rounded-full border-2 border-gray-600 flex justify-center pt-2">
              <div className="w-1 h-2 bg-cyber-accent rounded-full animate-pulse" />
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section id="stats" ref={statsRef} className="relative py-20 border-y border-cyber-accent/10">
          <div className="max-w-7xl mx-auto px-6">
            <div
              id="stats-section"
              data-animate
              className={`grid grid-cols-2 md:grid-cols-4 gap-8 transition-all duration-700 ${isVisible['stats-section'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              <StatCard number="50K+" label="Active Learners" icon={Users} />
              <StatCard number="200+" label="Expert Courses" icon={BookOpen} />
              <StatCard number="500+" label="Hands-on Labs" icon={Terminal} />
              <StatCard number="98%" label="Success Rate" icon={TrendingUp} />
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="relative py-32">
          <div className="max-w-7xl mx-auto px-6">
            <div
              id="features-header"
              data-animate
              className={`text-center mb-20 transition-all duration-700 ${isVisible['features-header'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              <span className="inline-block px-4 py-2 rounded-full bg-cyber-accent/10 text-cyber-accent text-sm font-medium mb-4">
                Why Choose CyyberAIx
              </span>
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Learn Cybersecurity the{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-accent to-cyber-blue">
                  Smart Way
                </span>
              </h2>
              <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                Our AI-powered platform adapts to your learning style,
                ensuring you master cybersecurity faster than ever before.
              </p>
            </div>

            <div
              id="features-grid"
              data-animate
              className={`grid md:grid-cols-2 lg:grid-cols-3 gap-6 transition-all duration-700 delay-200 ${isVisible['features-grid'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              <FeatureCard
                icon={Brain}
                title="AI Teaching Engine"
                description="Personalized instruction that adapts to your skill level and learning style in real-time."
                gradient="from-cyber-accent to-cyber-blue"
              />
              <FeatureCard
                icon={Terminal}
                title="Hands-on Labs"
                description="Practice in isolated lab environments with real tools. Learn by doing, not just reading."
                gradient="from-cyber-blue to-cyber-purple"
              />
              <FeatureCard
                icon={BookOpen}
                title="Expert Courses"
                description="From networking basics to advanced pentesting. All courses include practical exercises."
                gradient="from-cyber-purple to-cyber-pink"
              />
              <FeatureCard
                icon={Target}
                title="Adaptive Learning"
                description="AI-generated curriculum based on your goals, current skills, and available time."
                gradient="from-cyber-accent to-cyber-blue"
              />
              <FeatureCard
                icon={Award}
                title="Skill Assessment"
                description="Continuous evaluation using advanced algorithms for accurate skill measurement."
                gradient="from-cyber-blue to-cyber-purple"
              />
              <FeatureCard
                icon={Cpu}
                title="24/7 Alphha Tutor"
                description="Get instant help anytime with our AI tutor backed by current cybersecurity knowledge."
                gradient="from-cyber-purple to-cyber-accent"
              />
            </div>
          </div>
        </section>

        {/* Learning Paths Section */}
        <section id="paths" className="relative py-32 bg-gradient-to-b from-cyber-dark/50 to-transparent">
          <div className="max-w-7xl mx-auto px-6">
            <div
              id="paths-header"
              data-animate
              className={`text-center mb-20 transition-all duration-700 ${isVisible['paths-header'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              <span className="inline-block px-4 py-2 rounded-full bg-cyber-blue/10 text-cyber-blue text-sm font-medium mb-4">
                Career Paths
              </span>
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Choose Your{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-blue to-cyber-purple">
                  Destiny
                </span>
              </h2>
              <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                Select a career path and let our AI craft the perfect learning journey for you.
              </p>
            </div>

            <div
              id="paths-grid"
              data-animate
              className={`grid md:grid-cols-2 lg:grid-cols-4 gap-6 transition-all duration-700 delay-200 ${isVisible['paths-grid'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              <PathCard
                icon={Eye}
                title="SOC Analyst"
                description="Monitor, detect, and respond to security threats in real-time"
                skills={['SIEM', 'Log Analysis', 'Incident Response', 'Threat Intel']}
                color="cyber-accent"
              />
              <PathCard
                icon={Target}
                title="Penetration Tester"
                description="Find vulnerabilities before attackers do"
                skills={['Web Security', 'Network Pentesting', 'Exploit Dev', 'Red Team']}
                color="cyber-blue"
              />
              <PathCard
                icon={Server}
                title="Security Engineer"
                description="Build and maintain secure systems and infrastructure"
                skills={['Cloud Security', 'Hardening', 'DevSecOps', 'Architecture']}
                color="cyber-purple"
              />
              <PathCard
                icon={Code}
                title="Malware Analyst"
                description="Analyze and understand malicious software"
                skills={['Reverse Engineering', 'Sandboxing', 'Static Analysis', 'Forensics']}
                color="cyber-pink"
              />
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="relative py-32">
          <div className="max-w-4xl mx-auto px-6 text-center">
            <div
              id="cta-section"
              data-animate
              className={`relative transition-all duration-700 ${isVisible['cta-section'] ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
              {/* Glow Background */}
              <div className="absolute inset-0 bg-gradient-to-r from-cyber-accent/20 via-cyber-blue/20 to-cyber-purple/20 blur-3xl" />

              <div className="relative bg-cyber-dark/80 backdrop-blur-xl rounded-3xl border border-cyber-accent/20 p-12 md:p-16">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyber-accent/10 border border-cyber-accent/20 mb-8">
                  <Star className="w-4 h-4 text-cyber-accent" />
                  <span className="text-cyber-accent text-sm font-medium">Start Your Journey Today</span>
                </div>

                <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                  Ready to Become a{' '}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyber-accent via-cyber-blue to-cyber-purple">
                    Cyber Expert?
                  </span>
                </h2>

                <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
                  Join thousands of security professionals who transformed their careers with CyyberAIx.
                  Your journey starts with a single click.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <Link href="/register" className="group relative inline-flex items-center justify-center gap-2 px-10 py-5 overflow-hidden rounded-xl">
                    <div className="absolute inset-0 bg-gradient-to-r from-cyber-accent via-cyber-blue to-cyber-purple animate-gradient bg-[length:200%_auto]" />
                    <span className="relative text-cyber-dark font-bold text-lg">Create Free Account</span>
                    <ArrowRight className="relative w-5 h-5 text-cyber-dark group-hover:translate-x-1 transition-transform" />
                  </Link>
                </div>

                <p className="mt-6 text-gray-500 text-sm">
                  No credit card required • Free forever plan available
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="relative border-t border-cyber-accent/10 py-16">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid md:grid-cols-4 gap-12 mb-12">
              <div className="md:col-span-2">
                <Link href="/" className="flex items-center gap-3 mb-6">
                  <Shield className="w-10 h-10 text-cyber-accent" />
                  <span className="text-2xl font-bold text-white">
                    Cyyber<span className="text-cyber-accent">AIx</span>
                  </span>
                </Link>
                <p className="text-gray-400 mb-6 max-w-md">
                  The future of cybersecurity education. Learn, practice, and master
                  security skills with AI-powered personalized learning.
                </p>
                <div className="flex items-center gap-4">
                  <a href="#" className="w-10 h-10 rounded-lg bg-cyber-dark border border-gray-800 flex items-center justify-center text-gray-400 hover:text-cyber-accent hover:border-cyber-accent/50 transition-colors">
                    <Globe className="w-5 h-5" />
                  </a>
                  <a href="#" className="w-10 h-10 rounded-lg bg-cyber-dark border border-gray-800 flex items-center justify-center text-gray-400 hover:text-cyber-accent hover:border-cyber-accent/50 transition-colors">
                    <Code className="w-5 h-5" />
                  </a>
                </div>
              </div>

              <div>
                <h4 className="text-white font-semibold mb-4">Platform</h4>
                <ul className="space-y-3">
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Courses</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Labs</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Learning Paths</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Certifications</a></li>
                </ul>
              </div>

              <div>
                <h4 className="text-white font-semibold mb-4">Company</h4>
                <ul className="space-y-3">
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">About Us</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Contact</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Privacy Policy</a></li>
                  <li><a href="#" className="text-gray-400 hover:text-cyber-accent transition-colors">Terms of Service</a></li>
                </ul>
              </div>
            </div>

            <div className="pt-8 border-t border-gray-800 flex flex-col md:flex-row items-center justify-between gap-4">
              <p className="text-gray-500 text-sm">
                &copy; 2024 CyyberAIx. All rights reserved. | cyyberaix.in
              </p>
              <p className="text-gray-600 text-sm">
                Built with AI for the cybersecurity community
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

// Stats Card Component
function StatCard({ number, label, icon: Icon }: { number: string; label: string; icon: any }) {
  return (
    <div className="text-center group">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-cyber-accent/10 mb-4 group-hover:bg-cyber-accent/20 transition-colors">
        <Icon className="w-7 h-7 text-cyber-accent" />
      </div>
      <div className="text-4xl md:text-5xl font-bold text-white mb-2">{number}</div>
      <div className="text-gray-400">{label}</div>
    </div>
  );
}

// Feature Card Component
function FeatureCard({ icon: Icon, title, description, gradient }: { icon: any; title: string; description: string; gradient: string }) {
  return (
    <div className="group relative p-8 rounded-2xl bg-cyber-dark/50 backdrop-blur-sm border border-gray-800 hover:border-cyber-accent/30 transition-all duration-300 overflow-hidden">
      {/* Hover Gradient */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />

      <div className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br ${gradient} mb-6`}>
        <Icon className="w-7 h-7 text-white" />
      </div>

      <h3 className="text-xl font-semibold text-white mb-3 group-hover:text-cyber-accent transition-colors">
        {title}
      </h3>
      <p className="text-gray-400 leading-relaxed">
        {description}
      </p>

      <div className="flex items-center gap-2 mt-6 text-cyber-accent opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-sm font-medium">Learn more</span>
        <ChevronRight className="w-4 h-4" />
      </div>
    </div>
  );
}

// Path Card Component
function PathCard({ icon: Icon, title, description, skills, color }: { icon: any; title: string; description: string; skills: string[]; color: string }) {
  const colorClasses: Record<string, string> = {
    'cyber-accent': 'from-cyber-accent/20 to-cyber-accent/5 border-cyber-accent/30 hover:border-cyber-accent/50',
    'cyber-blue': 'from-cyber-blue/20 to-cyber-blue/5 border-cyber-blue/30 hover:border-cyber-blue/50',
    'cyber-purple': 'from-cyber-purple/20 to-cyber-purple/5 border-cyber-purple/30 hover:border-cyber-purple/50',
    'cyber-pink': 'from-cyber-pink/20 to-cyber-pink/5 border-cyber-pink/30 hover:border-cyber-pink/50',
  };

  const iconColorClasses: Record<string, string> = {
    'cyber-accent': 'text-cyber-accent',
    'cyber-blue': 'text-cyber-blue',
    'cyber-purple': 'text-cyber-purple',
    'cyber-pink': 'text-cyber-pink',
  };

  return (
    <div className={`group relative p-6 rounded-2xl bg-gradient-to-b ${colorClasses[color]} border transition-all duration-300 cursor-pointer hover:scale-105 hover:-translate-y-1`}>
      <div className={`w-12 h-12 rounded-xl bg-cyber-dark/50 flex items-center justify-center mb-4`}>
        <Icon className={`w-6 h-6 ${iconColorClasses[color]}`} />
      </div>

      <h3 className="text-xl font-semibold text-white mb-2 group-hover:text-cyber-accent transition-colors">
        {title}
      </h3>
      <p className="text-gray-400 text-sm mb-4">
        {description}
      </p>

      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span
            key={skill}
            className="px-2.5 py-1 text-xs bg-cyber-dark/50 text-gray-300 rounded-lg border border-gray-800"
          >
            {skill}
          </span>
        ))}
      </div>
    </div>
  );
}
