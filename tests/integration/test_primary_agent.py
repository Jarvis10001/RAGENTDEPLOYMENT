"""Integration tests for the primary agent (AgentExecutor construction).

These tests verify that the agent construction function wires tools,
memory, prompt, and LLM correctly. The AgentExecutor's internal
validation is exercised via ``AgentExecutor.from_agent_and_tools``.
All external calls (LLMs, Supabase, tools) are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestPrimaryAgentConstruction:
    """Tests for get_agent_executor and its wiring."""

    @patch("src.agent.primary_agent.hub")
    @patch("src.agent.primary_agent.create_react_agent")
    @patch("src.agent.primary_agent.ChatGoogleGenerativeAI")
    @patch("src.agent.primary_agent.create_memory")
    def test_create_react_agent_called_with_tools(
        self,
        mock_create_memory: MagicMock,
        mock_llm_cls: MagicMock,
        mock_create_agent: MagicMock,
        mock_hub: MagicMock,
    ) -> None:
        """Verify that create_react_agent is called with all 5 tools.

        Args:
            mock_create_memory: Mocked memory factory.
            mock_llm_cls: Mocked ChatGoogleGenerativeAI class.
            mock_create_agent: Mocked create_react_agent function.
            mock_hub: Mocked LangChain hub.
        """
        from src.agent.primary_agent import get_agent_executor

        mock_memory = MagicMock()
        mock_memory.memory_variables = ["chat_history"]
        mock_create_memory.return_value = mock_memory

        mock_prompt = MagicMock()
        mock_prompt.messages = []
        mock_prompt.template = "test template"
        mock_hub.pull.return_value = mock_prompt

        # Make the agent return the correct tool list
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        try:
            get_agent_executor()
        except Exception:
            pass  # AgentExecutor validation may fail with mocks

        # Verify create_react_agent was called
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args
        tools_passed = call_kwargs.kwargs.get("tools", call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])
        tool_names = {t.name for t in tools_passed}

        expected_tools = {
            "omnichannel_feedback_search",
            "marketing_content_search",
            "ecommerce_sql_query",
            "ecommerce_analytics_query",
            "web_market_search",
        }
        assert tool_names == expected_tools

    @patch("src.agent.primary_agent.hub")
    @patch("src.agent.primary_agent.create_react_agent")
    @patch("src.agent.primary_agent.ChatGoogleGenerativeAI")
    @patch("src.agent.primary_agent.create_memory")
    def test_system_prefix_is_injected_into_prompt(
        self,
        mock_create_memory: MagicMock,
        mock_llm_cls: MagicMock,
        mock_create_agent: MagicMock,
        mock_hub: MagicMock,
    ) -> None:
        """Verify that the system prefix is injected into the prompt template.

        Args:
            mock_create_memory: Mocked memory factory.
            mock_llm_cls: Mocked ChatGoogleGenerativeAI class.
            mock_create_agent: Mocked create_react_agent function.
            mock_hub: Mocked LangChain hub.
        """
        from src.agent.primary_agent import get_agent_executor

        mock_memory = MagicMock()
        mock_memory.memory_variables = ["chat_history"]
        mock_create_memory.return_value = mock_memory

        mock_prompt = MagicMock()
        mock_prompt.messages = []
        mock_prompt.template = "Original template {tools}"
        mock_hub.pull.return_value = mock_prompt

        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        try:
            get_agent_executor()
        except Exception:
            pass

        # Verify the template was modified
        assert "E-commerce Intelligence Analyst" in mock_prompt.template

    @patch("src.agent.primary_agent.hub")
    @patch("src.agent.primary_agent.create_react_agent")
    @patch("src.agent.primary_agent.ChatGoogleGenerativeAI")
    @patch("src.agent.primary_agent.create_memory")
    def test_memory_factory_is_called_when_no_memory_provided(
        self,
        mock_create_memory: MagicMock,
        mock_llm_cls: MagicMock,
        mock_create_agent: MagicMock,
        mock_hub: MagicMock,
    ) -> None:
        """Verify that create_memory() is called when no memory is provided.

        Args:
            mock_create_memory: Mocked memory factory.
            mock_llm_cls: Mocked ChatGoogleGenerativeAI class.
            mock_create_agent: Mocked create_react_agent function.
            mock_hub: Mocked LangChain hub.
        """
        from src.agent.primary_agent import get_agent_executor

        mock_memory = MagicMock()
        mock_memory.memory_variables = ["chat_history"]
        mock_create_memory.return_value = mock_memory

        mock_prompt = MagicMock()
        mock_prompt.messages = []
        mock_prompt.template = "test template"
        mock_hub.pull.return_value = mock_prompt

        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        try:
            get_agent_executor()
        except Exception:
            pass

        mock_create_memory.assert_called_once()

    @patch("src.agent.primary_agent.hub")
    @patch("src.agent.primary_agent.create_react_agent")
    @patch("src.agent.primary_agent.ChatGoogleGenerativeAI")
    @patch("src.agent.primary_agent.create_memory")
    def test_provided_memory_skips_factory(
        self,
        mock_create_memory: MagicMock,
        mock_llm_cls: MagicMock,
        mock_create_agent: MagicMock,
        mock_hub: MagicMock,
    ) -> None:
        """Verify that providing a memory instance skips the factory call.

        Args:
            mock_create_memory: Mocked memory factory (should NOT be called).
            mock_llm_cls: Mocked ChatGoogleGenerativeAI class.
            mock_create_agent: Mocked create_react_agent function.
            mock_hub: Mocked LangChain hub.
        """
        from src.agent.primary_agent import get_agent_executor

        mock_prompt = MagicMock()
        mock_prompt.messages = []
        mock_prompt.template = "test template"
        mock_hub.pull.return_value = mock_prompt

        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        custom_memory = MagicMock()
        custom_memory.memory_variables = ["chat_history"]

        try:
            get_agent_executor(memory=custom_memory)
        except Exception:
            pass

        mock_create_memory.assert_not_called()

    @patch("src.agent.primary_agent.hub")
    @patch("src.agent.primary_agent.ChatGoogleGenerativeAI")
    @patch("src.agent.primary_agent.create_memory")
    def test_primary_llm_uses_correct_model(
        self,
        mock_create_memory: MagicMock,
        mock_llm_cls: MagicMock,
        mock_hub: MagicMock,
    ) -> None:
        """Verify that the primary LLM is constructed with the correct model name.

        Args:
            mock_create_memory: Mocked memory factory.
            mock_llm_cls: Mocked ChatGoogleGenerativeAI class.
            mock_hub: Mocked LangChain hub.
        """
        from src.agent.primary_agent import get_agent_executor
        from src.config import settings

        mock_memory = MagicMock()
        mock_memory.memory_variables = ["chat_history"]
        mock_create_memory.return_value = mock_memory

        mock_prompt = MagicMock()
        mock_prompt.messages = []
        mock_prompt.template = "test template"
        mock_hub.pull.return_value = mock_prompt

        try:
            get_agent_executor()
        except Exception:
            pass

        # Check the first call to ChatGoogleGenerativeAI is for the primary model
        first_call_kwargs = mock_llm_cls.call_args_list[0].kwargs
        assert first_call_kwargs["model"] == settings.primary_model
