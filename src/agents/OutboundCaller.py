import logging

from typing import Any, Type

from livekit import rtc, api
from livekit.agents import function_tool, get_job_context, RunContext, Agent


logger = logging.getLogger()


def get_outbound_caller_agent(base: Type[Agent]):
    class OutboundCallerAgent(base):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            metadata = kwargs.get("metadata", {})
            self._transfer_to = metadata.get("dial", {}).get("transfer_to")

        async def _hangup(self):
            """Helper function to hang up the call by deleting the room"""
            job_ctx = get_job_context()
            await job_ctx.api.room.delete_room(
                api.DeleteRoomRequest(
                    room=job_ctx.room.name,
                )
            )

        @function_tool()
        async def end_call(self, ctx: RunContext):
            """Called when conversation is over to end the call"""
            logger.info(f"ending the call")

            # let the agent finish speaking
            current_speech = ctx.session.current_speech
            if current_speech:
                await current_speech.wait_for_playout()

            await self._hangup()

        @function_tool()
        async def detected_answering_machine(self, ctx: RunContext):
            """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
            logger.info(f"detected answering machine")
            await self._hangup()

        @function_tool()
        async def transfer_call(self, ctx: RunContext):
            """Transfer the call to a human agent, called after confirming with the user"""

            transfer_to = self._transfer_to

            if not transfer_to:
                return "sorry, cannot transfer the call at the moment"

            logger.info(f"transferring call to {transfer_to}")

            job_ctx = get_job_context()

            try:
                await job_ctx.api.sip.transfer_sip_participant(
                    api.TransferSIPParticipantRequest(
                        room_name=job_ctx.room.name,
                        transfer_to=transfer_to,
                    )
                )
                logger.info(f"transferred call to {transfer_to}")

            except Exception as e:
                logger.error(f"error transferring call: {e}")
                await ctx.session.generate_reply(
                    instructions="there was an error transferring the call"
                )

    return OutboundCallerAgent
