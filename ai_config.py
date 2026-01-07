"""
AI Configuration for cribl-hc development.

This module provides configuration and utilities for connecting to Harbor/Ollama
services for AI-assisted development tasks.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class AIConfig:
    """Configuration for AI services connection."""

    def __init__(self):
        # Harbor/Ollama connection settings
        self.overlord_host = os.getenv("HARBOR_HOST", "overlord")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", "33821"))
        self.litellm_port = os.getenv("LITELLM_PORT")  # Optional

        # Performance settings
        self.max_concurrency = int(os.getenv("AI_MAX_CONCURRENCY", "5"))
        self.timeout = int(os.getenv("AI_TIMEOUT", "300"))

        # Model preferences
        self.preferred_models = {
            "code": os.getenv("AI_CODE_MODEL", "ollama/qwen2.5-coder"),
            "creative": os.getenv("AI_CREATIVE_MODEL", "ollama/llama3"),
            "analysis": os.getenv("AI_ANALYSIS_MODEL", "ollama/mistral"),
            "general": os.getenv("AI_GENERAL_MODEL", "ollama/llama3"),
        }

    @property
    def ollama_url(self) -> str:
        """Get the Ollama API URL."""
        return f"http://{self.overlord_host}:{self.ollama_port}"

    @property
    def litellm_url(self) -> Optional[str]:
        """Get the LiteLLM API URL if configured."""
        if self.litellm_port:
            return f"http://{self.overlord_host}:{self.litellm_port}"
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "overlord_host": self.overlord_host,
            "ollama_port": self.ollama_port,
            "litellm_port": self.litellm_port,
            "ollama_url": self.ollama_url,
            "litellm_url": self.litellm_url,
            "max_concurrency": self.max_concurrency,
            "timeout": self.timeout,
            "preferred_models": self.preferred_models,
        }

    def print_config(self):
        """Print current configuration."""
        print("🤖 AI Configuration")
        print("=" * 30)
        print(f"Host: {self.overlord_host}")
        print(f"Ollama URL: {self.ollama_url}")
        if self.litellm_url:
            print(f"LiteLLM URL: {self.litellm_url}")
        print(f"Max Concurrency: {self.max_concurrency}")
        print(f"Timeout: {self.timeout}s")
        print("\n🎯 Preferred Models:")
        for task_type, model in self.preferred_models.items():
            print(f"  {task_type}: {model}")


# Global configuration instance
ai_config = AIConfig()


def get_ai_config() -> AIConfig:
    """Get the global AI configuration."""
    return ai_config


def test_connection():
    """Test connection to Harbor/Ollama services."""
    import asyncio
    from cribl_hc.core.ai_connector import ParallelTaskManager

    async def test():
        print("🔍 Testing Harbor/Ollama Connection...")
        print(f"📍 Connecting to: {ai_config.ollama_url}")

        try:
            async with ParallelTaskManager(
                overlord_host=ai_config.overlord_host, ollama_port=ai_config.ollama_port
            ) as manager:
                # Check available models
                total_models = sum(len(models) for models in manager.executor.models_cache.values())
                print(f"✅ Connection successful! Found {total_models} models")

                for connector_name, models in manager.executor.models_cache.items():
                    print(f"  📦 {connector_name}: {len(models)} models")
                    for model in models:
                        print(
                            f"    • {model.name} ({model.context_length} tokens, {model.provider})"
                        )

                # Test a simple task
                print("\n🧪 Testing model response...")
                result = await manager.executor.execute_task(
                    "Say 'Harbor connection successful' in exactly 3 words", task_type="general"
                )

                if result.success:
                    print(f"✅ AI Response: {result.response}")
                    print(f"⚡ Processing time: {result.processing_time:.2f}s")
                else:
                    print(f"❌ Task failed: {result.error}")

                return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    return asyncio.run(test())


if __name__ == "__main__":
    # Print configuration
    ai_config.print_config()

    # Test connection if run directly
    print("\n" + "=" * 50)
    success = test_connection()
    if success:
        print("\n🎉 Harbor/Ollama setup is ready for AI-assisted development!")
    else:
        print("\n⚠️  Connection test failed. Check Harbor services on overlord.")
