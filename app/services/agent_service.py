"""
LangChain tool-calling agent for Koin's finance advisor chat.

The agent has access to tools that query the user's real financial data, so it
can answer questions like "How much did I spend on food this month?" or
"Am I on track for my savings goals?" with actual numbers instead of guesses.

Uses the LangChain 1.x / LangGraph create_agent API.
Input: {"messages": [*history, HumanMessage(current_message)]}
Output: last AIMessage in result["messages"]
"""

from collections.abc import AsyncIterator
from time import perf_counter

from fastapi import HTTPException, status
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessageRole
from app.services.finance_service import (
    agent_get_budget_status,
    agent_get_expense_summary,
    agent_get_income_summary,
    agent_get_savings_goals,
    agent_get_spending_trend,
)
from app.services.llm_service import (
    LLMResponse,
    LLMStreamChunk,
    _resolve_and_validate,
    get_llm_for_agent,
)

# ---------------------------------------------------------------------------
# Response types (re-export for callers)
# ---------------------------------------------------------------------------

AgentResponse = LLMResponse


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


def _make_finance_tools(db: Session, user_id: str) -> list[StructuredTool]:
    """Create LangChain tools bound to the current user's DB session."""

    def get_expenses(period: str = "current_month") -> str:
        """
        Get the user's expense summary for a given period.
        Valid period values: current_month, last_month, current_week, last_30_days, last_90_days, this_year.
        """
        return agent_get_expense_summary(db, user_id, period)

    def get_income(period: str = "current_month") -> str:
        """
        Get the user's income summary for a given period.
        Valid period values: current_month, last_month, current_week, last_30_days, last_90_days, this_year.
        """
        return agent_get_income_summary(db, user_id, period)

    def get_budget_status() -> str:
        """
        Get the user's current budget status across all categories, showing how much
        has been spent vs. the limit for the current period.
        """
        return agent_get_budget_status(db, user_id)

    def get_savings_goals() -> str:
        """
        Get all of the user's active savings goals with current progress.
        """
        return agent_get_savings_goals(db, user_id)

    def get_spending_trend(months: int = 3) -> str:
        """
        Get the user's spending trend over the last N months (default 3).
        Shows income, expenses, and net for each month.
        """
        return agent_get_spending_trend(db, user_id, months=months)

    return [
        StructuredTool.from_function(func=get_expenses, name="get_expenses"),
        StructuredTool.from_function(func=get_income, name="get_income"),
        StructuredTool.from_function(func=get_budget_status, name="get_budget_status"),
        StructuredTool.from_function(func=get_savings_goals, name="get_savings_goals"),
        StructuredTool.from_function(
            func=get_spending_trend, name="get_spending_trend"
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_finance_agent(
    db: Session,
    user_id: str,
    message: str,
    history: list,
    model: str | None = None,
) -> LLMResponse:
    """
    Invoke the finance agent and return the full response.
    History is a list of ChatMessage or ChatMemoryMessage objects (excluding
    the current message — it is appended here as the final HumanMessage).
    """
    model_str = _resolve_and_validate(model)
    llm = get_llm_for_agent(model)
    tools = _make_finance_tools(db, user_id)

    agent = create_agent(llm, tools, system_prompt=settings.chat_system_prompt)

    messages = [*_build_langchain_history(history), HumanMessage(content=message)]

    started_at = perf_counter()
    try:
        result = await agent.ainvoke({"messages": messages})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed",
        ) from exc

    latency_ms = int((perf_counter() - started_at) * 1000)

    # The last message in the result is the final AI response
    ai_messages = [m for m in result.get("messages", []) if isinstance(m, AIMessage)]
    content = ai_messages[-1].content if ai_messages else ""
    if isinstance(content, list):
        # Some providers return a list of content blocks
        content = "\n".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ).strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service returned an empty response",
        )

    return LLMResponse(
        content=content,
        model=model_str,
        latency_ms=latency_ms,
    )


async def stream_finance_agent(
    db: Session,
    user_id: str,
    message: str,
    history: list,
    model: str | None = None,
) -> AsyncIterator[LLMStreamChunk]:
    """
    Stream the finance agent response.
    Yields content chunks while the agent thinks, then a final done=True chunk.
    Tool calls happen silently (not streamed to the client).
    """
    model_str = _resolve_and_validate(model)
    llm = get_llm_for_agent(model)
    tools = _make_finance_tools(db, user_id)

    agent = create_agent(llm, tools, system_prompt=settings.chat_system_prompt)

    messages = [*_build_langchain_history(history), HumanMessage(content=message)]

    started_at = perf_counter()
    collected: list[str] = []

    try:
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            kind = event.get("event")
            # Stream only the final LLM text output, not tool-call tokens
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk is None:
                    continue
                content = chunk.content
                if isinstance(content, list):
                    # Gemini-style: list of dicts with "text" key
                    text = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    )
                elif isinstance(content, str):
                    text = content
                else:
                    text = ""
                # Filter out tool-call chunks (they have empty string content)
                if text:
                    collected.append(text)
                    yield LLMStreamChunk(content=text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed",
        ) from exc

    full_content = "".join(collected)
    if not full_content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service returned an empty response",
        )

    latency_ms = int((perf_counter() - started_at) * 1000)
    yield LLMStreamChunk(
        content=full_content,
        done=True,
        model=model_str,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_langchain_history(history: list) -> list:
    """Convert ChatMessage / ChatMemoryMessage objects to LangChain message objects."""
    messages = []
    for msg in history[-settings.chat_context_message_limit :]:
        role = msg.role if isinstance(msg.role, str) else msg.role.value
        if role == ChatMessageRole.USER:
            messages.append(HumanMessage(content=msg.content))
        elif role == ChatMessageRole.ASSISTANT:
            messages.append(AIMessage(content=msg.content))
    return messages
