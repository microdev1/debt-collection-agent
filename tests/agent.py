"""
Testing utilities for the debt collection voice agent
"""

import json
import asyncio

from typing import Dict, Any, List, TypedDict


class ComplianceCheck(TypedDict):
    professional_tone: bool
    no_threats: bool
    identifies_collector: bool
    respectful_language: bool


class CallEvent(TypedDict):
    event: str
    timestamp: str
    details: str


class TestScenario(TypedDict):
    name: str
    config: Dict[str, Any]


class TestResult(TypedDict):
    scenario: str
    user_inputs: List[str]
    agent_responses: List[str]
    compliance_checks: List[ComplianceCheck]
    errors: List[str]


class CallResult(TypedDict):
    phone_number: str
    scenario: str
    call_duration: int
    successful_contact: bool
    customer_response: str
    outcome: str


class ScenarioConfig(TypedDict):
    customer_type: str
    debt_amount: str
    expected_outcome: str
    user_inputs: List[str]


class TestOutput(TypedDict):
    scenario: str
    conversation_test: TestResult
    call_simulation: CallResult


class AgentTester:
    """Utility class for testing voice agent functionality"""

    def __init__(self):
        self.test_scenarios: List[TestScenario] = []
        self.mock_responses: List[str] = []

    def add_test_scenario(self, name: str, config: Dict[str, Any]):
        """Add a test scenario"""
        self.test_scenarios.append({"name": name, "config": config})

    async def test_conversation_flow(
        self, scenario: str, user_inputs: List[str]
    ) -> TestResult:
        """Test conversation flow with mock user inputs"""
        results: TestResult = {
            "scenario": scenario,
            "user_inputs": user_inputs,
            "agent_responses": [],
            "compliance_checks": [],
            "errors": [],
        }

        # Mock the conversation flow
        for input_text in user_inputs:
            try:
                # Simulate agent processing
                response = await self.simulate_agent_response(input_text, scenario)
                results["agent_responses"].append(response)

                # Check compliance
                compliance_check = self.check_compliance(response)
                results["compliance_checks"].append(compliance_check)

            except Exception as e:
                results["errors"].append(str(e))

        return results

    async def simulate_agent_response(self, user_input: str, scenario: str) -> str:
        """Simulate agent response for testing"""
        # This would integrate with your actual agent logic
        return f"Mock response to: {user_input} in scenario: {scenario}"

    def check_compliance(self, response: str) -> ComplianceCheck:
        """Check response for FDCPA compliance"""
        checks: ComplianceCheck = {
            "professional_tone": not any(
                word in response.lower() for word in ["stupid", "idiot", "moron"]
            ),
            "no_threats": not any(
                word in response.lower() for word in ["sue", "arrest", "jail"]
            ),
            "identifies_collector": "collection" in response.lower()
            or "debt" in response.lower(),
            "respectful_language": True,  # More sophisticated check needed
        }

        return checks


class CallSimulator:
    """Simulate phone call scenarios"""

    def __init__(self):
        self.call_events: List[CallEvent] = []

    async def simulate_outbound_call(
        self, phone_number: str, scenario: str
    ) -> CallResult:
        """Simulate an outbound call"""
        call_result: CallResult = {
            "phone_number": phone_number,
            "scenario": scenario,
            "call_duration": 0,
            "successful_contact": True,
            "customer_response": "cooperative",
            "outcome": "payment_arranged",
        }

        # Simulate call progression
        await self.simulate_call_events(call_result)

        return call_result

    async def simulate_call_events(self, call_result: CallResult):
        """Simulate various call events"""
        events = [
            "call_initiated",
            "ringing",
            "answered",
            "agent_greeting",
            "customer_response",
            "negotiation",
            "resolution",
            "call_ended",
        ]

        for event in events:
            await asyncio.sleep(0.1)  # Simulate time delay
            self.call_events.append(
                {
                    "event": event,
                    "timestamp": "2025-06-14T09:00:00Z",
                    "details": f"Simulated {event}",
                }
            )


# Test scenarios
TEST_SCENARIOS: Dict[str, ScenarioConfig] = {
    "cooperative_customer": {
        "customer_type": "cooperative",
        "debt_amount": "$1,250.00",
        "expected_outcome": "payment_arranged",
        "user_inputs": [
            "Yes, I am John Smith",
            "I remember this debt",
            "I can pay $200 per month",
            "Yes, that works for me",
        ],
    },
    "dispute_customer": {
        "customer_type": "dispute",
        "debt_amount": "$850.00",
        "expected_outcome": "dispute_logged",
        "user_inputs": [
            "Yes, this is Jane Doe",
            "I don't owe this money",
            "I want to dispute this debt",
            "Send me the validation",
        ],
    },
    "financial_hardship": {
        "customer_type": "hardship",
        "debt_amount": "$2,100.00",
        "expected_outcome": "hardship_program",
        "user_inputs": [
            "This is Mike Johnson",
            "I lost my job recently",
            "I can only afford $50 per month",
            "Thank you for understanding",
        ],
    },
}


async def run_comprehensive_tests() -> List[TestOutput]:
    """Run comprehensive test suite"""
    tester = AgentTester()
    simulator = CallSimulator()

    results: List[TestOutput] = []

    for scenario_name, scenario_config in TEST_SCENARIOS.items():
        print(f"Testing scenario: {scenario_name}")

        # Test conversation flow
        conversation_result = await tester.test_conversation_flow(
            scenario_name, scenario_config["user_inputs"]
        )

        # Test call simulation
        call_result = await simulator.simulate_outbound_call(
            "+15551234567", scenario_name
        )

        results.append(
            {
                "scenario": scenario_name,
                "conversation_test": conversation_result,
                "call_simulation": call_result,
            }
        )

    return results


if __name__ == "__main__":
    results = asyncio.run(run_comprehensive_tests())
    print(json.dumps(results, indent=2))
