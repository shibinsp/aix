import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { skillsApi } from '@/services/api';
import {
  Network,
  Server,
  Globe,
  Key,
  Search,
  Bug,
  Cloud,
  Shield,
  LucideIcon,
} from 'lucide-react';

// Types
export interface LearningMilestone {
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  order: number;
  status: 'completed' | 'current' | 'available' | 'locked';
  progress: number;
  skillCount: number;
  skillsCompleted: number;
  description: string;
}

// Skill domain definitions - IDs must match backend skill tree keys
const SKILL_DOMAINS: Array<{
  id: string;
  name: string;
  icon: LucideIcon;
  color: string;
  description: string;
}> = [
  {
    id: 'network_security',
    name: 'Network Security',
    icon: Network,
    color: 'cyan',
    description: 'Master network protocols, firewalls, and intrusion detection',
  },
  {
    id: 'system_security',
    name: 'System Security',
    icon: Server,
    color: 'purple',
    description: 'Secure operating systems and infrastructure',
  },
  {
    id: 'web_security',
    name: 'Web Security',
    icon: Globe,
    color: 'green',
    description: 'Protect web applications from common vulnerabilities',
  },
  {
    id: 'cryptography',
    name: 'Cryptography',
    icon: Key,
    color: 'orange',
    description: 'Understand encryption, hashing, and secure communications',
  },
  {
    id: 'forensics',
    name: 'Digital Forensics',
    icon: Search,
    color: 'pink',
    description: 'Investigate and analyze digital evidence',
  },
  {
    id: 'malware_analysis',
    name: 'Malware Analysis',
    icon: Bug,
    color: 'red',
    description: 'Analyze and understand malicious software',
  },
  {
    id: 'cloud_security',
    name: 'Cloud Security',
    icon: Cloud,
    color: 'blue',
    description: 'Secure cloud infrastructure and services',
  },
  {
    id: 'soc_operations',
    name: 'SOC Operations',
    icon: Shield,
    color: 'emerald',
    description: 'Master security operations and incident response',
  },
];

// API Response Types
interface SkillTreeResponse {
  [domainId: string]: {
    name: string;
    skills: string[];
  };
}

interface UserSkillData {
  proficiency_level: number;
  confidence_score: number;
  level_label: string;
  total_practice_time: number;
  questions_attempted: number;
  questions_correct: number;
  last_practiced: string | null;
}

interface UserSkillsResponse {
  skills: {
    [skillName: string]: UserSkillData;
  };
  overall_proficiency: number;
  overall_level: string;
}

// Transform skills data to milestones
function transformToMilestones(
  userSkillsData: UserSkillsResponse | null,
  skillTree: SkillTreeResponse | null
): LearningMilestone[] {
  // Build a map of skill name -> domain id from the skill tree
  const skillToDomain: Record<string, string> = {};
  const domainSkillCounts: Record<string, number> = {};

  if (skillTree) {
    Object.entries(skillTree).forEach(([domainId, domainData]) => {
      domainSkillCounts[domainId] = domainData.skills?.length || 0;
      domainData.skills?.forEach((skillName: string) => {
        skillToDomain[skillName] = domainId;
      });
    });
  }

  // Calculate stats per domain from user skills
  const domainStats: Record<string, {
    totalLevel: number;
    skillsWithProgress: number;
    skillsCompleted: number;
  }> = {};

  // Initialize stats for all domains
  SKILL_DOMAINS.forEach(d => {
    domainStats[d.id] = {
      totalLevel: 0,
      skillsWithProgress: 0,
      skillsCompleted: 0,
    };
  });

  // Process user skills
  if (userSkillsData?.skills) {
    Object.entries(userSkillsData.skills).forEach(([skillName, skillData]) => {
      const domainId = skillToDomain[skillName];
      if (domainId && domainStats[domainId]) {
        const level = skillData.proficiency_level || 0;
        domainStats[domainId].totalLevel += level;
        domainStats[domainId].skillsWithProgress++;
        if (level >= 4) {
          domainStats[domainId].skillsCompleted++;
        }
      }
    });
  }

  // Create milestones
  let foundCurrent = false;
  const milestones: LearningMilestone[] = SKILL_DOMAINS.map((domain, index) => {
    const stats = domainStats[domain.id];
    const totalSkills = domainSkillCounts[domain.id] || 5;

    // Calculate progress: average proficiency level across all skills in domain
    // Max level is 5, so progress = (totalLevel / (totalSkills * 5)) * 100
    const maxPossibleLevel = totalSkills * 5;
    const progress = maxPossibleLevel > 0
      ? Math.round((stats.totalLevel / maxPossibleLevel) * 100)
      : 0;

    let status: LearningMilestone['status'];
    if (progress >= 80) {
      status = 'completed';
    } else if (!foundCurrent && progress > 0) {
      status = 'current';
      foundCurrent = true;
    } else if (!foundCurrent && index === 0) {
      status = 'current';
      foundCurrent = true;
    } else {
      status = 'available';
    }

    return {
      id: domain.id,
      name: domain.name,
      icon: domain.icon,
      color: domain.color,
      order: index + 1,
      status,
      progress,
      skillCount: totalSkills,
      skillsCompleted: stats.skillsCompleted,
      description: domain.description,
    };
  });

  return milestones;
}

export function useLearningPath() {
  const { data: userSkillsData, isLoading: skillsLoading, error: skillsError } = useQuery({
    queryKey: ['userSkills'],
    queryFn: skillsApi.getMySkills,
    staleTime: 5 * 60 * 1000,
  });

  const { data: skillTree, isLoading: treeLoading, error: treeError } = useQuery({
    queryKey: ['skillTree'],
    queryFn: skillsApi.getSkillTree,
    staleTime: 5 * 60 * 1000,
  });

  const milestones = useMemo(() => {
    return transformToMilestones(userSkillsData, skillTree);
  }, [userSkillsData, skillTree]);

  const overallProgress = useMemo(() => {
    if (!milestones.length) return 0;
    return Math.round(milestones.reduce((sum, m) => sum + m.progress, 0) / milestones.length);
  }, [milestones]);

  const currentMilestone = useMemo(() => {
    return milestones.find(m => m.status === 'current') || milestones[0];
  }, [milestones]);

  const completedCount = useMemo(() => {
    return milestones.filter(m => m.status === 'completed').length;
  }, [milestones]);

  // Use overall proficiency from API if available
  const apiOverallProgress = userSkillsData?.overall_proficiency
    ? Math.round((userSkillsData.overall_proficiency / 5) * 100)
    : overallProgress;

  return {
    milestones,
    overallProgress: apiOverallProgress,
    currentMilestone,
    completedCount,
    isLoading: skillsLoading || treeLoading,
    error: skillsError || treeError,
    userSkillsData,
    skillTree,
  };
}

export { SKILL_DOMAINS };
