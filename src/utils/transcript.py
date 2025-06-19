import os
import json
import logging
import datetime

from livekit.agents import AgentSession, JobContext

from dotenv import load_dotenv

load_dotenv(".env.local")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_transcript(ctx: JobContext, session: AgentSession, prefix="transcript"):
    async def save_transcript():
        current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            LOG_DIR, f"{prefix}_{ctx.room.name}_{current_date}.json"
        )

        try:
            with open(filename, "w") as f:
                json.dump(session.history.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save transcript: {e}")

    ctx.add_shutdown_callback(save_transcript)
