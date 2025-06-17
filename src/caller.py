import os
import json
import asyncio
import logging
import datetime

from dotenv import load_dotenv

from livekit import api
from livekit.agents import (
    cli,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
)
from livekit.plugins import openai, noise_cancellation

from agents.DebtCollection import DebtCollectionAgent
from agents.OutboundCaller import get_outbound_caller_agent

load_dotenv(dotenv_path=".env.local")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_NAME = os.environ.get("LIVEKIT_AGENT_NAME", "outbound-caller")
OUTBOUND_TRUNK = os.environ["LIVEKIT_SIP_OUTBOUND_TRUNK"]

LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_transcript(ctx: JobContext, session: AgentSession):
    async def save_transcript():
        current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            LOG_DIR, f"transcript_{ctx.room.name}_{current_date}.json"
        )

        try:
            with open(filename, "w") as f:
                json.dump(session.history.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save transcript: {e}")

    ctx.add_shutdown_callback(save_transcript)


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")

    session = AgentSession(llm=openai.realtime.RealtimeModel())

    setup_transcript(ctx, session)

    metadata = json.loads(ctx.job.metadata)
    agent = get_outbound_caller_agent(DebtCollectionAgent)(
        metadata=metadata,
    )
    participant_identity = metadata["dial"]["to"]

    try:
        await ctx.connect()

        session_started = asyncio.create_task(
            session.start(
                agent=agent,
                room=ctx.room,
                room_input_options=RoomInputOptions(
                    noise_cancellation=noise_cancellation.BVCTelephony(),
                ),
            )
        )

        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=OUTBOUND_TRUNK,
                sip_call_to=participant_identity,
                participant_identity=participant_identity,
            )
        )

        # wait for agent
        await session_started

        # wait for participant
        await ctx.wait_for_participant(identity=participant_identity)

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # necessary for external dispatch signal
            agent_name=AGENT_NAME,
        )
    )
