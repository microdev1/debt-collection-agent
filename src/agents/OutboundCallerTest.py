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

        @function_tool()
        async def end_call(self, ctx: RunContext):
            """Called when conversation is over to end the call"""
            logger.info(f"ending the call")

            self.hangup = True

        @function_tool()
        async def detected_answering_machine(self, ctx: RunContext):
            """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
            logger.info(f"detected answering machine")
            self.hangup = True

        @function_tool()
        async def transfer_call(self, ctx: RunContext):
            """Transfer the call to a human agent, called after confirming with the user"""
            return "sorry, cannot transfer the call at the moment"

    return OutboundCallerTestAgent
