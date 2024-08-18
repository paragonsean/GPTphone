from datetime import datetime, timezone



HIGH_LEVEL_ASSISTANT_ANALYTICS_DATA = {
        "extraction_details":{},
        "cost_details": {
            "average_transcriber_cost_per_conversation": 0,
            "average_llm_cost_per_conversation": 0,
            "average_synthesizer_cost_per_conversation": 1.0
        },
        "historical_spread": {
            "number_of_conversations_in_past_5_days": [],
            "cost_past_5_days": [],
            "average_duration_past_5_days": []
        },
        "conversation_details": {
            "total_conversations": 0,
            "finished_conversations": 0,
            "rejected_conversations": 0
        },
        "execution_details": {
            "total_conversations": 0,
            "total_cost": 0,
            "average_duration_of_conversation": 0
        },
        "last_updated_at": datetime.now(timezone.utc).isoformat()
    }

ACCIDENTAL_INTERRUPTION_PHRASES = [
    "stop", "quit", "bye", "wait", "no", "wrong", "incorrect", "hold", "pause", "break",
    "cease", "halt", "silence", "enough", "excuse", "hold on", "hang on", "cut it",
    "that's enough", "shush", "listen", "excuse me", "hold up", "not now", "stop there", "stop speaking"
]

PRE_FUNCTION_CALL_MESSAGE = "Just give me a moment, I'll be back with you."

FILLER_PHRASES = [
    "No worries.", "It's fine.", "I'm here.", "No rush.", "Take your time.",
    "Great!", "Awesome!", "Fantastic!", "Wonderful!", "Perfect!", "Excellent!",
    "I get it.", "Noted.", "Alright.", "I understand.", "Understood.", "Got it.",
    "Sure.", "Okay.", "Right.", "Absolutely.", "Sure thing.",
    "I see.", "Gotcha.", "Makes sense."
]

FILLER_DICT = {
  "Unsure": ["No worries.", "It's fine.", "I'm here.", "No rush.", "Take your time."],
  "Positive": ["Great!", "Awesome!", "Fantastic!", "Wonderful!", "Perfect!", "Excellent!"],
  "Negative": ["I get it.", "Noted.", "Alright.", "I understand.", "Understood.", "Got it."],
  "Neutral": ["Sure.", "Okay.", "Right.", "Absolutely.", "Sure thing."],
  "Explaining": ["I see.", "Gotcha.", "Makes sense."],
  "Greeting": ["Hello!", "Hi there!", "Hi!", "Hey!"],
  "Farewell": ["Goodbye!", "Thank you!", "Take care!", "Bye!"],
  "Thanking": ["Welcome!", "No worries!"],
  "Apology": ["I'm sorry.", "My apologies.", "I apologize.", "Sorry."],
  "Clarification": ["Please clarify.", "Can you explain?", "More details?", "Can you elaborate?"],
  "Confirmation": ["Got it.", "Okay.", "Understood."]
}

CHECKING_THE_DOCUMENTS_FILLER = "Umm, just a moment, getting details..."
PREDEFINED_FUNCTIONS = ['transfer_call']
TRANSFERING_CALL_FILLER = "Sure, I'll transfer the call for you. Please wait a moment..."

DEFAULT_USER_ONLINE_MESSAGE = "Hey, are you still there?"
DEFAULT_USER_ONLINE_MESSAGE_TRIGGER_DURATION = 6

EXTRACTION_PROMPT = """
Given this transcript from the communication between user and an agent, your task is to extract following information:

###JSON Structure
{}
- Make sure your response is in ENGLISH. 
- If required data doesn't exist or if the transcript is empty, PLEASE USE NULL, 0, or "DOESN'T EXIST" as the values. DO NOT USE RANDOM ARBRITARY DATA.
"""

SUMMARY_JSON_STRUCTURE = {"summary": "Summary of the conversation goes here"}

SUMMARIZATION_PROMPT = """
Given this transcript from the communication between user and an agent your task is to summarize the conversation.
"""

completion_json_format = {"answer": "A simple Yes or No based on if you should cut the phone or not"}

CHECK_FOR_COMPLETION_PROMPT = """
You are an helpful AI assistant that's having a conversation with customer on a phone call. 
Based on the given transcript, should you cut the call?\n\n 
RULES: 
1. If user is not interested in talking, or is annoyed or is angry we might need to cut the phone. 
2. You are also provided with original prompt use the content of original prompt to make your decision. For example if the purpose of the phone call is done and we have all the required content we need to cut the call.

### JSON Structure
{}

""".format(completion_json_format)

EXTRACTION_PROMPT_GENERATION_PROMPT = """
I've asked user to explain in English what data would they like to extract from the conversation. A user will write in points and your task is to form a JSON by converting every point into a respective key value pair.
Always use SNAKE_CASE with lower case characters as JSON Keys

### Example input
1. user intent - intent for the user to come back on app. Example cold, lukewarm, warm, hot.
2. user pulse - Whether the user beleives India will win the world cup or not. Example Austrailia will win the cup, yields no, Rohit Sharma will finally get a world cup medal yields yes 

### Example Output
{
"user_intent": "Classify user's intent to come back to app into cold, warm, lukewarm and hot",
"user_pulse": "Classify user's opinion on who will win the worldcup as "Yes" if user thinks India will win the world cup. Or "No" if user thinks India will not win the worldcup.
}

### Rules
{}
"""

CONVERSATION_SUMMARY_PROMPT = """
Your job is to create the persona of users on based of previous messages in a conversation between an AI persona and a human to maintain a persona of user from assistant's perspective.
Messages sent by the AI are marked with the 'assistant' role.
Messages the user sends are in the 'user' role.
Gather the persona of user like their name, likes dislikes, tonality of their conversation, theme of the conversation or any anything else a human would notice.
Keep your persona summary less than 150 words, do NOT exceed this word limit.
Only output the persona, do NOT include anything else in your output.
If there were any proper nouns, or number or date or time involved explicitly maintain it.
"""

FILLER_PROMPT = "Please, do not start your response with fillers like Got it, Noted.\nAbstain from using any greetings like hey, hello at the start of your conversation"

DATE_PROMPT = "### Date\n Today\'s Date is {}"

FUNCTION_CALL_PROMPT = "We did made a function calling for user. We hit the function : {} and send a {} request and it returned us the response as given below: {} \n\n . Understand the above response and convey this response in a context to user. ### Important\n1. If there was an issue with the API call, kindly respond with - Hey, I'm not able to use the system right now, can you please try later? \n2. IF YOU CALLED THE FUNCTION BEFORE, PLEASE DO NOT CALL THE SAME FUNCTION AGAIN!"

SERVICES=StreamService,AssistantService,OpenAIService,GeminiService
EVENTHANDLERS=EventHandler,AssitantsEventHandler
telephony=BASE