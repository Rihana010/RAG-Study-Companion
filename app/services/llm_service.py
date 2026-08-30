
import logging
import re
from groq import Groq
from config import Config

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.model = Config.GROQ_MODEL
        self.client = None
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info(f"Groq client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")

    def generate_grounded_response(
        self, 
        user_query: str, 
        retrieved_chunks: list[dict], 
        conversation_history: list[dict] = None
    ) -> dict:
        """
        Generates a grounded RAG response using Groq LLM API.
        
        Returns:
        {
            "reply": "...",
            "sources": [{"source": "physics.pdf", "page": 4}, ...],
            "grounded": True/False
        }
        """
        if not self.client:
            return {
                "reply": "⚠️ Groq API key is missing or invalid. Please configure `GROQ_API_KEY` in your `.env` file to enable AI answers.",
                "sources": [],
                "grounded": False
            }

        # Build context string and source list
        context_blocks = []
        sources = []
        seen_sources = set()

        for idx, chunk in enumerate(retrieved_chunks, 1):
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            src = meta.get("source", "Unknown")
            page = meta.get("page", 1)
            video_url = meta.get("video_url", None)
            timestamp = meta.get("timestamp_start", None)

            source_label = f"{src} (Page {page})"
            if video_url:
                source_label = f"YouTube: {meta.get('video_title', src)} (Timestamp {timestamp})"

            context_blocks.append(f"[Source {idx}: {source_label}]\n{text}")

            source_key = f"{src}_p{page}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "source": src,
                    "page": page,
                    "video_url": video_url,
                    "timestamp": timestamp
                })

        context_str = "\n\n".join(context_blocks) if context_blocks else "NO STUDY MATERIAL AVAILABLE."

        system_prompt = (
            "You are an expert AI Study Assistant. Your task is to answer the student's question based strictly on the provided study materials below.\n\n"
            "STRICT RULES:\n"
            "1. Base your answer ONLY on the provided study context. Do NOT fabricate or hallucinate facts.\n"
            "2. If the study context does not contain enough information to answer the question, state clearly: 'I could not find information about this in your uploaded study materials.'\n"
            "3. Cite your sources in the text using format [Source X] or mentioning the document name and page number.\n"
            "4. Be clear, educational, concise, and structured.\n\n"
            f"--- STUDY CONTEXT ---\n{context_str}\n--------------------"
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Append recent conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:  # keep last 6 turns
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Append current user query
        messages.append({"role": "user", "content": user_query})

        try:
            logger.info(f"Sending request to Groq model {self.model}...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2, # Low temperature for accurate grounded answers
                max_tokens=2048
            )
            
            reply_text = completion.choices[0].message.content.strip()
            # Strip internal reasoning blocks if model produces <think>...</think>
            reply_text = re.sub(r'<think>[\s\S]*?</think>', '', reply_text).strip()
            
            return {
                "reply": reply_text,
                "sources": sources,
                "grounded": bool(context_blocks)
            }
            
        except Exception as e:
            logger.exception("Groq API request failed")
            return {
                "reply": "An error occurred while contacting the AI service. Please try again.",
                "sources": [],
                "grounded": False
            }
