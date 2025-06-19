from livekit.agents import Agent

from prompts.customer import get_prompt


class CustomerAgent(Agent):
    """
    Customer agent is designed to simulate a customer interaction.
    """

    def __init__(self, name: str, account_number: str, personality: str):
        super().__init__(
            instructions=get_prompt(
                {
                    "name": name,
                    "account_number": account_number,
                    "personality": personality,
                }
            ),
        )
