"""
Mermaid Diagram Generator for educational content.

Generates various types of diagrams:
- Flowcharts
- Sequence diagrams
- Class diagrams
- State diagrams
- ER diagrams
"""

import json
import re
from typing import Dict, Any, List, Optional
import structlog

from app.services.ai.teaching_engine import teaching_engine

logger = structlog.get_logger()


class DiagramGenerator:
    """Service for generating Mermaid diagrams from content."""

    # Common diagram patterns for cybersecurity
    DIAGRAM_PATTERNS = {
        "flowchart": [
            "process", "workflow", "steps", "procedure", "flow",
            "how to", "attack chain", "kill chain", "phases"
        ],
        "sequence": [
            "communication", "protocol", "handshake", "request",
            "response", "interaction", "exchange", "authentication"
        ],
        "architecture": [
            "architecture", "system", "network", "infrastructure",
            "components", "layers", "topology"
        ],
        "state": [
            "state", "status", "lifecycle", "transition",
            "mode", "phase"
        ],
    }

    async def generate_diagram(
        self,
        description: str,
        diagram_type: str = "flowchart",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a Mermaid diagram from a description.

        Returns: {type, code, title, description}
        """
        type_instructions = {
            "flowchart": "Create a flowchart showing the process flow. Use 'graph TD' or 'graph LR'.",
            "sequence": "Create a sequence diagram showing interactions between parties. Use 'sequenceDiagram'.",
            "architecture": "Create a block diagram showing system architecture. Use 'graph TB' with subgraphs.",
            "state": "Create a state diagram showing state transitions. Use 'stateDiagram-v2'.",
        }

        instruction = type_instructions.get(diagram_type, type_instructions["flowchart"])

        prompt = f"""Generate a Mermaid diagram for the following concept:

Description: {description}
{f"Context: {context}" if context else ""}

Requirements:
1. {instruction}
2. Use clear, concise node labels
3. Include relevant connections and relationships
4. Keep it focused and not overly complex
5. Use appropriate styling if needed
6. Do NOT use HTML tags like <br> or &nbsp;. Use simple text labels only.

Return ONLY the Mermaid code, no markdown code blocks, no explanations.

Example format for flowchart:
graph TD
    A[Start] --> B[Process]
    B --> C{{Decision}}
    C -->|Yes| D[Action 1]
    C -->|No| E[Action 2]
    D --> F[End]
    E --> F

Generate the diagram now:"""

        messages = [{"role": "user", "content": prompt}]
        response = await teaching_engine.generate_response(
            messages,
            teaching_mode="lecture",
            temperature=0.5,
            max_tokens=1500,
        )

        # Clean the response
        code = self._clean_mermaid_code(response)

        # Validate the code
        if not self._validate_mermaid(code):
            # Try to fix common issues
            code = self._fix_common_issues(code)

            if not self._validate_mermaid(code):
                logger.warning("Invalid Mermaid code generated", description=description)
                code = self._generate_fallback_diagram(description, diagram_type)

        return {
            "type": "mermaid",
            "diagram_type": diagram_type,
            "code": code,
            "title": f"Diagram: {description[:50]}...",
            "description": description,
        }

    async def suggest_diagrams_for_lesson(
        self,
        content: str,
        lesson_title: str,
        max_diagrams: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Analyze lesson content and suggest appropriate diagrams.

        Returns list of diagram specifications.
        """
        # Determine what types of diagrams would be useful
        suggested_types = self._detect_diagram_opportunities(content)

        if not suggested_types:
            return []

        diagrams = []

        for diagram_type, topic in suggested_types[:max_diagrams]:
            try:
                diagram = await self.generate_diagram(
                    description=topic,
                    diagram_type=diagram_type,
                    context=f"From lesson: {lesson_title}",
                )
                if diagram.get("code"):
                    diagrams.append(diagram)
            except Exception as e:
                logger.error("Failed to generate diagram", error=str(e), topic=topic)

        return diagrams

    def _detect_diagram_opportunities(
        self,
        content: str,
    ) -> List[tuple]:
        """Detect what diagrams would enhance the content."""
        content_lower = content.lower()
        opportunities = []

        for diagram_type, keywords in self.DIAGRAM_PATTERNS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    # Extract relevant sentence/context
                    sentences = content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            topic = sentence.strip()[:100]
                            if topic and len(topic) > 20:
                                opportunities.append((diagram_type, topic))
                                break
                    break

        return opportunities

    def _clean_mermaid_code(self, response: str) -> str:
        """Clean and extract Mermaid code from AI response."""
        # Remove markdown code blocks
        response = response.strip()

        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first line (```mermaid or ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # Remove any leading/trailing whitespace
        return response.strip()

    def _validate_mermaid(self, code: str) -> bool:
        """Basic validation of Mermaid syntax."""
        if not code or len(code) < 10:
            return False

        # Check for valid diagram type declaration
        valid_starts = [
            "graph", "flowchart", "sequenceDiagram", "classDiagram",
            "stateDiagram", "erDiagram", "pie", "gantt", "journey",
            "gitGraph", "mindmap", "timeline", "block-beta"
        ]

        first_line = code.strip().split("\n")[0].strip()
        has_valid_start = any(first_line.startswith(start) for start in valid_starts)

        if not has_valid_start:
            return False

        # Check for balanced brackets
        if code.count("[") != code.count("]"):
            return False
        if code.count("{") != code.count("}"):
            return False
        if code.count("(") != code.count(")"):
            return False

        return True

    def _fix_common_issues(self, code: str) -> str:
        """Fix common Mermaid syntax issues."""
        # Remove any text before the graph declaration
        for start in ["graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram"]:
            if start in code:
                idx = code.find(start)
                code = code[idx:]
                break

        # Fix common issues
        lines = code.split("\n")
        fixed_lines = []

        for line in lines:
            # Skip empty lines at start
            if not fixed_lines and not line.strip():
                continue

            # Remove HTML br tags (common AI mistake)
            line = re.sub(r'<br\s*/?>', ' ', line)

            # Remove other HTML tags that might cause issues
            line = re.sub(r'&nbsp;', ' ', line)

            # Fix arrows with spaces
            line = re.sub(r'\s*-->\s*', ' --> ', line)
            line = re.sub(r'\s*--->\s*', ' ---> ', line)
            line = re.sub(r'\s*-\.->\s*', ' -.-> ', line)

            # Fix node IDs with spaces (wrap in quotes)
            # This is a simplified fix

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _generate_fallback_diagram(
        self,
        description: str,
        diagram_type: str,
    ) -> str:
        """Generate a simple fallback diagram."""
        # Create a simple but valid diagram based on the description
        words = description.split()[:5]
        title = " ".join(words).title()

        if diagram_type == "sequence":
            return f"""sequenceDiagram
    participant A as Client
    participant B as Server
    A->>B: Request
    B-->>A: Response"""

        elif diagram_type == "state":
            return f"""stateDiagram-v2
    [*] --> Initial
    Initial --> Processing
    Processing --> Complete
    Complete --> [*]"""

        else:  # Default to flowchart
            return f"""graph TD
    A[Start: {title}] --> B[Process]
    B --> C[Complete]"""

    async def generate_network_diagram(
        self,
        components: List[str],
        connections: Optional[List[tuple]] = None,
    ) -> Dict[str, Any]:
        """Generate a network/infrastructure diagram."""
        if not connections:
            # Generate logical connections
            diagram_parts = ["graph TB"]

            # Add subgraphs for different network zones
            diagram_parts.append("    subgraph External")
            diagram_parts.append("        Internet((Internet))")
            diagram_parts.append("    end")

            diagram_parts.append("    subgraph DMZ")
            for comp in components[:2]:
                safe_id = comp.replace(" ", "_").replace("-", "_")
                diagram_parts.append(f"        {safe_id}[{comp}]")
            diagram_parts.append("    end")

            diagram_parts.append("    subgraph Internal")
            for comp in components[2:]:
                safe_id = comp.replace(" ", "_").replace("-", "_")
                diagram_parts.append(f"        {safe_id}[{comp}]")
            diagram_parts.append("    end")

            # Add connections
            diagram_parts.append("    Internet --> DMZ")
            diagram_parts.append("    DMZ --> Internal")

            code = "\n".join(diagram_parts)
        else:
            # Use provided connections
            diagram_parts = ["graph TB"]

            # Add all components
            for comp in components:
                safe_id = comp.replace(" ", "_").replace("-", "_")
                diagram_parts.append(f"    {safe_id}[{comp}]")

            # Add connections
            for source, target in connections:
                safe_source = source.replace(" ", "_").replace("-", "_")
                safe_target = target.replace(" ", "_").replace("-", "_")
                diagram_parts.append(f"    {safe_source} --> {safe_target}")

            code = "\n".join(diagram_parts)

        return {
            "type": "mermaid",
            "diagram_type": "architecture",
            "code": code,
            "title": "Network Architecture",
            "description": "Network infrastructure diagram",
        }

    async def generate_attack_flow(
        self,
        attack_name: str,
        steps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate an attack flow diagram."""
        if not steps:
            prompt = f"""Create a detailed attack flow diagram for: {attack_name}

Generate a Mermaid flowchart showing:
1. Initial access/entry point
2. Each step of the attack
3. Decision points
4. Final objective

Use 'graph TD' format with clear node labels.
Return ONLY the Mermaid code:"""

            messages = [{"role": "user", "content": prompt}]
            response = await teaching_engine.generate_response(
                messages,
                temperature=0.5,
                max_tokens=1000,
            )

            code = self._clean_mermaid_code(response)
        else:
            # Build from provided steps
            diagram_parts = ["graph TD"]
            prev_id = None

            for i, step in enumerate(steps):
                step_id = f"step{i}"
                safe_label = step.replace('"', "'")

                if i == 0:
                    diagram_parts.append(f"    {step_id}[[\"{safe_label}\"]]")
                elif i == len(steps) - 1:
                    diagram_parts.append(f"    {step_id}((\"{safe_label}\"))")
                else:
                    diagram_parts.append(f"    {step_id}[\"{safe_label}\"]")

                if prev_id:
                    diagram_parts.append(f"    {prev_id} --> {step_id}")

                prev_id = step_id

            code = "\n".join(diagram_parts)

        return {
            "type": "mermaid",
            "diagram_type": "flowchart",
            "code": code,
            "title": f"Attack Flow: {attack_name}",
            "description": f"Attack methodology for {attack_name}",
        }


# Singleton instance
diagram_generator = DiagramGenerator()
