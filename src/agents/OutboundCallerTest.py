import logging

from typing import Type

from livekit.agents import function_tool, RunContext, Agent


logger = logging.getLogger()


def get_outbound_caller_test_agent(base: Type[Agent]):
    class OutboundCallerTestAgent(base):
        hangup = False

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            metadata = kwargs.get("metadata", {})
            self._transfer_to = metadata.get("dial", {}).get("transfer_to")

        async def _hangup(self):
            """Helper function to hang up the call by deleting the room"""
            self.hangup = True

        @function_tool()
        async def end_call(self, ctx: RunContext):
            """Called when conversation is over to end the call"""
            logger.info(f"ending the call")

            # let the agent finish speaking
            current_speech = ctx.session.current_speech
            if current_speech:
                await current_speech.wait_for_playout()

            await self._hangup()

    return OutboundCallerTestAgent
