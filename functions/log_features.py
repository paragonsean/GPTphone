import logging

# Configure logging to file
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler('log_features.log')
file_handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the handlers to the logger
if not logger.handlers:
    logger.addHandler(file_handler)

async def log_features(context, args):
    """
    Logs the features and then asks if the person would like to add their name for credit.

    Args:
        context: The context object (not used in this function).
        args: A dictionary containing new function ideas.
    """
    new_function_ideas = args.get("new_function_ideas", [])

    for idea in new_function_ideas:
        function_name = idea.get("name")
        description = idea.get("description")
        parameters = idea.get("parameters", {})

        logger.info("New Function Idea:")
        logger.info(f"Function Name: {function_name}")
        logger.info(f"Description: {description}")
        logger.info(f"Parameters: {json.dumps(parameters, indent=2)}")
        logger.info("-----")

    return "Logging features. Would you like to add your name for credit?"
