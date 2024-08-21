TOOL_MAP = [
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer call to a human, only do this if the user insists on it.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "say": "Transferring your call, please wait."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "End the current call but always ask for confirmation unless it's a natural place in the conversation (and your intent is fulfilled) to end the call.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
            "say": "Goodbye."
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        }
    },
]
