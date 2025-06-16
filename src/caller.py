# https://github.com/livekit-examples/outbound-caller-python

import os
import json
import asyncio
import logging
import datetime

from dotenv import load_dotenv

from livekit import api
from livekit.agents import (
    AgentSession,
    JobContext,
    cli,
    WorkerOptions,
    RoomInputOptions,
)
from livekit.plugins import (
    openai,
    noise_cancellation,  # noqa: F401
)

from agents.DebtCollector import DebtCollectionAgent

# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")

outbound_trunk_id = os.environ["LIVEKIT_SIP_OUTBOUND_TRUNK"]
agent_name = "outbound-caller"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Directory for storing transcripts
TRANSCRIPT_DIR = os.environ.get("TRANSCRIPT_DIR", "logs")
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")

    # Define transcript saving function
    async def save_transcript():
        current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            TRANSCRIPT_DIR, f"transcript_{ctx.room.name}_{current_date}.json"
        )

        logger.info(f"Saving transcript to {filename}")
        try:
            with open(filename, "w") as f:
                json.dump(session.history.to_dict(), f, indent=2)
            logger.info(
                f"Transcript for {ctx.room.name} saved successfully to {filename}"
            )
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")

    # Register the callback to run when the session ends
    ctx.add_shutdown_callback(save_transcript)

    await ctx.connect()

    # Parse the metadata from the dispatch
    metadata = json.loads(ctx.job.metadata)

    participant_identity = phone_number = metadata["dial"]["phone_number"]

    agent = DebtCollectionAgent(
        metadata=metadata,
    )

    session = AgentSession(llm=openai.realtime.RealtimeModel())

    # start the session first before dialing, to ensure that when the user picks up
    # the agent does not miss anything the user says
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                # enable Krisp background voice and noise removal
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        )
    )

    # `create_sip_participant` starts dialing the user
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # function blocks until user answers the call, or if the call fails
                wait_until_answered=True,
            )
        )

        # wait for the agent session start and participant join
        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        agent.client = participant

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=agent_name,
        )
    )
