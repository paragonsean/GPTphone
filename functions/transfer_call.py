import asyncio
import os

from twilio.rest import Client

'''
Author: Sean Baker
Date: 2024-07-08 
Description: Transfers call to my personal number, can be useful if ai needs to pass call to human support. 
'''
async def transfer_call(context, args):
    """
    Transfers an active call to a specified phone number.

    Args:
        context: The context object containing information about the call.
        args: Additional arguments (not used in this function).

    Returns:
        A string indicating the result of the call transfer.

    Raises:
        Exception: If there is an error during the call transfer.
    """
    # Retrieve the active call using the CallSid
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    transfer_number = os.environ['TRANSFER_NUMBER']

    client = Client(account_sid, auth_token)
    call_sid = context.call_sid

    # Wait for 10 seconds before transferring the call
    await asyncio.sleep(8)

    try:
        call = client.calls(call_sid).fetch()

        # Update the call with the transfer number
        call = client.calls(call_sid).update(
            url=f'http://twimlets.com/forward?PhoneNumber={transfer_number}',
            method='POST'
        )

        return f"Call transferred."

    except Exception as e:
        return f"Error transferring call: {str(e)}"