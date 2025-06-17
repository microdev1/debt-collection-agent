import os
import json
import asyncio
import difflib

from datetime import datetime

from livekit.agents.llm import ChatContext, LLMStream
from livekit.plugins import openai

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint
from rich.syntax import Syntax

from prompts.customer import get_prompt as get_customer_prompt
from prompts.debt_collection import get_prompt as get_debt_collection_prompt

from dotenv import load_dotenv

load_dotenv(".env.local")

# Initialize Rich console
console = Console()


LLM_MODEL = "gpt-4.1-mini"

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


async def have_conversation(metadata: dict, turns=20):
    """
    Simulates a conversation between a customer agent and a debt collection agent.
    The agents are connected to a LiveKit room to demonstrate realistic agent communication.
    """
    hangup_msg = "\n\nIf you want to hangup the call just repond with 'hangup'."

    transcript = []

    customer_ctx = ChatContext()
    customer_ctx.add_message(
        role="system", content=get_customer_prompt(metadata["customer"]) + hangup_msg
    )

    collector_ctx = ChatContext()
    collector_ctx.add_message(
        role="system",
        content=get_debt_collection_prompt(metadata=metadata)
        + f"\n\nThis is a test scenario, so tools aren't available. You can verify user manually by asking for last four digits of their account number."
        + f"\n{str(metadata)}"
        + hangup_msg,
    )

    def add_message(msg: str, speaker_is_customer: bool):
        if speaker_is_customer:
            customer_ctx.add_message(role="assistant", content=msg)
            collector_ctx.add_message(role="user", content=msg)

        else:
            customer_ctx.add_message(role="user", content=msg)
            collector_ctx.add_message(role="assistant", content=msg)

        role = "customer" if speaker_is_customer else "agent"
        transcript_entry = {
            "role": role,
            "text": msg,
        }

        transcript.append(transcript_entry)

        # Print colorful message
        role_display = f"[bold {COLORS[role]}]{role.upper()}[/bold {COLORS[role]}]"
        rprint(f"{role_display}: {msg}")

    add_message("Hello, who is this?", speaker_is_customer=True)

    llm = openai.LLM(model=LLM_MODEL)

    for _ in range(turns):
        reply = await get_llm_stream_content(llm.chat(chat_ctx=collector_ctx))
        add_message(reply, speaker_is_customer=False)

        if "hangup" in reply.lower():
            break

        reply = await get_llm_stream_content(llm.chat(chat_ctx=customer_ctx))
        add_message(reply, speaker_is_customer=True)

        if "hangup" in reply.lower():
            break

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


if __name__ == "__main__":
    asyncio.run(self_improve())
