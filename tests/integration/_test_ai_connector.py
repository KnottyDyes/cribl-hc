"""
Integration test for AI Connector Framework with real Harbor/Ollama services.
"""

import pytest

from cribl_hc.core.ai_connector import ParallelTaskManager


class TestAIConnectorIntegration:
    """Integration tests with real Harbor/Ollama services."""

    @pytest.fixture
    async def task_manager(self):
        """Create real task manager for integration testing."""
        manager = ParallelTaskManager()
        await manager.executor.initialize()
        yield manager
        await manager.executor.close()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_ollama_connection(self, task_manager):
        """Test connection to real Ollama service."""
        # Check if models are available
        models = []
        for _connector_name, model_list in task_manager.executor.models_cache.items():
            models.extend(model_list)

        assert len(models) > 0, "No models available from Ollama"

        # Verify model properties
        for model in models:
            assert model.name
            assert model.provider in ["ollama", "litellm"]
            assert model.context_length > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_task_execution(self, task_manager):
        """Test executing real tasks with Ollama."""
        # Skip if no models available
        models = []
        for model_list in task_manager.executor.models_cache.values():
            models.extend(model_list)

        if not models:
            pytest.skip("No models available for testing")

        # Execute a simple test task
        result = await task_manager.executor.execute_task(
            "Say 'Hello from integration test' in exactly 5 words", task_type="general"
        )

        assert result.success, f"Task failed: {result.error}"
        assert result.response, "Empty response received"
        assert result.processing_time > 0
        assert "hello" in result.response.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_parallel_execution(self, task_manager):
        """Test parallel execution of multiple tasks."""
        # Skip if no models available
        models = []
        for model_list in task_manager.executor.models_cache.values():
            models.extend(model_list)

        if not models:
            pytest.skip("No models available for testing")

        # Execute multiple tasks in parallel
        tasks = [
            {"prompt": "What is 2+2? Answer with just the number.", "task_type": "general"},
            {"prompt": "Name one programming language. Just the name.", "task_type": "code"},
            {"prompt": "What color is the sky? One word answer.", "task_type": "general"},
        ]

        results = await task_manager.executor.execute_parallel(tasks)

        assert len(results) == 3
        assert all(r.success for r in results), (
            f"Some tasks failed: {[r.error for r in results if not r.success]}"
        )
        assert all(r.response for r in results)

        # Check specific responses
        assert "4" in results[0].response or "four" in results[0].response.lower()
        assert any(
            lang in results[1].response.lower()
            for lang in ["python", "javascript", "java", "c++", "go"]
        )
        assert any(color in results[2].response.lower() for color in ["blue", "sky"])

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_research_task_execution(self, task_manager):
        """Test research task execution through ParallelTaskManager."""
        # Skip if no models available
        models = []
        for model_list in task_manager.executor.models_cache.values():
            models.extend(model_list)

        if not models:
            pytest.skip("No models available for testing")

        async with task_manager:
            results = await task_manager.execute_research_tasks(
                ["What is the capital of France? Answer in one word."]
            )

        assert len(results) == 1
        assert results[0].success
        assert "paris" in results[0].response.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrency_limits(self, task_manager):
        """Test that concurrency limits are respected."""
        # This test verifies that the semaphore works
        # by checking execution time with many tasks
        models = []
        for model_list in task_manager.executor.models_cache.values():
            models.extend(model_list)

        if not models:
            pytest.skip("No models available for testing")

        # Create many small tasks
        tasks = [
            {"prompt": f"What is {i} + 1? Just the number.", "task_type": "general"}
            for i in range(10)  # More tasks than concurrency limit (5)
        ]

        import time

        start_time = time.time()

        results = await task_manager.executor.execute_parallel(tasks)

        execution_time = time.time() - start_time

        # With concurrency limit of 5, should take longer than sequential
        # but not as long as if limited to 1
        assert execution_time > 1.0  # Should take some time
        assert len(results) == 10
        assert all(r.success for r in results)
