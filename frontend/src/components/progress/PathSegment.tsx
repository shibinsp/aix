interface PathSegmentProps {
  from: { x: number; y: number };
  to: { x: number; y: number };
  completed: boolean;
  index: number;
}

export default function PathSegment({ from, to, completed, index }: PathSegmentProps) {
  // Calculate control points for a curved path
  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;

  // Add some curve variation based on index
  const curveOffset = index % 2 === 0 ? 40 : -40;

  // Create bezier curve path
  const path = `M ${from.x} ${from.y} Q ${midX + curveOffset} ${midY} ${to.x} ${to.y}`;

  // Calculate path length for animation
  const pathLength = Math.sqrt(
    Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2)
  ) * 1.2; // Approximate curved path length

  return (
    <g>
      {/* Background path (gray) */}
      <path
        d={path}
        fill="none"
        strokeWidth="4"
        className="stroke-gray-700"
        strokeLinecap="round"
      />

      {/* Completed path (colored) */}
      {completed && (
        <path
          d={path}
          fill="none"
          strokeWidth="4"
          className="stroke-cyber-accent"
          strokeLinecap="round"
          strokeDasharray={pathLength}
          strokeDashoffset="0"
          style={{
            animation: `pathDraw 0.8s ease-out ${index * 0.15}s forwards`,
            filter: 'drop-shadow(0 0 4px rgba(0, 255, 157, 0.5))',
          }}
        />
      )}

      {/* Animated dots along the path for active segments */}
      {completed && (
        <circle r="3" className="fill-cyber-accent">
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            path={path}
          />
        </circle>
      )}
    </g>
  );
}
