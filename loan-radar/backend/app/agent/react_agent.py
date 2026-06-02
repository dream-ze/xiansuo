from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from app.agent.memory import ConversationBufferMemory, ConversationMessage
from app.agent.tools import (
    TOOL_DEFINITIONS,
    ToolCall,
    ToolResult,
    execute_tool,
    _format_tool_definitions,
)
from app.services.structured_llm import StructuredLLMClient

logger = logging.getLogger(__name__)

_REACT_SYSTEM_PROMPT = """你是助贷行业的智能助手，能够通过调用工具来帮助用户完成各种任务。

你可以使用以下工具：

{tool_definitions}

## 工作方式

你采用 ReAct (Reasoning + Acting) 模式工作：

1. **思考 (Thought)**：分析用户需求，决定下一步行动
2. **行动 (Action)**：调用合适的工具
3. **观察 (Observation)**：分析工具返回的结果
4. 重复以上步骤直到得出最终答案

## 输出格式

每次回复请严格按以下 JSON 格式输出：

```json
{{
  "thought": "你的思考过程",
  "action": "工具名称 或 finish",
  "action_input": {{}},
  "final_answer": "当 action 为 finish 时，给出最终答案"
}}
```

- 如果还需要继续调用工具，`action` 填写工具名称，`action_input` 填写工具参数
- 如果已经得出最终答案，`action` 填写 `"finish"`，`final_answer` 给出完整回答
- 每次只能调用一个工具
- 最多进行 {max_iterations} 轮思考-行动循环

## 注意事项

- 生成话术后，务必使用 compliance_check 检查合规性
- 如果合规检查发现风险，应修改话术并重新检查
- 优先使用 knowledge_search 获取参考素材，再生成话术
- 对不确定的文本，先用 lead_score 评分再决定后续操作
- 结合对话历史理解用户意图，保持上下文连贯
"""


class AgentState(TypedDict, total=False):
    thread_id: str
    user_id: int | None
    query: str
    model_config: Any
    api_key: str

    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str
    final_answer: str

    iteration: int
    max_iterations: int
    tool_history: list[dict[str, Any]]

    conversation_history: list[dict[str, Any]]
    new_user_message: bool

    _query_engine: Any
    _structured_llm: Any
    _memory: Any

    error: str | None


def _init_agent_state(
    *,
    query: str,
    model_config=None,
    api_key: str = "",
    user_id: int | None = None,
    max_iterations: int = 8,
    thread_id: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> AgentState:
    return AgentState(
        thread_id=thread_id or uuid.uuid4().hex[:16],
        user_id=user_id,
        query=query,
        model_config=model_config,
        api_key=api_key,
        thought="",
        action="",
        action_input={},
        observation="",
        final_answer="",
        iteration=0,
        max_iterations=max_iterations,
        tool_history=[],
        conversation_history=conversation_history or [],
        new_user_message=True,
        error=None,
    )


def _parse_llm_response(raw: str) -> dict[str, Any]:
    json_str = raw.strip()

    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", json_str, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1).strip()

    start = json_str.find("{")
    end = json_str.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = json_str[start : end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {
            "thought": raw[:500],
            "action": "finish",
            "action_input": {},
            "final_answer": raw,
        }


def _format_conversation_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return ""

    parts: list[str] = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"用户: {content}")
        elif role == "assistant":
            parts.append(f"助手: {content}")
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                name = tc.get("name", tc.get("action", "unknown"))
                args = tc.get("args", tc.get("action_input", {}))
                parts.append(f"  [调用工具: {name}({json.dumps(args, ensure_ascii=False)})]")
        elif role == "tool":
            tool_name = msg.get("metadata", {}).get("tool_name", "unknown")
            parts.append(f"  [工具结果({tool_name}): {content[:300]}]")

    return "\n".join(parts)


def agent_think_node(state: AgentState) -> dict[str, Any]:
    structured_llm: StructuredLLMClient | None = state.get("_structured_llm")
    query = state.get("query", "")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 8)
    tool_history = state.get("tool_history", [])
    conversation_history = state.get("conversation_history", [])

    if structured_llm is None:
        return {
            "thought": "LLM 不可用，直接结束",
            "action": "finish",
            "final_answer": "抱歉，AI 服务暂不可用，请稍后重试。",
            "iteration": iteration + 1,
        }

    system_prompt = _REACT_SYSTEM_PROMPT.format(
        tool_definitions=_format_tool_definitions(),
        max_iterations=max_iterations,
    )

    history_text = ""
    for entry in tool_history:
        history_text += f"\n思考: {entry.get('thought', '')}\n"
        history_text += f"行动: {entry.get('action', '')}\n"
        if entry.get("action_input"):
            history_text += f"行动参数: {json.dumps(entry.get('action_input', {}), ensure_ascii=False)}\n"
        history_text += f"观察: {entry.get('observation', '')}\n"

    user_prompt = ""

    conv_text = _format_conversation_history(conversation_history)
    if conv_text:
        user_prompt += f"=== 对话历史 ===\n{conv_text}\n=== 对话历史结束 ===\n\n"

    if iteration == 0:
        user_prompt += f"用户问题: {query}\n"
    else:
        user_prompt += f"继续处理用户问题: {query}\n"

    if history_text:
        user_prompt += f"\n本轮思考-行动历史:\n{history_text}\n"
    user_prompt += "\n请继续你的思考和行动（输出 JSON）："

    if iteration >= max_iterations - 1:
        user_prompt += "\n\n注意：你已接近最大迭代次数，请使用 finish 给出最终答案。"

    try:
        from app.services.ai_service import OpenAICompatibleTextClient

        raw_response = structured_llm._text_client._complete(
            model_config=state["model_config"],
            api_key=state["api_key"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        parsed = _parse_llm_response(raw_response)

        output = {
            "thought": parsed.get("thought", ""),
            "action": parsed.get("action", "finish"),
            "action_input": parsed.get("action_input", {}),
            "final_answer": parsed.get("final_answer", ""),
            "iteration": iteration + 1,
        }

        if output["action"] == "finish" and not output["final_answer"]:
            output["final_answer"] = parsed.get("thought", raw_response[:500])

        return output

    except Exception as exc:
        logger.error("Agent think failed: %s", exc)
        return {
            "thought": f"LLM 调用失败: {exc}",
            "action": "finish",
            "final_answer": "抱歉，处理过程中出现错误，请稍后重试。",
            "iteration": iteration + 1,
            "error": str(exc),
        }


def agent_act_node(state: AgentState) -> dict[str, Any]:
    action = state.get("action", "finish")
    action_input = state.get("action_input", {})
    tool_history = list(state.get("tool_history", []))

    if action == "finish":
        return {"observation": ""}

    tool_result: ToolResult = execute_tool(
        action,
        action_input,
        query_engine=state.get("_query_engine"),
        structured_llm_client=state.get("_structured_llm"),
        model_config=state.get("model_config"),
        api_key=state.get("api_key", ""),
        user_id=state.get("user_id"),
    )

    if tool_result.success and tool_result.output is not None:
        obs = json.dumps(tool_result.output, ensure_ascii=False, default=str)
    elif tool_result.error:
        obs = f"工具调用失败: {tool_result.error}"
    else:
        obs = "工具无返回结果"

    tool_history.append({
        "thought": state.get("thought", ""),
        "action": action,
        "action_input": action_input,
        "observation": obs[:2000],
        "success": tool_result.success,
    })

    return {
        "observation": obs[:2000],
        "tool_history": tool_history,
    }


def agent_save_memory_node(state: AgentState) -> dict[str, Any]:
    memory: ConversationBufferMemory | None = state.get("_memory")
    if memory is None:
        return {}

    if state.get("new_user_message", False):
        memory.add_user_message(state.get("query", ""))

    final_answer = state.get("final_answer", "")
    if final_answer:
        tool_calls = []
        for entry in state.get("tool_history", []):
            tool_calls.append({
                "action": entry.get("action"),
                "action_input": entry.get("action_input", {}),
                "success": entry.get("success", True),
            })

        memory.add_assistant_message(
            final_answer,
            tool_calls=tool_calls if tool_calls else None,
            iterations=state.get("iteration", 0),
        )

        for entry in state.get("tool_history", []):
            memory.add_tool_result(
                tool_name=entry.get("action", "unknown"),
                observation=entry.get("observation", "")[:500],
                success=entry.get("success", True),
            )

    return {"new_user_message": False}


def should_continue(state: AgentState) -> str:
    action = state.get("action", "finish")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 8)

    if action == "finish":
        return "save_memory"

    if iteration >= max_iterations:
        return "save_memory"

    return "act"


def build_react_agent(
    *,
    query_engine=None,
    structured_llm_client=None,
    max_iterations: int = 8,
) -> CompiledStateGraph:
    graph = StateGraph(AgentState)

    def wrapped_think(state: AgentState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        enriched["_query_engine"] = query_engine
        if "max_iterations" not in enriched or not enriched["max_iterations"]:
            enriched["max_iterations"] = max_iterations
        return agent_think_node(enriched)

    def wrapped_act(state: AgentState) -> dict:
        enriched = dict(state)
        enriched["_structured_llm"] = structured_llm_client
        enriched["_query_engine"] = query_engine
        return agent_act_node(enriched)

    def wrapped_save_memory(state: AgentState) -> dict:
        return agent_save_memory_node(state)

    graph.add_node("think", wrapped_think)
    graph.add_node("act", wrapped_act)
    graph.add_node("save_memory", wrapped_save_memory)

    graph.set_entry_point("think")

    graph.add_conditional_edges(
        "think",
        should_continue,
        {
            "act": "act",
            "save_memory": "save_memory",
        },
    )

    graph.add_edge("act", "think")
    graph.add_edge("save_memory", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
