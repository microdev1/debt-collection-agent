import os
import json
import asyncio

from livekit import api

from dotenv import load_dotenv

load_dotenv(".env.local")

AGENT = "outbound-caller"
ROOM = "debt-collector-room"


async def create_explicit_dispatch():
    """Create a dispatch to trigger the debt collection agent to make a call"""

    # Prepare metadata to pass to the agent
    metadata = {
        "customer": {"name": "Alex Johnson", "account_number": "5033-4329"},
        "debt": {
            "age": "2 months",
            "amount": 150.75,
            "creditor": "Bank of America",
            "type": "Credit Card",
        },
        "dial": {
            "to": os.environ["TWILIO_PHONE_TO"],
            "transfer_to": os.getenv("TRANSFER_PHONE_NUMBER"),
        },
    }

    # Create LiveKit API client
    lkapi = api.LiveKitAPI()

    # Create a dispatch for the agent
    try:
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT,
                room=ROOM,
                metadata=json.dumps(metadata),
            )
        )
        print(f"Created dispatch: {dispatch}")

        # List active dispatches in the room
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=ROOM)
        print(f"There are {len(dispatches)} dispatches in {ROOM}")
    except Exception as e:
        print(f"Error creating dispatch: {e}")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(create_explicit_dispatch())
