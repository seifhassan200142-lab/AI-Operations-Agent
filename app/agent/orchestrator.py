from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.agent.llm import LLMClient, LLMConfigurationError
from app.agent.memory import ConversationMemory
from app.agent.policy import ApprovalPolicy
from app.agent.prompts import AGENT_SYSTEM_PROMPT, build_agent_prompt
from app.db.models import ActionLog, PendingAction
from app.schemas.models import ChatResponse, ToolCallRecord
from app.tools.registry import ToolRegistry, create_default_registry


class AgentOrchestrator:
    """Understandable tool-using agent loop.

    The LLM decides the next action in JSON. The backend executes tools and enforces
    approval policies. The UI receives only safe reasoning summaries, not hidden chain-of-thought.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        memory: ConversationMemory | None = None,
        llm_client: LLMClient | None = None,
        policy: ApprovalPolicy | None = None,
        max_steps: int = 6,
    ) -> None:
        self.registry = registry or create_default_registry()
        self.memory = memory or ConversationMemory()
        self.llm_client = llm_client or LLMClient()
        self.policy = policy or ApprovalPolicy()
        self.max_steps = max_steps

    def run(self, user_request: str, session_id: str, db: Session) -> ChatResponse:
        self.memory.add(session_id, "user", user_request)

        if not self.llm_client.is_configured():
            answer = self.llm_client.setup_error()
            self.memory.add(session_id, "assistant", answer)
            return ChatResponse(
                answer=answer,
                reasoning_summary="The agent could not start because no LLM provider is configured.",
                tool_calls=[],
                pending_action_ids=[],
            )

        tool_calls: list[ToolCallRecord] = []
        pending_action_ids: list[str] = []
        observations: list[dict[str, Any]] = []
        reasoning_summaries: list[str] = []

        for _ in range(self.max_steps):
            next_step = self._ask_llm(user_request, session_id, observations)
            reasoning = str(next_step.get("reasoning_summary", "The agent selected the next step."))
            reasoning_summaries.append(reasoning)

            action = next_step.get("action")
            if action == "finish":
                final_answer = str(next_step.get("final_answer", "Done."))
                self.memory.add(session_id, "assistant", final_answer)
                return ChatResponse(
                    answer=final_answer,
                    reasoning_summary=self._combine_reasoning(reasoning_summaries),
                    tool_calls=tool_calls,
                    pending_action_ids=pending_action_ids,
                )

            if action != "tool":
                final_answer = "The agent could not understand the next action returned by the LLM."
                self.memory.add(session_id, "assistant", final_answer)
                return ChatResponse(
                    answer=final_answer,
                    reasoning_summary="The LLM returned an invalid action schema.",
                    tool_calls=tool_calls,
                    pending_action_ids=pending_action_ids,
                )

            tool_name = str(next_step.get("tool_name", ""))
            arguments = next_step.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}

            try:
                tool = self.registry.get(tool_name)
                result = tool.execute(arguments, db)
            except Exception as exc:  # noqa: BLE001 - convert internal tool errors into safe response
                result_data = {"error": str(exc)}
                observations.append({"tool": tool_name, "success": False, "message": str(exc), "data": result_data})
                tool_calls.append(
                    ToolCallRecord(
                        tool_name=tool_name,
                        arguments=arguments,
                        result_summary=f"Tool error: {exc}",
                    )
                )
                continue

            action_id: str | None = None
            if self.policy.should_require_approval(result):
                action_id = self._create_pending_action(result, db)
                pending_action_ids.append(action_id)
                self._log_action(db, result.action_type or "approval_required", action_id, "pending", result.message)

            observation = {
                "tool": tool_name,
                "success": result.success,
                "message": result.message,
                "data": result.data,
                "requires_approval": result.requires_approval,
                "action_id": action_id,
            }
            observations.append(observation)
            tool_calls.append(
                ToolCallRecord(
                    tool_name=tool_name,
                    arguments=arguments,
                    result_summary=result.message,
                    requires_approval=result.requires_approval,
                    action_id=action_id,
                )
            )

            if action_id:
                answer = (
                    "A sensitive action is waiting for human approval before it can continue. "
                    f"Pending action ID: {action_id}."
                )
                self.memory.add(session_id, "assistant", answer)
                return ChatResponse(
                    answer=answer,
                    reasoning_summary=self._combine_reasoning(reasoning_summaries),
                    tool_calls=tool_calls,
                    pending_action_ids=pending_action_ids,
                )

        answer = "The agent reached the maximum number of steps before finishing. Try a more specific request."
        self.memory.add(session_id, "assistant", answer)
        return ChatResponse(
            answer=answer,
            reasoning_summary=self._combine_reasoning(reasoning_summaries),
            tool_calls=tool_calls,
            pending_action_ids=pending_action_ids,
        )

    def _ask_llm(self, user_request: str, session_id: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_agent_prompt(
                    user_request=user_request,
                    memory_text=self.memory.as_text(session_id),
                    tools_json=json.dumps(self.registry.describe(), indent=2),
                    observations_json=json.dumps(observations, indent=2),
                ),
            },
        ]
        try:
            raw = self.llm_client.chat(messages)
        except LLMConfigurationError:
            raise
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("LLM JSON response must be an object.")
        return data

    def _create_pending_action(self, result: Any, db: Session) -> str:
        action_id = str(uuid.uuid4())
        reason = result.approval_reason or self.policy.reason_for(result.action_type)
        pending = PendingAction(
            id=action_id,
            action_type=result.action_type or "unknown_sensitive_action",
            payload_json=json.dumps(result.action_payload or result.data),
            reason=reason,
            status="pending",
        )
        db.add(pending)
        db.commit()
        return action_id

    def _log_action(self, db: Session, action_type: str, action_id: str | None, status: str, message: str) -> None:
        db.add(ActionLog(action_type=action_type, action_id=action_id, status=status, message=message))
        db.commit()

    def _combine_reasoning(self, summaries: list[str]) -> str:
        cleaned = [summary.strip() for summary in summaries if summary.strip()]
        if not cleaned:
            return "The agent completed the request using the available workflow."
        return " ".join(cleaned[:4])
