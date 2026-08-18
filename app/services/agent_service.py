import json
import re
import logging
from app.services.llm_service import LLMService
from app.services.study_service import StudyService
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# Whitelisted tools ONLY
ALLOWED_TOOLS = {
    "answer_question",
    "search_documents",
    "search_youtube",
    "generate_quiz",
    "generate_flashcards",
    "summarize_material"
}

class AgentService:
    def __init__(self):
        self.llm = LLMService()
        self.study_service = StudyService()
        self.retriever = RetrievalService(top_k=5)

    def process_request(self, user_query: str, history: list[dict] = None) -> dict:
        """
        Agent router entry point.
        Analyzes user prompt, resolves context from conversation history,
        selects approved tool from whitelist, validates parameters, and executes.
        """
        if not user_query.strip():
            return {"status": "error", "message": "Empty query"}

        # 1. Decide Tool & Arguments using LLM Intent Router
        decision = self._route_intent(user_query, history)
        selected_tool = decision.get("tool", "answer_question")
        arguments = decision.get("arguments", {})

        logger.info(f"Agent Router selected tool '{selected_tool}' with arguments {arguments}")

        # 2. Tool Whitelist Validation
        if selected_tool not in ALLOWED_TOOLS:
            logger.warning(f"Rejected unapproved tool call '{selected_tool}'. Falling back to 'answer_question'.")
            selected_tool = "answer_question"

        # 3. Execute Selected Tool
        try:
            if selected_tool == "generate_quiz":
                topic = arguments.get("topic", "") or user_query
                count = int(arguments.get("count", 5))
                result = self.study_service.generate_quiz(topic=topic, count=count)
                
                if result.get("status") == "success":
                    quiz_obj = result.get("quiz", {})
                    q_count = len(quiz_obj.get("questions", []))
                    reply_text = f"🎯 **Generated Quiz: {quiz_obj.get('title', 'Study Quiz')}** ({q_count} questions)\n\nSwitch to the **Quiz** tab to start your interactive assessment!"
                    return {
                        "status": "success",
                        "reply": reply_text,
                        "tool_used": "generate_quiz",
                        "quiz_data": quiz_obj,
                        "sources": []
                    }
                else:
                    return {"status": "error", "reply": result.get("message", "Quiz generation failed.")}

            elif selected_tool == "generate_flashcards":
                topic = arguments.get("topic", "") or user_query
                count = int(arguments.get("count", 10))
                result = self.study_service.generate_flashcards(topic=topic, count=count)
                
                if result.get("status") == "success":
                    cards = result.get("flashcards", [])
                    reply_text = f"🎴 **Generated {len(cards)} Flashcards** for topic '{topic or 'Material'}'.\n\nSwitch to the **Flashcards** tab to review your cards!"
                    return {
                        "status": "success",
                        "reply": reply_text,
                        "tool_used": "generate_flashcards",
                        "flashcards_data": cards,
                        "sources": []
                    }
                else:
                    return {"status": "error", "reply": result.get("message", "Flashcard generation failed.")}

            elif selected_tool == "summarize_material":
                topic = arguments.get("topic", "") or user_query
                result = self.study_service.summarize_material(topic=topic)
                
                if result.get("status") == "success":
                    summary = result.get("summary", {})
                    reply_text = f"📖 **Summary: {summary.get('title', 'Study Summary')}**\n\nSwitch to the **Summary** tab to view key concepts, definitions, and takeaways!"
                    return {
                        "status": "success",
                        "reply": reply_text,
                        "tool_used": "summarize_material",
                        "summary_data": summary,
                        "sources": []
                    }
                else:
                    return {"status": "error", "reply": result.get("message", "Summary generation failed.")}

            elif selected_tool in ("search_documents", "search_youtube"):
                query_str = arguments.get("query", "") or user_query
                chunks = self.retriever.retrieve_context(query_str, top_k=4)
                llm_res = self.llm.generate_grounded_response(user_query, chunks, history)
                return {
                    "status": "success",
                    "reply": llm_res["reply"],
                    "sources": llm_res["sources"],
                    "tool_used": selected_tool
                }

            else: # Default: answer_question
                chunks = self.retriever.retrieve_context(user_query, top_k=4)
                llm_res = self.llm.generate_grounded_response(user_query, chunks, history)
                return {
                    "status": "success",
                    "reply": llm_res["reply"],
                    "sources": llm_res["sources"],
                    "tool_used": "answer_question"
                }

        except Exception as e:
            logger.error(f"Error executing agent tool '{selected_tool}': {e}")
            # Fallback to standard grounded Q&A
            chunks = self.retriever.retrieve_context(user_query, top_k=4)
            llm_res = self.llm.generate_grounded_response(user_query, chunks, history)
            return {
                "status": "success",
                "reply": llm_res["reply"],
                "sources": llm_res["sources"],
                "tool_used": "answer_question_fallback"
            }

    def _route_intent(self, user_query: str, history: list[dict] = None) -> dict:
        """Uses LLM to select tool and extract arguments from query & history."""
        if not self.llm.client:
            return {"tool": "answer_question", "arguments": {"topic": user_query}}

        history_summary = ""
        if history:
            turns = [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in history[-4:]]
            history_summary = "\n".join(turns)

        router_prompt = f"""You are an Intent Router for a Study Companion system. Analyze the user request and select the single best tool from the approved list below.

APPROVED TOOLS:
1. `answer_question`: For general questions, explanations, asking for details or clarifications.
2. `generate_quiz`: When user asks to create a quiz, test, MCQs, or questions (e.g. "make 10 MCQs", "test me on chapter 2").
3. `generate_flashcards`: When user asks to create flashcards, study cards, or review cards (e.g. "make flashcards for this topic").
4. `summarize_material`: When user asks for a summary, overview, key concepts, or definitions (e.g. "summarize module 3").
5. `search_documents`: When user explicitly asks to search text documents.
6. `search_youtube`: When user explicitly asks to search YouTube lectures.

STRICT JSON OUTPUT REQUIREMENT:
Respond ONLY with a valid JSON object matching this schema:
{{
  "tool": "tool_name_here",
  "arguments": {{
    "topic": "extracted topic or subject",
    "count": 5
  }}
}}

RECENT CONVERSATION HISTORY:
{history_summary or 'None'}

USER REQUEST:
"{user_query}"
"""

        try:
            completion = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[{"role": "user", "content": router_prompt}],
                temperature=0.0,
                max_tokens=256
            )
            raw_text = completion.choices[0].message.content.strip()
            parsed = self.study_service._extract_json(raw_text)
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        except Exception as e:
            logger.warning(f"Intent routing LLM call failed: {e}")

        return {"tool": "answer_question", "arguments": {"topic": user_query}}
