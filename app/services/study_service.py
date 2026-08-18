import json
import re
import logging

from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class StudyService:

    def __init__(self):
        self.retriever = RetrievalService(top_k=6)
        self.llm = LLMService()

    # ============================================================
    # JSON HELPER
    # ============================================================

    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Extract JSON from an LLM response.

        Handles:
        - plain JSON
        - ```json ... ```
        - <think>...</think>
        - accidental text before/after JSON
        """

        if not text:
            return {}

        text = text.strip()

        # Remove complete reasoning blocks.
        text = re.sub(
            r"<think>[\s\S]*?</think>",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

        # If an unfinished <think> block exists, keep only the
        # content starting at the first JSON object.
        if "<think>" in text.lower() and "</think>" not in text.lower():
            first_brace = text.find("{")

            if first_brace != -1:
                text = text[first_brace:]

        # --------------------------------------------------------
        # 1. Direct JSON
        # --------------------------------------------------------

        try:
            parsed = json.loads(text)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

        # --------------------------------------------------------
        # 2. Markdown JSON block
        # --------------------------------------------------------

        match = re.search(
            r"```(?:json)?\s*([\s\S]*?)\s*```",
            text,
            flags=re.IGNORECASE
        )

        if match:

            try:
                parsed = json.loads(
                    match.group(1).strip()
                )

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                pass

        # --------------------------------------------------------
        # 3. Find outermost JSON object
        # --------------------------------------------------------

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:

            candidate = text[start:end + 1]

            try:
                parsed = json.loads(candidate)

                if isinstance(parsed, dict):
                    return parsed

            except json.JSONDecodeError:
                pass

        logger.error(
            "Failed to parse JSON from LLM output: %s",
            text[:1000]
        )

        return {}

    # ============================================================
    # QUIZ
    # ============================================================

    def generate_quiz(
        self,
        topic: str = "",
        count: int = 5,
        difficulty: str = "medium"
    ) -> dict:
        """
        Generates a grounded multiple-choice study quiz.
        """

        query = (
            topic.strip()
            if topic.strip()
            else "all core concepts and key terms"
        )

        retrieved_chunks = self.retriever.retrieve_context(
            query,
            top_k=8
        )

        if not retrieved_chunks:

            return {
                "status": "error",
                "message": (
                    "No study material found in your library "
                    "to generate a quiz. Please upload a PDF "
                    "or YouTube lecture first."
                )
            }

        context_parts = []

        for chunk in retrieved_chunks:

            metadata = chunk.get("metadata", {})

            source = metadata.get(
                "source",
                "Unknown"
            )

            page = metadata.get(
                "page",
                1
            )

            text = chunk.get(
                "text",
                ""
            ).strip()

            if text:

                context_parts.append(
                    f"[Source: {source}, Page {page}]\n{text}"
                )

        context_str = "\n\n".join(
            context_parts
        )

        prompt = f"""
You are an educational quiz generator.

Create exactly {count} multiple-choice questions using ONLY
the study material provided below.

Requested difficulty: {difficulty}

Return ONLY valid JSON.

Do not write explanations outside the JSON.
Do not use markdown code fences.
Do not use <think> tags.

Use EXACTLY this structure:

{{
  "title": "{topic or 'Study Material'} Quiz",
  "questions": [
    {{
      "id": 1,
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_answer": 0,
      "explanation": "Short explanation based on the study material.",
      "difficulty": "{difficulty}",
      "source": {{
        "document": "document.pdf",
        "page": 1
      }}
    }}
  ]
}}

STRICT RULES:

1. Create exactly {count} questions.
2. Every question MUST be answerable from the supplied study material.
3. Every question MUST have exactly four options.
4. correct_answer MUST be a 0-indexed integer:
   0, 1, 2, or 3.
5. Do not invent information.
6. Keep explanations concise.
7. Avoid duplicate questions.
8. If the material does not contain enough information
   for a question, choose another question.
9. Output JSON only.

STUDY MATERIAL:

{context_str}
"""

        try:

            if not self.llm.client:

                return {
                    "status": "error",
                    "message": (
                        "Groq API key is missing. "
                        "Please configure GROQ_API_KEY."
                    )
                }

            logger.info(
                "Generating quiz with model %s",
                self.llm.model
            )

            completion = (
                self.llm.client.chat.completions.create(
                    model=self.llm.model,

                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    temperature=0.2,

                    # JSON mode
                    response_format={
                        "type": "json_object"
                    },

                    max_completion_tokens=4096
                )
            )

            raw_text = (
                completion
                .choices[0]
                .message
                .content
                or ""
            )

            logger.info(
                "Quiz response received: %d characters",
                len(raw_text)
            )

            quiz_data = self._extract_json(
                raw_text
            )

            if not quiz_data:

                return {
                    "status": "error",
                    "message": (
                        "The AI returned an invalid quiz "
                        "response. Please try again."
                    )
                }

            questions = quiz_data.get(
                "questions"
            )

            if not isinstance(
                questions,
                list
            ):

                return {
                    "status": "error",
                    "message": (
                        "The AI returned quiz data without "
                        "a valid questions list."
                    )
                }

            valid_questions = []

            for index, question in enumerate(
                questions[:count],
                start=1
            ):

                if not isinstance(
                    question,
                    dict
                ):
                    continue

                question_text = str(
                    question.get(
                        "question",
                        ""
                    )
                ).strip()

                options = question.get(
                    "options",
                    []
                )

                correct_answer = question.get(
                    "correct_answer",
                    -1
                )

                explanation = str(
                    question.get(
                        "explanation",
                        ""
                    )
                ).strip()

                if not question_text:
                    continue

                if not isinstance(
                    options,
                    list
                ):
                    continue

                if len(options) != 4:
                    continue

                try:

                    correct_answer = int(
                        correct_answer
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    continue

                if correct_answer not in range(4):
                    continue

                options = [
                    str(option).strip()
                    for option in options
                ]

                if any(
                    not option
                    for option in options
                ):
                    continue

                valid_questions.append(
                    {
                        "id": index,
                        "question": question_text,
                        "options": options,
                        "correct_answer": correct_answer,
                        "explanation": explanation,
                        "difficulty": question.get(
                            "difficulty",
                            difficulty
                        ),
                        "source": question.get(
                            "source",
                            {}
                        )
                    }
                )

            if not valid_questions:

                logger.error(
                    "Quiz contained no valid questions."
                )

                return {
                    "status": "error",
                    "message": (
                        "The AI generated quiz questions "
                        "in an unsupported format. "
                        "Please try again."
                    )
                }

            return {
                "status": "success",
                "quiz": {
                    "title": quiz_data.get(
                        "title",
                        f"{topic or 'Study Material'} Quiz"
                    ),
                    "questions": valid_questions
                }
            }

        except Exception as e:

            logger.exception(
                "Quiz generation error"
            )

            return {
                "status": "error",
                "message": str(e)
            }

    # ============================================================
    # FLASHCARDS
    # ============================================================

    def generate_flashcards(
        self,
        topic: str = "",
        count: int = 10
    ) -> dict:
        """
        Generates grounded study flashcards.
        """

        query = (
            topic.strip()
            if topic.strip()
            else "key definitions and important formulas"
        )

        retrieved_chunks = self.retriever.retrieve_context(
            query,
            top_k=8
        )

        if not retrieved_chunks:

            return {
                "status": "error",
                "message": (
                    "No study material found in your "
                    "library to generate flashcards."
                )
            }

        context_str = "\n\n".join(
            [
                (
                    f"[Source: "
                    f"{c['metadata'].get('source', 'Unknown')}, "
                    f"Page "
                    f"{c['metadata'].get('page', 1)}]\n"
                    f"{c['text']}"
                )
                for c in retrieved_chunks
            ]
        )

        prompt = f"""
You are an educational study-card generator.

Generate exactly {count} concise flashcards using ONLY
the study material below.

Return ONLY valid JSON.

Use this structure:

{{
  "title": "{topic or 'Study Material'} Flashcards",
  "flashcards": [
    {{
      "id": 1,
      "front": "Question or concept",
      "back": "Clear grounded answer",
      "difficulty": "medium",
      "source": {{
        "document": "document.pdf",
        "page": 1
      }}
    }}
  ]
}}

Rules:

- Create exactly {count} cards.
- Use only the supplied study material.
- Avoid duplicate concepts.
- Do not invent information.
- Output JSON only.

STUDY MATERIAL:

{context_str}
"""

        try:

            if not self.llm.client:

                return {
                    "status": "error",
                    "message": (
                        "Groq API key is missing. "
                        "Please configure GROQ_API_KEY."
                    )
                }

            completion = (
                self.llm.client.chat.completions.create(
                    model=self.llm.model,

                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    temperature=0.2,

                    response_format={
                        "type": "json_object"
                    },

                    max_completion_tokens=4096
                )
            )

            raw_text = (
                completion
                .choices[0]
                .message
                .content
                or ""
            )

            card_data = self._extract_json(
                raw_text
            )

            cards = card_data.get(
                "flashcards"
            )

            if not isinstance(
                cards,
                list
            ):

                return {
                    "status": "error",
                    "message": (
                        "Generated flashcard data did "
                        "not match the required format."
                    )
                }

            return {
                "status": "success",
                "flashcards": cards
            }

        except Exception as e:

            logger.exception(
                "Flashcards generation error"
            )

            return {
                "status": "error",
                "message": str(e)
            }

    # ============================================================
    # SUMMARY
    # ============================================================

    def summarize_material(
        self,
        topic: str = ""
    ) -> dict:
        """
        Generates a structured study summary.
        """

        query = (
            topic.strip()
            if topic.strip()
            else (
                "overall main principles, formulas, "
                "definitions, and takeaways"
            )
        )

        retrieved_chunks = self.retriever.retrieve_context(
            query,
            top_k=8
        )

        if not retrieved_chunks:

            return {
                "status": "error",
                "message": (
                    "No study material found in your "
                    "library to summarize."
                )
            }

        context_str = "\n\n".join(
            [
                (
                    f"[Source: "
                    f"{c['metadata'].get('source', 'Unknown')}, "
                    f"Page "
                    f"{c['metadata'].get('page', 1)}]\n"
                    f"{c['text']}"
                )
                for c in retrieved_chunks
            ]
        )

        prompt = f"""
You are an expert academic tutor.

Create a structured study summary strictly based
on the study material below.

Return ONLY valid JSON.

Use this structure:

{{
  "title": "Study Summary: {topic or 'Core Concepts'}",
  "key_concepts": [
    "Concept 1",
    "Concept 2"
  ],
  "definitions": [
    {{
      "term": "Term",
      "definition": "Grounded definition"
    }}
  ],
  "formulas_or_laws": [
    "Formula or law"
  ],
  "major_takeaways": [
    "Important takeaway"
  ]
}}

Rules:

- Use ONLY the supplied material.
- Do not invent information.
- Keep the summary useful for studying.
- Output JSON only.

STUDY MATERIAL:

{context_str}
"""

        try:

            if not self.llm.client:

                return {
                    "status": "error",
                    "message": (
                        "Groq API key is missing. "
                        "Please configure GROQ_API_KEY."
                    )
                }

            completion = (
                self.llm.client.chat.completions.create(
                    model=self.llm.model,

                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],

                    temperature=0.2,

                    response_format={
                        "type": "json_object"
                    },

                    max_completion_tokens=4096
                )
            )

            raw_text = (
                completion
                .choices[0]
                .message
                .content
                or ""
            )

            summary_data = self._extract_json(
                raw_text
            )

            if not summary_data:

                return {
                    "status": "error",
                    "message": (
                        "The AI returned an invalid "
                        "summary response."
                    )
                }

            if "key_concepts" not in summary_data:

                return {
                    "status": "error",
                    "message": (
                        "Generated summary did not match "
                        "the required format."
                    )
                }

            return {
                "status": "success",
                "summary": summary_data
            }

        except Exception as e:

            logger.exception(
                "Summary generation error"
            )

            return {
                "status": "error",
                "message": str(e)
            }