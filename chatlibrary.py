import asyncio
from services.call_details import CallContext
from services.gpt_service import LLMFactory  # Replace `your_module` with the correct module where the classes are defined
from services.call_details import  CallContext
from Utils.logger_config import
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("Welcome to the LLM Chat Interface!")
    service_name = input("Please select a service (OpenAI, Assistant, Gemini): ")

    context = CallContext()
    context.system_message="You are a helpful assistant.",
    context.initial_message="How can I assist you today?"


    # Instantiate the LLM service using the factory
    llm_service = LLMFactory.get_llm_service(service_name, context)

    print(f"Chatting with {service_name} service. Type 'exit' to quit.")

    interaction_count = 0
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        interaction_count += 1
        await llm_service.completion(user_input, interaction_count)

    print("Goodbye!")



