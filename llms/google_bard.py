import os

import google.generativeai as genai

from .call_details import CallContext
from .gpt_service import AbstractLLMService, logger


class GeminiService(AbstractLLMService):
    """
    GeminiService

    This class provides a service for interacting with the Gemini generative AI model.

    __init__(self, context: CallContext)
        Initialize the GeminiService with the provided CallContext.

        Parameters:
            - context (CallContext): The CallContext object.

    completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user')
        Generate a completion using the Gemini generative AI model based on the provided text.

        Parameters:
            - text (str): The input text to generate a completion for.
            - interaction_count (int): The number of interactions that have occurred.
            - role (str): The role of the user in the interaction. Defaults to 'user'.
            - name (str): The name of the user. Defaults to 'user'.

        Raises:
            - Exception: If an error occurs during the completion process.

        Returns:
            None
    """

    def __init__(self, context: CallContext):
        super().__init__(context)
        genai.configure(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context
            prompt = "\n".join([msg["content"] for msg in messages])

            response = genai.generate_text(
                model="models/text-bison-001",
                prompt=prompt,
                temperature=0.2,
                top_p=0.95,
                top_k=40,
            )

            # Process response and emit
            complete_response = response.result
            await self.emit_complete_sentences(complete_response, interaction_count)
            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in GeminiService completion: {str(e)}")
