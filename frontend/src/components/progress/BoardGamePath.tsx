import { useMemo } from 'react';
import { Flag, Trophy } from 'lucide-react';
import { LearningMilestone } from '@/hooks/useLearningPath';
import MilestoneNode from './MilestoneNode';
import PathSegment from './PathSegment';

interface BoardGamePathProps {
  milestones: LearningMilestone[];
  selectedId?: string;
  onMilestoneClick: (id: string) => void;
}

export default function BoardGamePath({
  milestones,
  selectedId,
  onMilestoneClick,
}: BoardGamePathProps) {
  // SVG dimensions
  const width = 800;
  const height = 1100;
  const padding = 80;

  // Calculate node positions in a winding path pattern
  const nodePositions = useMemo(() => {
    const positions: Array<{ x: number; y: number }> = [];
    const verticalSpacing = (height - padding * 2 - 100) / (milestones.length);

    milestones.forEach((_, index) => {
      // Create a snake/S-curve pattern
      const y = padding + 60 + index * verticalSpacing;

      // Alternate between left and right sides with some variation
      let x;
      if (index % 4 === 0) {
        x = padding + 100;
      } else if (index % 4 === 1) {
        x = width / 2;
      } else if (index % 4 === 2) {
        x = width - padding - 100;
      } else {
        x = width / 2;
      }

      positions.push({ x, y });
    });

    return positions;
  }, [milestones.length]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full max-w-3xl mx-auto"
      style={{ minHeight: '700px' }}
    >
      {/* Definitions */}
      <defs>
        {/* Grid pattern */}
        <pattern
          id="cyber-grid-pattern"
          width="40"
          height="40"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 40 0 L 0 0 0 40"
            fill="none"
            stroke="rgba(0, 255, 157, 0.05)"
            strokeWidth="1"
          />
        </pattern>

        {/* Glow filters */}
        <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Path animation keyframes */}
        <style>
          {`
            @keyframes pathDraw {
              from { stroke-dashoffset: 200; }
              to { stroke-dashoffset: 0; }
            }
            @keyframes nodeAppear {
              from { transform: scale(0); opacity: 0; }
              to { transform: scale(1); opacity: 1; }
            }
            @keyframes float {
              0%, 100% { transform: translateY(0); }
              50% { transform: translateY(-5px); }
            }
          `}
        </style>
      </defs>

      {/* Background grid */}
      <rect
        width={width}
        height={height}
        fill="url(#cyber-grid-pattern)"
        opacity="0.5"
      />

      {/* Start marker */}
      <g transform={`translate(${nodePositions[0]?.x || padding}, ${padding})`}>
        <circle
          r="24"
          className="fill-cyber-dark stroke-cyber-accent stroke-2"
          filter="url(#glow-green)"
        />
        <foreignObject x={-10} y={-10} width={20} height={20}>
          <div className="flex items-center justify-center w-full h-full">
            <Flag className="w-5 h-5 text-cyber-accent" />
          </div>
        </foreignObject>
        <text
          y={-35}
          textAnchor="middle"
          className="text-sm font-bold fill-cyber-accent"
        >
          START
        </text>
      </g>

      {/* Path segments connecting milestones */}
      {nodePositions.length > 0 && (
        <>
          {/* Start to first milestone */}
          <PathSegment
            from={{ x: nodePositions[0].x, y: padding + 24 }}
            to={{ x: nodePositions[0].x, y: nodePositions[0].y - 45 }}
            completed={true}
            index={0}
          />

          {/* Between milestones */}
          {milestones.slice(0, -1).map((milestone, index) => (
            <PathSegment
              key={`path-${index}`}
              from={{
                x: nodePositions[index].x,
                y: nodePositions[index].y + 45,
              }}
              to={{
                x: nodePositions[index + 1].x,
                y: nodePositions[index + 1].y - 45,
              }}
              completed={milestone.status === 'completed'}
              index={index + 1}
            />
          ))}
        </>
      )}

      {/* Milestone nodes */}
      {milestones.map((milestone, index) => (
        <MilestoneNode
          key={milestone.id}
          milestone={milestone}
          position={nodePositions[index]}
          isSelected={milestone.id === selectedId}
          onClick={() => onMilestoneClick(milestone.id)}
          index={index}
        />
      ))}

      {/* Expert trophy at the end */}
      {nodePositions.length > 0 && (
        <g
          transform={`translate(${nodePositions[nodePositions.length - 1]?.x || width / 2}, ${height - padding})`}
          style={{ animation: 'float 3s ease-in-out infinite' }}
        >
          <circle
            r="30"
            className="fill-yellow-500/20 stroke-yellow-400 stroke-2"
            filter="url(#glow-gold)"
          />
          <foreignObject x={-14} y={-14} width={28} height={28}>
            <div className="flex items-center justify-center w-full h-full">
              <Trophy className="w-7 h-7 text-yellow-400" />
            </div>
          </foreignObject>
          <text
            y={50}
            textAnchor="middle"
            className="text-sm font-bold fill-yellow-400"
          >
            EXPERT
          </text>
        </g>
      )}

      {/* Decorative elements */}
      {[...Array(5)].map((_, i) => (
        <circle
          key={`deco-${i}`}
          cx={100 + i * 150}
          cy={50 + (i % 3) * 30}
          r="2"
          className="fill-cyber-accent/30"
          style={{
            animation: `float ${2 + i * 0.5}s ease-in-out infinite`,
            animationDelay: `${i * 0.3}s`,
          }}
        />
      ))}
    </svg>
  );
}
