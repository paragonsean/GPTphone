import os
import importlib
import json
from openai import AsyncOpenAI
from functions.function_manifest import tools
from .call_details import CallContext
from .gpt_service import AbstractLLMService
from Utils import log_function_call, configure_logger



logger = configure_logger(__name__)


class OpenAIService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.context.set_tools()
        se
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context

            stream = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=self.context.tools,
                tool_choice="auto",
                stream=True,
            )

            complete_response = ""
            function_name = ""
            function_args = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                tool_calls = delta.tool_calls

                if tool_calls:
                    for tool_call in tool_calls:
                        function_name = tool_call['function']['name']
                        if function_name not in self.context.available_functions:
                            logger.error(f"Function {function_name} is not available in available_functions.")
                        else:
                            tool_data = next((tool for tool in tools if tool['function']['name'] == function_name),
                                             None)
                            say = tool_data['function']['say']

                            await self.createEvent('llmreply', {
                                "partialResponseIndex": None,
                                "partialResponse": say
                            }, interaction_count)

                            function_to_call = self.context.available_functions[function_name]
                            function_args = json.loads(tool_call['function']['arguments'])

                        # Call the function and log the response
                            function_response = await function_to_call(**function_args)
                            messages.append(
                                {
                                    "tool_call_id": tool_call['id'],
                                    "role": "tool",
                                    "name": function_name,
                                    "content": function_response,
                                }
                            )
                            if function_name != "end_call":
                                await self.completion(function_response, interaction_count)
                else:
                    complete_response += content
                    await self.emit_complete_sentences(content, interaction_count)



            # Emit any remaining content in the buffer
            if self.sentence_buffer.strip():
                await self.createEvent('llmreply', {
                    "partialResponseIndex": self.partial_response_index,
                    "partialResponse": self.sentence_buffer.strip()
                }, interaction_count)
                self.sentence_buffer = ""

            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in OpenAIService completion: {str(e)}")