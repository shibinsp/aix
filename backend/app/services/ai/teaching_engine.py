import asyncio
from typing import AsyncGenerator, Optional, List, Dict, Any
import structlog
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

from app.core.config import settings
from app.services.ai.prompts import SystemPrompts

logger = structlog.get_logger()


class TeachingEngine:
    """AI Teaching Engine for cybersecurity education."""

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.mistral_client = None
        self.gemini_model = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AI provider clients."""
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Mistral uses OpenAI-compatible API
        if settings.MISTRAL_API_KEY:
            self.mistral_client = AsyncOpenAI(
                api_key=settings.MISTRAL_API_KEY,
                base_url="https://api.mistral.ai/v1"
            )

        # Initialize Gemini - use gemini-2.0-flash (stable version)
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        teaching_mode: str = "lecture",
        skill_level: str = "beginner",
        rag_context: Optional[str] = None,
        lab_context: Optional[Dict[str, Any]] = None,
        course_context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a non-streaming response."""
        model = model or settings.DEFAULT_AI_MODEL
        logger.info(f"Using AI model: {model}, DEFAULT_AI_MODEL: {settings.DEFAULT_AI_MODEL}")
        system_prompt = SystemPrompts.build_system_prompt(
            teaching_mode=teaching_mode,
            skill_level=skill_level,
            rag_context=rag_context,
            lab_context=lab_context,
            course_context=course_context,
        )

        if "claude" in model.lower():
            return await self._generate_anthropic(
                messages, system_prompt, model, max_tokens, temperature
            )
        elif "mistral" in model.lower():
            return await self._generate_mistral(
                messages, system_prompt, model, max_tokens, temperature
            )
        elif "gemini" in model.lower():
            return await self._generate_gemini(
                messages, system_prompt, model, max_tokens, temperature
            )
        elif self.mistral_client:
            return await self._generate_mistral(
                messages, system_prompt, model, max_tokens, temperature
            )
        elif self.gemini_model:
            return await self._generate_gemini(
                messages, system_prompt, model, max_tokens, temperature
            )
        else:
            return await self._generate_openai(
                messages, system_prompt, model, max_tokens, temperature
            )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        teaching_mode: str = "lecture",
        skill_level: str = "beginner",
        rag_context: Optional[str] = None,
        lab_context: Optional[Dict[str, Any]] = None,
        course_context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        model = model or settings.DEFAULT_AI_MODEL
        system_prompt = SystemPrompts.build_system_prompt(
            teaching_mode=teaching_mode,
            skill_level=skill_level,
            rag_context=rag_context,
            lab_context=lab_context,
            course_context=course_context,
        )

        if "claude" in model.lower():
            async for chunk in self._stream_anthropic(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk
        elif "mistral" in model.lower():
            async for chunk in self._stream_mistral(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk
        elif "gemini" in model.lower():
            async for chunk in self._stream_gemini(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk
        elif self.mistral_client:
            async for chunk in self._stream_mistral(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk
        elif self.gemini_model:
            async for chunk in self._stream_gemini(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk
        else:
            async for chunk in self._stream_openai(
                messages, system_prompt, model, max_tokens, temperature
            ):
                yield chunk

    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate response using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self.openai_client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content

    async def _stream_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        stream = await self.openai_client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _generate_mistral(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate response using Mistral AI."""
        if not self.mistral_client:
            raise ValueError("Mistral client not initialized. Set MISTRAL_API_KEY.")

        # Use mistral-large as default if no specific model
        if "mistral" not in model.lower():
            model = "mistral-large-latest"

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self.mistral_client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content

    async def _stream_mistral(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response using Mistral AI."""
        if not self.mistral_client:
            raise ValueError("Mistral client not initialized. Set MISTRAL_API_KEY.")

        if "mistral" not in model.lower():
            model = "mistral-large-latest"

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        stream = await self.mistral_client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _generate_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate response using Google Gemini."""
        if not self.gemini_model:
            raise ValueError("Gemini client not initialized. Set GEMINI_API_KEY.")

        # Combine system prompt with user messages
        full_prompt = f"{system_prompt}\n\n"
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                full_prompt += f"User: {content}\n"
            elif role == "assistant":
                full_prompt += f"Assistant: {content}\n"

        # Configure generation settings
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # Generate response
        response = await asyncio.to_thread(
            self.gemini_model.generate_content,
            full_prompt,
            generation_config=generation_config,
        )

        return response.text

    async def _stream_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response using Google Gemini."""
        if not self.gemini_model:
            raise ValueError("Gemini client not initialized. Set GEMINI_API_KEY.")

        # Combine system prompt with user messages
        full_prompt = f"{system_prompt}\n\n"
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                full_prompt += f"User: {content}\n"
            elif role == "assistant":
                full_prompt += f"Assistant: {content}\n"

        # Configure generation settings
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # Generate streaming response
        response = await asyncio.to_thread(
            self.gemini_model.generate_content,
            full_prompt,
            generation_config=generation_config,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Generate response using Anthropic."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized. Set ANTHROPIC_API_KEY.")

        response = await self.anthropic_client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.content[0].text

    async def _stream_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream response using Anthropic."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized. Set ANTHROPIC_API_KEY.")

        async with self.anthropic_client.messages.stream(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from AI response."""
        import re
        import json

        # Strip markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last lines if they're code block markers
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # Find the JSON object
        start = response.find("{")
        end = response.rfind("}") + 1

        if start == -1 or end == 0:
            return ""

        json_str = response[start:end]

        # Try parsing as-is first
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

        # Common fixes for malformed JSON
        # Fix trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        # Fix missing commas between objects
        json_str = re.sub(r'}\s*{', '},{', json_str)
        # Fix missing commas between array elements ("] [" or "] {")
        json_str = re.sub(r'\]\s*\[', '],[', json_str)
        json_str = re.sub(r'\]\s*\{', '],{', json_str)
        # Fix single quotes to double quotes for keys
        json_str = re.sub(r"'([^']+)'(\s*:)", r'"\1"\2', json_str)
        # Fix missing commas after string values followed by quotes
        json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
        # Fix missing commas between properties (value followed by key)
        json_str = re.sub(r'(\d)\s*\n\s*"', r'\1,\n"', json_str)
        json_str = re.sub(r'(true|false|null)\s*\n\s*"', r'\1,\n"', json_str)
        # Fix unescaped control characters in strings
        json_str = re.sub(r'[\x00-\x1f]', lambda m: '\\u{:04x}'.format(ord(m.group(0))) if m.group(0) not in '\n\r\t' else m.group(0), json_str)

        # Try parsing again
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

        # More aggressive repair: fix newlines inside strings
        # This is a character-by-character approach to find unescaped newlines in strings
        result = []
        in_string = False
        escape_next = False
        for i, char in enumerate(json_str):
            if escape_next:
                result.append(char)
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                result.append(char)
                continue
            if char == '"':
                in_string = not in_string
                result.append(char)
                continue
            if in_string and char == '\n':
                result.append('\\n')
                continue
            if in_string and char == '\r':
                result.append('\\r')
                continue
            if in_string and char == '\t':
                result.append('\\t')
                continue
            result.append(char)

        json_str = ''.join(result)

        return json_str

    async def generate_course_content(
        self,
        topic: str,
        difficulty: str = "beginner",
        num_modules: int = 5,
    ) -> Dict[str, Any]:
        """Generate AI course content."""
        prompt = f"""Create a comprehensive cybersecurity course on "{topic}" for {difficulty} level students.

Generate a structured course with {num_modules} modules. For each module, provide:
1. Module title
2. Module description
3. 3-4 lesson titles with brief descriptions

IMPORTANT: Return ONLY valid JSON, no markdown, no extra text. Use this exact format:
{{
    "title": "Course Title",
    "description": "Course description (2-3 sentences)",
    "modules": [
        {{
            "title": "Module 1 Title",
            "description": "Module description",
            "lessons": [
                {{"title": "Lesson 1", "description": "Brief description", "type": "text"}},
                {{"title": "Lesson 2", "description": "Brief description", "type": "text"}}
            ]
        }}
    ]
}}

Focus on practical, hands-on learning with real-world applications. Keep descriptions concise."""

        messages = [{"role": "user", "content": prompt}]
        response = await self.generate_response(
            messages,
            teaching_mode="lecture",
            skill_level=difficulty,
            temperature=0.5,  # Lower temperature for more consistent JSON
            max_tokens=3000,
        )

        # Parse JSON from response
        import json
        try:
            json_str = self._clean_json_response(response)
            if not json_str:
                raise ValueError("No JSON found in response")
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse course content", error=str(e), response_preview=response[:500])
            # Return a default structure on failure
            return {
                "title": f"{topic} Course",
                "description": f"A comprehensive course on {topic} for {difficulty} level students.",
                "modules": [
                    {
                        "title": f"Introduction to {topic}",
                        "description": f"Getting started with {topic}",
                        "lessons": [
                            {"title": "Overview", "description": f"Understanding {topic} fundamentals", "type": "text"},
                            {"title": "Core Concepts", "description": "Key concepts and terminology", "type": "text"},
                            {"title": "Practical Applications", "description": "Real-world use cases", "type": "text"}
                        ]
                    },
                    {
                        "title": f"{topic} Techniques",
                        "description": "Hands-on techniques and methods",
                        "lessons": [
                            {"title": "Basic Techniques", "description": "Fundamental approaches", "type": "text"},
                            {"title": "Advanced Methods", "description": "More sophisticated techniques", "type": "text"}
                        ]
                    },
                    {
                        "title": "Best Practices",
                        "description": "Industry standards and recommendations",
                        "lessons": [
                            {"title": "Security Guidelines", "description": "Following security best practices", "type": "text"},
                            {"title": "Common Pitfalls", "description": "Avoiding common mistakes", "type": "text"}
                        ]
                    }
                ]
            }

    async def generate_lab_scenario(
        self,
        topic: str,
        lab_type: str = "challenge",
        difficulty: str = "intermediate",
    ) -> Dict[str, Any]:
        """Generate AI lab scenario."""
        prompt = f"""Create a cybersecurity lab scenario about "{topic}".

Lab Type: {lab_type}
Difficulty: {difficulty}

Generate a complete lab specification including:
1. Title and description
2. Learning objectives (3-5 specific skills)
3. Infrastructure needed (containers, networks)
4. Step-by-step instructions
5. 2-3 flags to capture with hints
6. Success criteria

Return in JSON format:
{{
    "title": "Lab Title",
    "description": "Lab description",
    "objectives": ["Objective 1", ...],
    "infrastructure_spec": {{
        "containers": [
            {{"name": "target", "image": "suggested-image", "ports": ["80:80"]}}
        ],
        "networks": ["lab_network"]
    }},
    "instructions": "Markdown formatted instructions...",
    "flags": [
        {{"name": "flag1", "hint": "Hint text", "points": 25}}
    ],
    "estimated_time": 45
}}"""

        messages = [{"role": "user", "content": prompt}]
        response = await self.generate_response(
            messages,
            teaching_mode="challenge",
            skill_level=difficulty,
            temperature=0.8,
        )

        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse lab scenario", error=str(e))
            return {"error": "Failed to generate lab scenario"}

    async def assess_skill(
        self,
        skill_name: str,
        user_response: str,
        question: str,
        difficulty: float = 0.5,
    ) -> Dict[str, Any]:
        """Assess user's skill based on their response."""
        prompt = f"""Evaluate this cybersecurity assessment response.

Skill Being Assessed: {skill_name}
Question Difficulty: {difficulty} (0.0 = easy, 1.0 = hard)

Question: {question}

Student's Response: {user_response}

Evaluate the response and provide:
1. Is the answer correct? (true/false)
2. Score from 0-100
3. What they got right
4. What they got wrong or missed
5. Brief feedback for improvement

Return JSON:
{{
    "correct": true/false,
    "score": 0-100,
    "strengths": ["list of correct points"],
    "weaknesses": ["list of errors or gaps"],
    "feedback": "Constructive feedback message"
}}"""

        messages = [{"role": "user", "content": prompt}]
        response = await self.generate_response(
            messages,
            teaching_mode="challenge",
            temperature=0.3,
        )

        import json
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Failed to parse skill assessment", error=str(e))
            return {"error": "Failed to assess response", "correct": False, "score": 0}


# Singleton instance
teaching_engine = TeachingEngine()
