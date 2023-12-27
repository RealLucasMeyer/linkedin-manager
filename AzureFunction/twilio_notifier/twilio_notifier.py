import os
from twilio.rest import Client

def update_lucas(body):

    account_sid = os.getenv("TWILIO_ACCOUNT_ID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    client = Client(account_sid, auth_token)

    client.api.account.messages.create(
        to="+14258776991",
        from_="+19783965634",
        body=body
    )