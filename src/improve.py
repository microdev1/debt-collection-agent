import os
import json
import asyncio
import difflib

from datetime import datetime

from livekit.agents import AgentSession, RoomInputOptions, RoomOutputOptions
from livekit.agents.llm import ChatContext, LLMStream
from livekit.plugins import openai

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich import print as rprint

from agents.Customer import CustomerAgent
from agents.DebtCollection import DebtCollectionAgent
from agents.OutboundCallerTest import get_outbound_caller_test_agent

from prompts.debt_collection import get_prompt as get_debt_collection_prompt

from dotenv import load_dotenv

load_dotenv(".env.local")

# Initialize Rich console
console = Console()


LLM_MODEL = "gpt-4.1-nano"

LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Colors for different roles
COLORS = {
    "system": "cyan",
    "customer": "green",
    "agent": "yellow",
    "analysis": "magenta",
    "instruction": "blue",
}


async def get_llm_stream_content(stream: LLMStream):
    """
    Helper function to collect content from an LLM stream.
    """
    content = ""
    async for chunk in stream.to_str_iterable():
        content += chunk
    return content


async def gen_llm_response(system: str, prompt: str, llm=openai.LLM(model=LLM_MODEL)):
    chat_ctx = ChatContext()
    chat_ctx.add_message(role="system", content=system)
    chat_ctx.add_message(role="user", content=prompt)
    return await get_llm_stream_content(llm.chat(chat_ctx=chat_ctx))


async def gen_personality(metadata: dict):
    system = f"""
Your job is to generate realistic loan defaulter personality for testing of voice agents.

Be creative. Hints for things you can vary:
- attitudes like evasive, cooperative, angry, anxious, dispitive, refusive etc.
- backstories like recently lost job, single parent, medical bills etc.

Here is some metadata to help you:
{str(metadata)}

ONLY output the behavioural description combined with backstory.
"""
    prompt = "Generate a personality profile"

    return await gen_llm_response(
        system, prompt, llm=openai.LLM(model=LLM_MODEL, temperature=1.5)
    )


async def have_conversation(metadata: dict, turns=20, text_mode=True):
    """
    Simulates a conversation between a customer agent and a debt collection agent.
    """
    session_config = {
        "room_input_options": RoomInputOptions(text_enabled=text_mode),
        "room_output_options": RoomOutputOptions(
            audio_enabled=not text_mode, transcription_enabled=True
        ),
    }

    # Create agents
    agents = [
        {
            "role": "agent",
            "agent": get_outbound_caller_test_agent(DebtCollectionAgent)(
                metadata=metadata
            ),
            "session": AgentSession(llm=openai.LLM(model="gpt-4.1-mini")),
        },
        {
            "role": "customer",
            "agent": CustomerAgent(**metadata["customer"]),
            "session": AgentSession(llm=openai.LLM(model="gpt-4.1-nano")),
        },
    ]

    for agent in agents:
        await agent["session"].start(agent=agent["agent"], **session_config)

    transcript = []

    def add_message(role: str, text: str):
        transcript.append({"role": role, "text": text})
        role_display = f"[bold {COLORS[role]}]{role.upper()}[/bold {COLORS[role]}]"
        rprint(f"{role_display}: {text}")

    add_message("customer", "Hello, who is this?")

    def check_hangup(agent_info):
        if hasattr(agent_info["agent"], "hangup") and agent_info["agent"].hangup:
            add_message(agent_info["role"], text="hangup")
            return True
        return False

    for _ in range(turns):
        for agent in agents:
            while not (
                reply := await agent["session"].generate_reply(
                    user_input=transcript[-1]["text"]
                )
            ).chat_message:
                if check_hangup(agent):
                    return transcript
                print(".", end="")

            print()

            add_message(agent["role"], reply.chat_message.content[0])

            if check_hangup(agent):
                return transcript

    return transcript


async def analyze(transcript):
    system = """
You are an expert debt collection quality assurance analyst. Your task is to review and analyze a conversation transcript between a debt collection agent and a customer.

Analyze the conversation for the following metrics and provide a score (1-10) for each:
1. Compliance: Did the agent follow FDCPA regulations and maintain professional conduct?
2. Empathy: Did the agent show understanding and compassion for the customer's situation?
3. Efficiency: Did the agent handle the call efficiently without unnecessary delays?
4. Resolution: How effectively did the agent work towards resolving the debt issue?
5. Communication Clarity: Was the agent clear and easy to understand?

For each metric, provide:
- Score (1-10)
- Brief explanation for the score
- Specific examples from the transcript
- Suggestions for improvement

Finally, provide an overall assessment and key recommendations.
"""
    prompt = f"Here is the transcript of a debt collection call. Please analyze it:\n\n{transcript}"

    return await gen_llm_response(system, prompt)


async def tweak_instruction(transcript, analysis, prev_instructions):
    system = """
Your job is to improve instructions for a debt collection agent based on conversation analysis.

You will be given:
1. A transcript of a conversation between a debt collection agent and a customer
2. Analysis of the conversation with metrics and recommendations
3. The previous instructions used by the agent

Your task is to tweak the instructions to address the weaknesses identified in the analysis.

Output ONLY the revised instructions without any explanations or commentary.
"""
    prompt = f"""
Previous Instructions:
{prev_instructions}

Conversation Transcript:
{transcript}

Analysis:
{analysis}

Please tweak the instructions to improve the agent's performance.
"""

    return await gen_llm_response(system, prompt)


async def self_improve():
    # Create a timestamped log file for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"self_improve_{timestamp}.json"
    log_path = os.path.join(LOG_DIR, log_filename)

    metadata = {
        "customer": {
            "name": "Richard Smith",
            "account_number": "4189-5033",
        },
        "debt": {
            "age": "2 months",
            "amount": 150.75,
            "creditor": "Bank of America",
            "type": "Credit Card",
        },
    }

    # Step 1: Generating customer personality
    console.rule("[bold white]Step 1: Generating Customer Personality[/bold white]")
    metadata["customer"]["personality"] = await gen_personality(metadata)

    personality_panel = Panel(
        metadata["customer"]["personality"],
        title="[bold]Customer Personality[/bold]",
        border_style=COLORS["customer"],
        expand=False,
    )
    console.print(personality_panel)

    # Step 2: Simulating conversation
    console.rule("[bold white]Step 2: Simulating Conversation[/bold white]")
    transcript = await have_conversation(metadata)
    console.print(f"[bold]Generated transcript with {len(transcript)} exchanges[/bold]")

    # Step 3: Analyzing conversation
    console.rule("[bold white]Step 3: Analyzing Conversation[/bold white]")
    analysis = await analyze(transcript)

    analysis_panel = Panel(
        Markdown(analysis),
        title="[bold]Conversation Analysis[/bold]",
        border_style=COLORS["analysis"],
        expand=False,
    )
    console.print(analysis_panel)

    # Step 4: Tweaking agent instructions
    console.rule("[bold white]Step 4: Tweaking Agent Instructions[/bold white]")
    old_instructions = get_debt_collection_prompt(metadata)
    new_instructions = await tweak_instruction(transcript, analysis, old_instructions)

    # Generate diff between old and new instructions
    console.rule("[bold white]Instruction Improvements[/bold white]")

    # Create a unified diff
    diff_lines = list(
        difflib.unified_diff(
            old_instructions.splitlines(),
            new_instructions.splitlines(),
            fromfile="Original Instructions",
            tofile="Improved Instructions",
            lineterm="",
            n=3,
        )
    )

    if diff_lines:
        diff_text = "\n".join(diff_lines)
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print("[yellow]No significant changes in instructions.[/yellow]")

    # Show the full new instructions
    instruction_panel = Panel(
        new_instructions,
        title="[bold]Improved Agent Instructions[/bold]",
        border_style=COLORS["instruction"],
        expand=False,
    )
    console.print(instruction_panel)

    # Save all data to log file
    log_data = {
        "metadata": metadata,
        "transcript": transcript,
        "analysis": analysis,
        "old_instructions": old_instructions,
        "new_instructions": new_instructions,
        "timestamp": timestamp,
    }

    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    console.print(
        f"\n[bold green]Self-improvement session completed and logged to {log_path}[/bold green]"
    )


async def quick_convo():
    metadata = {
        "customer": {
            "name": "Richard Smith",
            "account_number": "4189-5033",
            "personality": "",
        },
        "debt": {
            "age": "2 months",
            "amount": 150.75,
            "creditor": "Bank of America",
            "type": "Credit Card",
        },
    }

    await have_conversation(metadata)


if __name__ == "__main__":
    asyncio.run(quick_convo())
