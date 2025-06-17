import json
import logging
import datetime

from typing import Any

from livekit.agents import (
    function_tool,
    Agent,
    RunContext,
)

logger = logging.getLogger()


class DebtCollectionAgent(Agent):
    debt_disputed = False
    hardship_claimed = False
    payment_plan_offered = False
    payment_plan_started = False

    def __init__(
        self,
        metadata: dict[str, Any],
    ):
        super().__init__(
            instructions=f"""
You are Alex, a debt collection agent working for {metadata["debt"]["creditor"]}.
Your interface will be voice. You will be on a call with a customer who has an outstanding debt.

CONVERSATION FLOW:
1. Professional greeting.
2. Identify yourself and the company you represent.
3. Explain the purpose of the call.
4. Before proceeding, verify identity of the person you're speaking with by confirming their name and last four digits of their account number.
5. Discuss the debt amount and details.
6. Listen to the customer's situation with empathy.
7. Offer payment solutions (reschedule payment, payment plan, settlement).
8. Schedule follow-up if needed.
9. End professionally with next steps clearly stated.

CRITICAL COMPLIANCE RULES:
- Maintain a professional and respectful tone at all times
- Never use threatening language or intimidation tactics
- Provide debt validation information when requested
- Respect the customer's right to dispute the debt
- Be empathetic to hardship situations
- Stick to your job and do not deviate from the provided instructions
- If a situation is better handeled by a human agent, notify the customer and transfer the call
- Follow all FDCPA (Fair Debt Collection Practices Act) guidelines

CUSTOMER:
- Name: {metadata["customer"]["name"]}
- Account number: {metadata["customer"]["account_number"]}

DEBT:
- Age: {metadata["debt"]["age"]}
- Type: {metadata["debt"]["type"]}
- Outstanding amount: ${metadata["debt"]["amount"]}
"""
        )

        self.metadata = metadata

    def _log_event(self, event_type: str, data: dict) -> dict:
        """Helper method to create and log standardized event data"""
        event = {
            "event": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "account_number": self.metadata["customer"]["account_number"],
            "data": data,
        }

        logger.info(f"{event_type}: {json.dumps(event)}")
        return event

    @function_tool()
    async def send_validation(self, ctx: RunContext):
        """Send debt validation information to the customer"""

        logger.info(f"Sending debt validation")

        self.debt_disputed = True

        # In a real implementation, this would trigger sending validation documents

        await ctx.session.generate_reply(
            instructions="Inform the customer that debt validation documents will be sent within 5 business days",
        )

        self._log_event("debt_validation_requested", {})

        return "Debt validation request processed"

    @function_tool()
    async def dispute_debt(self, ctx: RunContext):
        """Record a debt dispute from the customer"""

        logger.info("Recording debt dispute")

        self.debt_disputed = True

        # In a real implementation, this would update the customer's record
        # and potentially trigger a formal dispute process

        # Log the dispute event
        self._log_event("debt_disputed", {})

        await ctx.session.generate_reply(
            instructions="Acknowledge the debt dispute and inform the customer that it will be processed according to FDCPA regulations",
        )

        return "Debt dispute recorded successfully"

    @function_tool()
    async def reschedule_payment(self, ctx: RunContext, new_date: str, reason: str):
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
    async def offer_or_start_payment_plan(
        self, ctx: RunContext, months: int = 6, start: bool = False
    ):
        """Offer a payment plan to the customer, start the plan on confirmation"""

        # Calculate a reasonable payment plan based on debt amount
        debt_amount = self.metadata["debt"]["amount"]
        monthly_payment = round(debt_amount / months, 2)  # 6-month payment plan

        if start:
            self.payment_plan_started = True

            # If starting the plan, log the start event
            self._log_event("payment_plan_started", {"months": months})

            await ctx.session.generate_reply(
                instructions="Confirm the payment plan has been started and provide next steps for payment"
            )

            return f"Payment plan started: ${monthly_payment}/month for 6 months"

        else:
            self.payment_plan_offered = True

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
    async def record_hardship_claim(
        self, ctx: RunContext, hardship_type: str, description: str
    ):
        """Record a hardship claim from the customer and adjust the collection approach accordingly"""

        logger.info(f"Recording hardship claim: {hardship_type}")

        self.hardship_claimed = True

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

    @function_tool()
    async def offer_settlement(self, ctx: RunContext, settlement_percentage: int):
        """Offer a settlement amount for the debt"""

        # Calculate settlement amount based on percentage
        debt_amount = self.metadata["debt"]["amount"]
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
    async def verify_customer_identity(
        self, ctx: RunContext, status: bool, notes: str = ""
    ):
        """Record the result of customer identity verification"""

        logger.info(f"Identity verification: {status}")

        # In a real implementation, this would update the verification status in a CRM system

        # Log the verification result
        self._log_event(
            "identity_verification",
            {
                "status": status,
                "notes": notes,
            },
        )

        if status:
            await ctx.session.generate_reply(
                instructions="Thank the customer for verifying their identity and proceed with the conversation",
            )
            return "Identity verified successfully"
        else:
            await ctx.session.generate_reply(
                instructions="Politely inform the customer that you cannot discuss account details without proper verification and offer to try again or have them call back with the necessary information",
            )
            return "Identity verification failed"

    @function_tool()
    async def handle_cease_communication(self, ctx: RunContext, reason: str):
        """Handle a customer's request to cease communication according to FDCPA regulations"""

        logger.info(f"Cease communication request from {reason}")

        # In a real implementation, this would update CRM systems to stop further contact

        # Log the cease communication request
        self._log_event("cease_communication", {"reason": reason})

        await ctx.session.generate_reply(
            instructions="Acknowledge the customer's request to cease communication, confirm that their request will be honored according to FDCPA regulations, and provide a professional closing to the call",
        )

        # After the agent has acknowledged the request, end the call
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        return "Cease communication request processed"

    @function_tool()
    async def creditor_policy_on_default(self, ctx: RunContext):
        """Provide information about the bank's policy on defaulted accounts"""

        logger.info("Providing bank policy on defaulted accounts")

        # Mock policy statement that would normally be retrieved from a database
        policy_statement = f"""
{self.metadata["debt"]["creditor"]} Policy on Defaulted Accounts:
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
