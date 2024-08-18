import os

from openai import AsyncOpenAI

from functions.function_manifest import tools
from .call_details import CallContext
from .gpt_service import AbstractLLMService


class OpenAIService(AbstractLLMService):
    """

    :class: OpenAIService

    OpenAIService class is a subclass of AbstractLLMService. It provides methods for interacting with the OpenAI Chat API for generating responses based on user input.

    Methods:
        __init__(self, context: CallContext)
            Initializes an instance of the OpenAIService class.

            Parameters:
                context (CallContext): The context for the service.

        async completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user')
            Generates a completion response based on the given text using the OpenAI Chat API.

            Parameters:
                text (str): The user input text.
                interaction_count (int): The number of interactions with the API.
                role (str, optional): The role of the input. Default is 'user'.
                name (str, optional): The name of the role. Default is 'user'.
    """
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context

            stream = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
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
                        if tool_call.function and tool_call.function.name:
                            logger.info(f"Function call detected: {tool_call.function.name}")
                            function_name = tool_call.function.name
                            function_args += tool_call.function.arguments or ""
                else:
                    complete_response += content
                    await self.emit_complete_sentences(content, interaction_count)

                if chunk.choices[0].finish_reason == "tool_calls":
                    logger.info(f"Function call detected: {function_name}")
                    function_to_call = self.available_functions[function_name]
                    function_args = self.validate_function_args(function_args)

                    tool_data = next((tool for tool in tools if tool['function']['name'] == function_name), None)
                    say = tool_data['function']['say']

                    await self.emit('llmreply', {
                        "partialResponseIndex": None,
                        "partialResponse": say
                    }, interaction_count)

                    self.user_context.append({"role": "assistant", "content": say})

                    function_response = await function_to_call(self.context, function_args)

                    logger.info(f"Function {function_name} called with args: {function_args}")

                    if function_name != "end_call":
                        await self.completion(function_response, interaction_count, 'function', function_name)

            # Emit any remaining content in the buffer
            if self.sentence_buffer.strip():
                await self.emit('llmreply', {
                    "partialResponseIndex": self.partial_response_index,
                    "partialResponse": self.sentence_buffer.strip()
                }, interaction_count)
                self.sentence_buffer = ""

            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in OpenAIService completion: {str(e)}")
