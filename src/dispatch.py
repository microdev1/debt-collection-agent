import os
import json
import asyncio
import argparse

from livekit import api

from dotenv import load_dotenv

load_dotenv(".env.local")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Dispatch a debt collection agent to make a call"
    )
    parser.add_argument(
        "--agent", default="outbound-caller", help="The name of the agent to dispatch"
    )
    parser.add_argument(
        "--room", default="debt-collector-room", help="The room name for the dispatch"
    )
    return parser.parse_args()


args = parse_args()

AGENT = args.agent
ROOM = args.room

metadata = {
    "customer": {"name": "David Jackson", "account_number": "5033-4329"},
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


async def create_explicit_dispatch():
    """Create a dispatch to trigger the debt collection agent to make a call"""
    async with api.LiveKitAPI() as lkapi:
        try:
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=AGENT,
                    room=ROOM,
                    metadata=json.dumps(metadata),
                )
            )
            print(f"Created dispatch: {dispatch}")

            dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=ROOM)
            print(f"There are {len(dispatches)} dispatches in {ROOM}")

        except Exception as e:
            print(f"Error creating dispatch: {e}")


if __name__ == "__main__":
    asyncio.run(create_explicit_dispatch())
