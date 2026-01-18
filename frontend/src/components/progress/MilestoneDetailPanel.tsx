import { LearningMilestone } from '@/hooks/useLearningPath';
import { CheckCircle2, Circle, Lock, ArrowRight, BookOpen, Target } from 'lucide-react';
import Link from 'next/link';

interface MilestoneDetailPanelProps {
  milestone: LearningMilestone | null;
}

const colorClasses: Record<string, {
  text: string;
  bg: string;
  border: string;
  button: string;
}> = {
  cyan: {
    text: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    button: 'bg-cyan-500 hover:bg-cyan-600',
  },
  purple: {
    text: 'text-purple-400',
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    button: 'bg-purple-500 hover:bg-purple-600',
  },
  green: {
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    button: 'bg-emerald-500 hover:bg-emerald-600',
  },
  orange: {
    text: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    button: 'bg-orange-500 hover:bg-orange-600',
  },
  pink: {
    text: 'text-pink-400',
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/30',
    button: 'bg-pink-500 hover:bg-pink-600',
  },
  red: {
    text: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    button: 'bg-red-500 hover:bg-red-600',
  },
  blue: {
    text: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    button: 'bg-blue-500 hover:bg-blue-600',
  },
  emerald: {
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    button: 'bg-emerald-500 hover:bg-emerald-600',
  },
};

export default function MilestoneDetailPanel({ milestone }: MilestoneDetailPanelProps) {
  if (!milestone) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Select a milestone to view details</p>
        </div>
      </div>
    );
  }

  const colors = colorClasses[milestone.color] || colorClasses.cyan;
  const Icon = milestone.icon;

  // Status badge
  const statusBadge = {
    completed: {
      text: 'Completed',
      className: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    },
    current: {
      text: 'In Progress',
      className: 'bg-cyber-accent/20 text-cyber-accent border-cyber-accent/30',
    },
    available: {
      text: 'Available',
      className: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    },
    locked: {
      text: 'Locked',
      className: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    },
  }[milestone.status];

  // Calculate circumference for circular progress
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const progressOffset = circumference - (milestone.progress / 100) * circumference;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className={`p-6 ${colors.bg} border-b ${colors.border}`}>
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl ${colors.bg} border ${colors.border}`}>
            <Icon className={`w-8 h-8 ${colors.text}`} />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-white">{milestone.name}</h2>
            <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full border ${statusBadge.className}`}>
              {statusBadge.text}
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Circular progress */}
        <div className="flex items-center justify-center">
          <div className="relative">
            <svg width="120" height="120" viewBox="0 0 120 120">
              {/* Background circle */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                strokeWidth="8"
                className="stroke-gray-700"
              />
              {/* Progress circle */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                strokeWidth="8"
                className={`${colors.text.replace('text-', 'stroke-')} transition-all duration-1000`}
                strokeDasharray={circumference}
                strokeDashoffset={progressOffset}
                strokeLinecap="round"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <span className={`text-3xl font-bold ${colors.text}`}>
                  {milestone.progress}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Description */}
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
            About
          </h3>
          <p className="text-gray-300">{milestone.description}</p>
        </div>

        {/* Skills progress */}
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Skills Progress
          </h3>
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-400">Mastered</span>
                <span className={`text-sm font-medium ${colors.text}`}>
                  {milestone.skillsCompleted} / {milestone.skillCount}
                </span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${colors.button.split(' ')[0]}`}
                  style={{ width: `${(milestone.skillsCompleted / milestone.skillCount) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Skills list (placeholder) */}
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Skills in this domain
          </h3>
          <ul className="space-y-2">
            {[...Array(Math.min(5, milestone.skillCount))].map((_, i) => (
              <li
                key={i}
                className="flex items-center gap-3 p-2 rounded-lg bg-cyber-dark/50"
              >
                {i < milestone.skillsCompleted ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                ) : milestone.status === 'locked' ? (
                  <Lock className="w-5 h-5 text-gray-500" />
                ) : (
                  <Circle className="w-5 h-5 text-gray-500" />
                )}
                <span className={i < milestone.skillsCompleted ? 'text-gray-300' : 'text-gray-500'}>
                  {milestone.name} Skill {i + 1}
                </span>
              </li>
            ))}
            {milestone.skillCount > 5 && (
              <li className="text-sm text-gray-500 pl-8">
                +{milestone.skillCount - 5} more skills
              </li>
            )}
          </ul>
        </div>
      </div>

      {/* Footer actions */}
      <div className="p-6 border-t border-gray-700/50">
        {milestone.status === 'locked' ? (
          <button
            disabled
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gray-700 text-gray-500 cursor-not-allowed"
          >
            <Lock className="w-5 h-5" />
            Complete previous domains first
          </button>
        ) : (
          <Link
            href={`/courses?category=${milestone.id}`}
            className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-white font-medium transition-colors ${colors.button}`}
          >
            <BookOpen className="w-5 h-5" />
            {milestone.status === 'completed' ? 'Review Courses' : 'Continue Learning'}
            <ArrowRight className="w-4 h-4" />
          </Link>
        )}
      </div>
    </div>
  );
}
