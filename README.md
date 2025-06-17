# 🏦 Debt Collection Voice Agent

An automated debt collection voice agent that makes outbound calls to customers with outstanding debts. The agent conducts professional conversations following FDCPA guidelines and handles various customer responses intelligently.

## ✅ Key Features

- Automated outbound calling to debtors
- Professional debt collection conversations compliant with FDCPA
- Handles payment arrangements, disputes, and hardship claims
- Live call transfer to human agents when needed
- Automatic call recording and transcript generation

## 🚀 Quick Start

1. Clone this repository
2. Setup resources and environment variables

### Making Calls

```bash
uv run src/dispatch.py
```

### Running the Agent Service

```bash
uv run src/caller.py
```

## ➡️ Architecture
![](https://docs.livekit.io/images/agents/realtime-model.svg)
![](https://docs.livekit.io/images/sip/outbound-sip-workflow.svg)
![](https://docs.livekit.io/images/sip/architecture.svg)

## 🛠️ Technical Stack

- **Package Manager**: uv (high-performance Python package installer and resolver)
- **Framework**: LiveKit Agents (Python)
- **Speech-to-Spech**: GPT-4o via OpenAI Realtime API
- **Noise Cancellation**: BVC (Background Voice Cancellation)
- **Telephony**: Twilio + LiveKit SIP

## 🔧 Resource Setup

The following resources have been configured for this project:

1. Twilio Phone Number - Used for outbound calling
2. Twilio Trunk - Configured with termination URI and authentication credentials
3. LiveKit outbound trunk - Integrated with Twilio credentials for call handling
4. OpenAI account - Powers the conversational AI capabilities

## 🔑 Environment Variables

The project requires the following environment variables to be set in your `.env.local` file:

- `LIVEKIT_URL` - Your LiveKit server URL
- `LIVEKIT_API_KEY` - Your LiveKit API key
- `LIVEKIT_API_SECRET` - Your LiveKit API secret
- `LIVEKIT_SIP_OUTBOUND_TRUNK` - ID of your LiveKit SIP outbound trunk
- `TWILIO_PHONE_TO` - Phone number to call (with country code)
- `OPENAI_API_KEY` - Your OpenAI API key


## 👨‍⚖️ Compliance

The agent strictly adheres to Fair Debt Collection Practices Act (FDCPA) requirements:
- Always identifies as a debt collector
- Uses professional, respectful communication
- Avoids threatening or abusive language
- Respects time restrictions (8 AM - 9 PM)
- Honors cease communication requests
- Provides debt validation rights
- Maintains accurate call records

## 📝 Development Status

This project has a functional implementation that follows best practices for debt collection, including professional tone, multiple payment solutions, proper dispute handling, and comprehensive conversation logging.

All call transcripts are automatically saved in the `logs` directory for compliance and quality assurance purposes.
