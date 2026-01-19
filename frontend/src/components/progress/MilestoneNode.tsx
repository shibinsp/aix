import { LucideIcon, Lock, Check } from 'lucide-react';
import { LearningMilestone } from '@/hooks/useLearningPath';

interface MilestoneNodeProps {
  milestone: LearningMilestone;
  position: { x: number; y: number };
  isSelected: boolean;
  onClick: () => void;
  index: number;
}

const colorClasses: Record<string, {
  fill: string;
  stroke: string;
  glow: string;
  text: string;
  bg: string;
}> = {
  cyan: {
    fill: 'fill-cyan-500',
    stroke: 'stroke-cyan-400',
    glow: 'drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]',
    text: 'text-cyan-400',
    bg: 'bg-cyan-500/20',
  },
  purple: {
    fill: 'fill-purple-500',
    stroke: 'stroke-purple-400',
    glow: 'drop-shadow-[0_0_8px_rgba(168,85,247,0.6)]',
    text: 'text-purple-400',
    bg: 'bg-purple-500/20',
  },
  green: {
    fill: 'fill-emerald-500',
    stroke: 'stroke-emerald-400',
    glow: 'drop-shadow-[0_0_8px_rgba(52,211,153,0.6)]',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
  },
  orange: {
    fill: 'fill-orange-500',
    stroke: 'stroke-orange-400',
    glow: 'drop-shadow-[0_0_8px_rgba(249,115,22,0.6)]',
    text: 'text-orange-400',
    bg: 'bg-orange-500/20',
  },
  pink: {
    fill: 'fill-pink-500',
    stroke: 'stroke-pink-400',
    glow: 'drop-shadow-[0_0_8px_rgba(236,72,153,0.6)]',
    text: 'text-pink-400',
    bg: 'bg-pink-500/20',
  },
  red: {
    fill: 'fill-red-500',
    stroke: 'stroke-red-400',
    glow: 'drop-shadow-[0_0_8px_rgba(239,68,68,0.6)]',
    text: 'text-red-400',
    bg: 'bg-red-500/20',
  },
  blue: {
    fill: 'fill-blue-500',
    stroke: 'stroke-blue-400',
    glow: 'drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]',
    text: 'text-blue-400',
    bg: 'bg-blue-500/20',
  },
  emerald: {
    fill: 'fill-emerald-500',
    stroke: 'stroke-emerald-400',
    glow: 'drop-shadow-[0_0_8px_rgba(52,211,153,0.6)]',
    text: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
  },
};

export default function MilestoneNode({
  milestone,
  position,
  isSelected,
  onClick,
  index,
}: MilestoneNodeProps) {
  const colors = colorClasses[milestone.color] || colorClasses.cyan;
  const Icon = milestone.icon;
  const nodeRadius = 32;
  const progressRadius = 38;

  // Calculate progress arc
  const circumference = 2 * Math.PI * progressRadius;
  const progressOffset = circumference - (milestone.progress / 100) * circumference;

  return (
    <g
      className={`cursor-pointer transition-transform duration-300 ${
        isSelected ? 'scale-110' : 'hover:scale-105'
      }`}
      style={{
        transform: `translate(${position.x}px, ${position.y}px)`,
        animationDelay: `${index * 100}ms`,
      }}
      onClick={onClick}
    >
      {/* Glow effect for current milestone */}
      {milestone.status === 'current' && (
        <circle
          r={nodeRadius + 12}
          className={`${colors.fill} opacity-20 animate-pulse`}
        />
      )}

      {/* Progress ring */}
      <circle
        r={progressRadius}
        fill="none"
        strokeWidth="4"
        className="stroke-gray-700"
      />
      <circle
        r={progressRadius}
        fill="none"
        strokeWidth="4"
        className={`${colors.stroke} transition-all duration-1000`}
        strokeDasharray={circumference}
        strokeDashoffset={progressOffset}
        strokeLinecap="round"
        transform="rotate(-90)"
        style={{ filter: milestone.status === 'completed' ? colors.glow.replace('drop-shadow-[', '').replace(']', '') : undefined }}
      />

      {/* Main node circle */}
      <circle
        r={nodeRadius}
        className={`
          ${milestone.status === 'completed' ? colors.fill : 'fill-cyber-dark'}
          ${milestone.status === 'locked' ? 'stroke-gray-600 stroke-dashed' : colors.stroke}
          stroke-2 transition-all duration-300
          ${milestone.status === 'current' ? colors.glow : ''}
          ${isSelected ? 'stroke-[3]' : ''}
        `}
      />

      {/* Inner content */}
      {milestone.status === 'locked' ? (
        <foreignObject x={-12} y={-12} width={24} height={24}>
          <div className="flex items-center justify-center w-full h-full">
            <Lock className="w-6 h-6 text-gray-500" />
          </div>
        </foreignObject>
      ) : milestone.status === 'completed' ? (
        <foreignObject x={-14} y={-14} width={28} height={28}>
          <div className="flex items-center justify-center w-full h-full">
            <Check className="w-7 h-7 text-white" strokeWidth={3} />
          </div>
        </foreignObject>
      ) : (
        <foreignObject x={-14} y={-14} width={28} height={28}>
          <div className="flex items-center justify-center w-full h-full">
            <Icon className={`w-6 h-6 ${colors.text}`} />
          </div>
        </foreignObject>
      )}

      {/* Label below node */}
      <text
        y={nodeRadius + 20}
        textAnchor="middle"
        className={`text-xs font-medium fill-current ${
          milestone.status === 'locked' ? 'text-gray-500' : 'text-gray-300'
        }`}
      >
        {milestone.name}
      </text>

      {/* Progress percentage */}
      <text
        y={nodeRadius + 34}
        textAnchor="middle"
        className={`text-[10px] fill-current ${colors.text}`}
      >
        {milestone.progress}%
      </text>

      {/* Selection indicator */}
      {isSelected && (
        <circle
          r={nodeRadius + 20}
          fill="none"
          strokeWidth="2"
          className={`${colors.stroke} opacity-50`}
          strokeDasharray="4 4"
        />
      )}
    </g>
  );
}
