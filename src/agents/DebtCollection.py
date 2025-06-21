import json
import logging
import datetime

from dataclasses import dataclass, field

from livekit import api
from livekit.agents import function_tool, get_job_context, RunContext, Agent

logger = logging.getLogger()

from prompts.debt_collection import get_prompt


@dataclass
class Customer:
    account_number: str
    name: str
    phone: str
    email: str


@dataclass
class Debt:
    amount: float
    creditor: str
    due_date: str
    status: str = field(default="unpaid")


@dataclass
class Dial:
    to: str
    transfer_to: str


@dataclass
class Metadata:
    customer: Customer
    debt: Debt
    dial: Dial


class BaseAgent(Agent):
    def __init__(self, instructions: str, metadata: Metadata):
        super().__init__(instructions=instructions)
        self.metadata = metadata

    def _log_event(self, event_type: str, data: dict) -> dict:
        """Helper method to create and log standardized event data"""
        event = {
            "event": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "account_number": self.metadata.customer.account_number,
            "data": data,
        }

        logger.info(f"{event_type}: {json.dumps(event)}")
        return event


class DebtCollectionAgent(Agent):
    def __init__(self, metadata: Metadata):
        super().__init__(instructions="You gotta run through the flow")
        self.metadata = metadata


class CallManagementAgent(BaseAgent):
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
        transfer_to = self.metadata.dial.transfer_to

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

    @function_tool()
    async def schedule_callback(
        self, ctx: RunContext, date: str, time: str, reason: str
    ):
        """Schedule a callback for a later date and time"""

        formatted_date_time = f"{date} at {time}"
        logger.info(f"Scheduling callback on {formatted_date_time}: {reason}")

        # In a real implementation, this would create a calendar entry or task
        # in a CRM or scheduling system

        # Log the callback request
        self._log_event(
            "callback_scheduled",
            {
                "date": date,
                "time": time,
                "reason": reason,
            },
        )

        await ctx.session.generate_reply(
            instructions=f"Confirm the callback has been scheduled for {formatted_date_time} and provide a professional closing to the call",
        )

        return f"Callback scheduled for {formatted_date_time}"


class KnowledgeBaseAgent(BaseAgent):
    @function_tool()
    async def creditor_policy_on_default(self, ctx: RunContext):
        """Provide information about the bank's policy on defaulted accounts"""

        logger.info("Providing bank policy on defaulted accounts")

        # Mock policy statement that would normally be retrieved from a database
        policy_statement = f"""
{self.metadata.debt.creditor} Policy on Defaulted Accounts:
1. Accounts are considered delinquent after 30 days of non-payment
2. After 60 days, accounts enter the collections process
3. At 90 days, accounts are marked as defaulted
4. Defaulted accounts may be reported to credit bureaus
5. After 120 days, accounts may be transferred to third-party collectors
6. Settlement options may be available based on account history and circumstances
7. Hardship programs are available for qualifying customers
"""

        # Log the policy request
        self._log_event("bank_policy_on_default", {})

        return policy_statement


class VerificationAgent(BaseAgent):
    @function_tool()
    async def verify_customer_identity(self, ctx: RunContext, last_four_digits: str):
        """Verify the customer's identity by confirming their last four digits of the account number"""

        # In a real implementation, this would update the verification status in a CRM system

        # Log the verification result
        self._log_event(
            "identity_verification",
            {
                "last_four_digits": last_four_digits,
            },
        )

        metadata = self.metadata

        if last_four_digits == metadata.customer.account_number[-4:]:
            return {
                "verification_status": "success",
                "customer": metadata.customer,
                "debt": metadata.debt,
            }

        else:
            await ctx.session.generate_reply(
                instructions="Politely inform the customer that you cannot discuss account details without proper verification and offer to try again or have them call back with the necessary information or proceed to end the call",
            )
            return "Identity verification failed"


class CustomerOptionsAgent(BaseAgent):
    @function_tool()
    async def payment_reschedule(self, ctx: RunContext, new_date: str, reason: str):
        """Reschedule a payment for the customer"""

        logger.info(f"Rescheduling payment to {new_date} for reason: {reason}")

        # In a real implementation, this would update the payment schedule in a CRM system

        # Log the reschedule request
        self._log_event(
            "payment_rescheduled",
            {
                "new_date": new_date,
                "reason": reason,
            },
        )

        await ctx.session.generate_reply(
            instructions=f"Confirm the payment has been rescheduled to {new_date} and provide any additional instructions needed",
        )

        return f"Payment rescheduled to {new_date}"

    @function_tool()
    async def payment_plan(self, ctx: RunContext, months: int = 6, start: bool = False):
        """Offer a payment plan to the customer, start the plan on confirmation"""

        # Calculate a reasonable payment plan based on debt amount
        debt_amount = self.metadata.debt.amount
        monthly_payment = round(debt_amount / months, 2)  # 6-month payment plan

        if start:
            # If starting the plan, log the start event
            self._log_event("payment_plan_started", {"months": months})

            await ctx.session.generate_reply(
                instructions="Confirm the payment plan has been started and provide next steps for payment"
            )

            return f"Payment plan started: ${monthly_payment}/month for 6 months"

        else:
            self._log_event(
                "payment_plan_offered",
                {
                    "months": months,
                    "monthly_payment": str(monthly_payment),
                    "total_amount": str(debt_amount),
                },
            )

            await ctx.session.generate_reply(
                instructions=f"Offer a payment plan of ${monthly_payment} per month for 6 months"
            )

            return f"Payment plan offered: ${monthly_payment}/month for 6 months"

    @function_tool()
    async def payment_settlement(self, ctx: RunContext, settlement_percentage: int):
        """Offer a settlement amount for the debt"""

        # Calculate settlement amount based on percentage
        debt_amount = self.metadata.debt.amount
        settlement_amount = round(debt_amount * settlement_percentage / 100, 2)

        logger.info(
            f"Offering settlement: ${settlement_amount} ({settlement_percentage}% of ${debt_amount})"
        )

        # In a real implementation, this would check if the settlement offer is authorized
        # based on business rules and debt age

        # Log the settlement offer
        self._log_event(
            "settlement_offered",
            {
                "original_amount": str(debt_amount),
                "settlement_percentage": settlement_percentage,
                "settlement_amount": str(settlement_amount),
            },
        )

        await ctx.session.generate_reply(
            instructions=f"Offer a settlement amount of ${settlement_amount} (which is {settlement_percentage}% of the original ${debt_amount}) as a one-time payment option",
        )

        return f"Settlement offered: ${settlement_amount} ({settlement_percentage}%)"

    @function_tool()
    async def claim_hardship(
        self, ctx: RunContext, hardship_type: str, description: str
    ):
        """Record a hardship claim from the customer and adjust the collection approach accordingly"""

        logger.info(f"Recording hardship claim: {hardship_type}")

        # In a real implementation, this would update the customer's record
        # and potentially trigger special handling procedures

        # Log the hardship claim details
        self._log_event(
            "hardship_claim",
            {"hardship_type": hardship_type, "description": description},
        )

        # Generate appropriate response based on hardship type
        await ctx.session.generate_reply(
            instructions=f"Acknowledge the {hardship_type} hardship with empathy and offer to adjust the payment options or timeline accordingly",
        )

        return f"Hardship claim for {hardship_type} recorded successfully"

    @function_tool()
    async def cease_communication(self, ctx: RunContext, reason: str):
        """Handle a customer's request to cease communication according to FDCPA regulations"""

        logger.info(f"Cease communication request from {reason}")

        # In a real implementation, this would update CRM systems to stop further contact

        # Log the cease communication request
        self._log_event("cease_communication", {"reason": reason})

        await ctx.session.generate_reply(
            instructions="Acknowledge the customer's request to cease communication, confirm that their request will be honored according to FDCPA regulations, and provide a professional closing to the call",
        )

        return "cease communication request processed"

    @function_tool()
    async def dispute_debt(self, ctx: RunContext):
        """Record a debt dispute from the customer"""

        logger.info("Recording debt dispute")

        # In a real implementation, this would update the customer's record
        # and potentially trigger a formal dispute process

        # Log the dispute event
        self._log_event("debt_disputed", {})

        await ctx.session.generate_reply(
            instructions="Acknowledge the debt dispute and inform the customer that it will be processed according to FDCPA regulations",
        )

        return "Debt dispute recorded successfully"
