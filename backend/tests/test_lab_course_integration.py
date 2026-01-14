"""Tests for lab-course integration functionality."""
import pytest
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

# Mock chromadb before any imports
sys.modules['chromadb'] = Mock()
sys.modules['chromadb.config'] = Mock()
sys.modules['sentence_transformers'] = Mock()
sys.modules['langchain'] = Mock()
sys.modules['langchain.text_splitter'] = Mock()
sys.modules['langchain_community'] = Mock()
sys.modules['langchain_community.embeddings'] = Mock()
sys.modules['langchain_openai'] = Mock()


class TestLabCourseIntegrationService:
    """Test the LabCourseIntegrationService class."""

    def test_get_workspace_path(self):
        """Test workspace path generation."""
        from app.services.labs.lab_course_integration import LabCourseIntegrationService

        service = LabCourseIntegrationService()
        course_id = "test-course-123"

        expected = f"/home/alphha/courses/{course_id}"
        result = service._get_workspace_path(course_id)

        assert result == expected

    def test_get_env_type_for_terminal_lab(self):
        """Test environment type detection for terminal labs."""
        from app.services.labs.lab_course_integration import LabCourseIntegrationService

        service = LabCourseIntegrationService()

        # Mock lab with terminal type
        mock_lab = Mock()
        mock_lab.lab_type = "terminal"

        result = service._get_env_type_for_lab(mock_lab)
        assert result == "terminal"

    def test_get_env_type_for_desktop_lab(self):
        """Test environment type detection for desktop labs."""
        from app.services.labs.lab_course_integration import LabCourseIntegrationService

        service = LabCourseIntegrationService()

        # Mock lab with desktop type
        mock_lab = Mock()
        mock_lab.lab_type = "desktop"

        result = service._get_env_type_for_lab(mock_lab)
        assert result == "desktop"

    def test_get_env_type_for_gui_lab(self):
        """Test environment type detection for GUI labs."""
        from app.services.labs.lab_course_integration import LabCourseIntegrationService

        service = LabCourseIntegrationService()

        # Mock lab with GUI type
        mock_lab = Mock()
        mock_lab.lab_type = "gui_based"

        result = service._get_env_type_for_lab(mock_lab)
        assert result == "desktop"

    def test_get_env_type_defaults_to_terminal(self):
        """Test that default environment type is terminal."""
        from app.services.labs.lab_course_integration import LabCourseIntegrationService

        service = LabCourseIntegrationService()

        # Mock lab with unknown type
        mock_lab = Mock()
        mock_lab.lab_type = "challenge"

        result = service._get_env_type_for_lab(mock_lab)
        assert result == "terminal"


class TestPersistentEnvironmentManager:
    """Test the PersistentEnvironmentManager class."""

    def test_get_volume_name(self):
        """Test shared volume name generation."""
        from app.services.environments.persistent_env_manager import PersistentEnvironmentManager

        manager = PersistentEnvironmentManager()
        user_id = "12345678-1234-1234-1234-123456789abc"

        result = manager._get_volume_name(user_id)

        # Should use first 8 chars of user_id
        assert "12345678" in result
        assert "data" in result

    def test_allocate_port(self):
        """Test port allocation returns valid port."""
        from app.services.environments.persistent_env_manager import PersistentEnvironmentManager

        manager = PersistentEnvironmentManager()

        # Test port allocation
        port = manager._allocate_port(10000)

        # Should return a port >= base port
        assert port >= 10000

    def test_get_container_name(self):
        """Test container name generation."""
        from app.services.environments.persistent_env_manager import PersistentEnvironmentManager

        manager = PersistentEnvironmentManager()
        user_id = "12345678-1234-1234-1234-123456789abc"

        result = manager._get_container_name(user_id, "terminal")

        # Should contain user_id prefix and env type
        assert "12345678" in result
        assert "terminal" in result

    def test_manager_has_docker_methods(self):
        """Test that manager has required Docker methods."""
        from app.services.environments.persistent_env_manager import PersistentEnvironmentManager

        manager = PersistentEnvironmentManager()

        # Check required methods exist
        assert hasattr(manager, 'start_environment')
        assert hasattr(manager, 'stop_environment')
        assert hasattr(manager, 'reset_environment')
        assert hasattr(manager, 'get_environment_status')
        assert hasattr(manager, 'check_docker_available')


class TestLabSessionModel:
    """Test the LabSession model fields."""

    def test_lab_session_has_course_fields(self):
        """Test that LabSession model has course integration fields."""
        from app.models.lab import LabSession

        # Check that the model has the required columns
        columns = [c.name for c in LabSession.__table__.columns]

        assert 'course_id' in columns
        assert 'lesson_id' in columns
        assert 'completed_objectives' in columns
        assert 'last_activity' in columns
        assert 'ended_at' in columns
        assert 'duration_minutes' in columns


class TestLabsAPIRoutes:
    """Test the labs API routes exist."""

    def test_start_in_course_route_exists(self):
        """Test that start-in-course route is defined."""
        from app.api.routes.labs import router

        routes = [r.path for r in router.routes]
        assert '/start-in-course' in routes

    def test_complete_objective_route_exists(self):
        """Test that complete objective route is defined."""
        from app.api.routes.labs import router

        routes = [r.path for r in router.routes]
        assert '/sessions/{session_id}/objectives/{objective_index}/complete' in routes

    def test_progress_route_exists(self):
        """Test that progress route is defined."""
        from app.api.routes.labs import router

        routes = [r.path for r in router.routes]
        assert '/progress/{course_id}' in routes

    def test_end_session_route_exists(self):
        """Test that end session route is defined."""
        from app.api.routes.labs import router

        routes = [r.path for r in router.routes]
        assert '/sessions/{session_id}/end' in routes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
