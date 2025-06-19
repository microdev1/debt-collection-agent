import json

from livekit.agents import (
    cli,
    AgentSession,
    JobContext,
    WorkerOptions,
    RoomInputOptions,
    RoomOutputOptions,
)
from livekit.plugins import openai

from agents.DebtCollection import DebtCollectionAgent
from agents.OutboundCaller import get_outbound_caller_agent

from utils.transcript import setup_transcript

from dotenv import load_dotenv

load_dotenv(".env.local")


async def entrypoint(ctx: JobContext):
    metadata = json.loads(ctx.job.metadata)
    agent = get_outbound_caller_agent(DebtCollectionAgent)(metadata=metadata)
    session = AgentSession(llm=openai.LLM(model="gpt-4.1-mini"))
    config = {
        "room": ctx.room,
        "room_input_options": RoomInputOptions(
            audio_enabled=False,
            text_enabled=True,
        ),
        "room_output_options": RoomOutputOptions(
            audio_enabled=False,
            transcription_enabled=True,
        ),
    }

    setup_transcript(ctx, session, "andrea")

    await ctx.connect()
    await session.start(agent=agent, **config)

    await session.generate_reply(user_input="who this?, please I can't talk right now")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint, agent_name="tester"))
