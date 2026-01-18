"""
Service for auto-detecting objective completion in labs.

This service monitors terminal commands and can run verification scripts
to automatically detect when users complete lab objectives.
"""
import re
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


class ObjectiveVerifier:
    """
    Verifies objective completion via command monitoring and verification scripts.

    Features:
    - Command history tracking per session
    - Pattern matching against executed commands
    - Verification script execution (optional)
    - Multi-pattern support for complex objectives
    """

    def __init__(self):
        # session_id -> list of command entries
        self.command_history: Dict[str, List[Dict[str, Any]]] = {}
        # session_id -> accumulated input buffer (for building complete commands)
        self.input_buffers: Dict[str, str] = {}
        # Maximum commands to keep per session
        self.max_history_size = 100

    def log_command(self, session_id: str, command: str) -> None:
        """
        Log a command to session history.

        Args:
            session_id: The lab session identifier
            command: The command that was executed
        """
        if not session_id or not command:
            return

        # Clean up the command
        command = command.strip()
        if not command:
            return

        # Initialize history for new sessions
        if session_id not in self.command_history:
            self.command_history[session_id] = []

        # Add the command entry
        self.command_history[session_id].append({
            "command": command,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Trim history if too large
        if len(self.command_history[session_id]) > self.max_history_size:
            self.command_history[session_id] = self.command_history[session_id][-self.max_history_size:]

        logger.debug(
            "Command logged for auto-detection",
            session_id=session_id,
            command=command[:100],  # Truncate for logging
        )

    def process_terminal_input(self, session_id: str, data: str) -> Optional[str]:
        """
        Process terminal input and extract complete commands.

        Detects when Enter is pressed (carriage return) and extracts
        the command from the input buffer.

        Args:
            session_id: The lab session identifier
            data: Raw terminal input data

        Returns:
            The complete command if Enter was pressed, None otherwise
        """
        if not session_id or not data:
            return None

        # Initialize buffer for new sessions
        if session_id not in self.input_buffers:
            self.input_buffers[session_id] = ""

        # Check for Enter key (carriage return)
        if '\r' in data or '\n' in data:
            # Get the command from buffer + current data before Enter
            full_input = self.input_buffers[session_id] + data

            # Split by newlines/carriage returns
            parts = re.split(r'[\r\n]+', full_input)

            # The command is everything before the Enter
            command = parts[0].strip()

            # Reset buffer with anything after Enter (for next command)
            self.input_buffers[session_id] = parts[-1] if len(parts) > 1 else ""

            if command:
                self.log_command(session_id, command)
                return command
        else:
            # Accumulate input in buffer
            self.input_buffers[session_id] += data

            # Prevent buffer from growing too large
            if len(self.input_buffers[session_id]) > 10000:
                self.input_buffers[session_id] = self.input_buffers[session_id][-1000:]

        return None

    def check_command_pattern(self, session_id: str, pattern: str) -> bool:
        """
        Check if any command in history matches the given pattern.

        Args:
            session_id: The lab session identifier
            pattern: Regular expression pattern to match

        Returns:
            True if a matching command was found
        """
        if session_id not in self.command_history:
            return False

        try:
            regex = re.compile(pattern, re.IGNORECASE)
            for entry in self.command_history[session_id]:
                if regex.search(entry["command"]):
                    logger.info(
                        "Command pattern matched",
                        session_id=session_id,
                        pattern=pattern,
                        matched_command=entry["command"][:100],
                    )
                    return True
        except re.error as e:
            logger.error("Invalid regex pattern", pattern=pattern, error=str(e))

        return False

    def check_command_patterns(self, session_id: str, patterns: List[str]) -> bool:
        """
        Check if commands match ALL patterns (for multi-step objectives).

        Args:
            session_id: The lab session identifier
            patterns: List of regex patterns that must all be matched

        Returns:
            True if all patterns were matched
        """
        return all(self.check_command_pattern(session_id, p) for p in patterns)

    def check_any_command_pattern(self, session_id: str, patterns: List[str]) -> bool:
        """
        Check if commands match ANY of the patterns.

        Args:
            session_id: The lab session identifier
            patterns: List of regex patterns where at least one must match

        Returns:
            True if any pattern was matched
        """
        return any(self.check_command_pattern(session_id, p) for p in patterns)

    async def verify_objective(
        self,
        session_id: str,
        objective_config: Dict[str, Any],
        terminal_service: Any = None,
    ) -> bool:
        """
        Verify if an objective is completed using configured verification methods.

        Supports multiple verification methods:
        - command_pattern: Single regex pattern to match
        - command_patterns: Multiple patterns that must all match
        - any_command_pattern: Multiple patterns where any can match
        - verification_script: Script to run for verification

        Args:
            session_id: The lab session identifier
            objective_config: Configuration dict with verification settings
            terminal_service: Optional terminal service for running scripts

        Returns:
            True if the objective is verified as complete
        """
        # Check single command pattern
        if "command_pattern" in objective_config:
            if self.check_command_pattern(session_id, objective_config["command_pattern"]):
                return True

        # Check all patterns must match
        if "command_patterns" in objective_config:
            if self.check_command_patterns(session_id, objective_config["command_patterns"]):
                return True

        # Check any pattern matches
        if "any_command_pattern" in objective_config:
            if self.check_any_command_pattern(session_id, objective_config["any_command_pattern"]):
                return True

        # Run verification script if provided
        if "verification_script" in objective_config and terminal_service:
            try:
                result = await self.run_verification_script(
                    terminal_service,
                    objective_config["verification_script"]
                )
                if result:
                    return True
            except Exception as e:
                logger.error(
                    "Verification script failed",
                    session_id=session_id,
                    error=str(e),
                )

        return False

    async def run_verification_script(
        self,
        terminal_service: Any,
        script: str,
    ) -> bool:
        """
        Run a verification script and check the result.

        The script should exit with code 0 for success (objective complete)
        or non-zero for failure (objective not complete).

        Args:
            terminal_service: Terminal service to execute the script
            script: Shell script/command to run

        Returns:
            True if script exits with code 0
        """
        try:
            # Execute script and check exit code
            # This depends on the terminal service implementation
            if hasattr(terminal_service, 'execute_command'):
                result = await terminal_service.execute_command(script)
                return result.get('exit_code', 1) == 0
            elif hasattr(terminal_service, 'run_script'):
                exit_code = await terminal_service.run_script(script)
                return exit_code == 0
            else:
                logger.warning("Terminal service doesn't support script execution")
                return False
        except Exception as e:
            logger.error(f"Verification script failed: {e}")
            return False

    def get_command_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the command history for a session.

        Args:
            session_id: The lab session identifier

        Returns:
            List of command entries with timestamps
        """
        return self.command_history.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """
        Clear all data for a session.

        Args:
            session_id: The lab session identifier
        """
        if session_id in self.command_history:
            del self.command_history[session_id]
        if session_id in self.input_buffers:
            del self.input_buffers[session_id]
        logger.debug("Session data cleared", session_id=session_id)

    def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs being tracked.

        Returns:
            List of session IDs
        """
        return list(self.command_history.keys())


# Singleton instance for use across the application
objective_verifier = ObjectiveVerifier()
