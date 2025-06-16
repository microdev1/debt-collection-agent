import logging

from typing import Any

from livekit import rtc, api
from livekit.agents import (
    Agent,
    function_tool,
    RunContext,
    get_job_context,
)


logger = logging.getLogger()


class OutboundCallerAgent(Agent):
    client: rtc.RemoteParticipant

    def __init__(self, instructions: str, transfer_to: str | None = None):
        super().__init__(instructions=instructions)
        self._transfer_to = transfer_to

    async def hangup(self):
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
        logger.info(f"ending the call for {self.client.identity}")  # type: ignore

        # let the agent finish speaking
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
        logger.info(
            f"detected answering machine for {self.client.identity}"  # type: ignore
        )
        await self.hangup()

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
                    participant_identity=self.client.identity,  # type: ignore
                    transfer_to=f"tel:{transfer_to}",
                )
            )
            logger.info(f"transferred call to {transfer_to}")

        except Exception as e:
            logger.error(f"error transferring call: {e}")
            await ctx.session.generate_reply(
                instructions="there was an error transferring the call"
            )
