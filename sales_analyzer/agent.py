"""
Sales Agent Prompt Generator

Takes the structured sales analysis and produces two artifacts:
  1. A fully-formed SYSTEM PROMPT ready to initialize a sales AI agent.
  2. An INTERACTIVE AGENT MODE that uses the generated prompt to run
     a live sales conversation powered by Claude.
"""

import json
import anthropic

# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

GENERATOR_SYSTEM_PROMPT = """You are a prompt engineer who specializes in building elite AI sales agents.
You translate structured sales knowledge into precise, behavioral system prompts that make AI agents
perform like seasoned sales professionals. Your prompts are direct, action-oriented, script-rich,
and cover every stage of the sales conversation."""

GENERATOR_USER_TEMPLATE = """Using the sales knowledge extracted below, write a comprehensive SYSTEM PROMPT
for an AI sales agent.

EXTRACTED SALES KNOWLEDGE:
{analysis_json}

---

The system prompt you write must:

1. **Define the agent's identity** — who they are, their sales philosophy, their tone and personality.
2. **Embed the full sales process** — step-by-step instructions for each stage (prospecting, opener,
   discovery, demo/pitch, objection handling, close, follow-up).
3. **Include verbatim scripts** — use exact talk tracks and scripts from the extracted knowledge wherever possible.
4. **Program objection responses** — include IF/THEN trees: IF prospect says X → respond with Y.
5. **List discovery questions** — the agent must ask these in sequence during discovery.
6. **Define qualifying criteria** — instruct the agent on how to qualify or disqualify prospects.
7. **Embed psychological triggers** — buying signals, rapport tactics, urgency creation.
8. **Set closing behavior** — when to go for the close, which technique to use, how to handle stalls.
9. **Specify follow-up cadence** — what to say and when after a call/meeting.
10. **Include mindset anchors** — key principles the agent should operate by at all times.
11. **Define success metrics** — what the agent is optimizing for.

The prompt must be written in SECOND PERSON (you/your) as a direct instruction to the agent.
It must be comprehensive enough that the agent needs NO additional context to conduct a full sales conversation.

Start the prompt with: "You are [Agent Name], an elite sales professional..."

Write the complete system prompt now — make it as detailed and powerful as possible:"""


def generate_agent_prompt(analysis: dict, client: anthropic.Anthropic, model: str = "claude-opus-4-5") -> str:
    """
    Generate a complete sales agent system prompt from the analysis dict.

    Returns the system prompt as a string.
    """
    analysis_json = json.dumps(analysis, indent=2, ensure_ascii=False)
    user_message = GENERATOR_USER_TEMPLATE.format(analysis_json=analysis_json)

    response = client.messages.create(
        model=model,
        max_tokens=8096,
        system=GENERATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Interactive Sales Agent
# ---------------------------------------------------------------------------

class SalesAgent:
    """
    An interactive sales agent powered by Claude, initialized with the
    generated system prompt. Maintains full conversation history.
    """

    def __init__(self, system_prompt: str, client: anthropic.Anthropic, model: str = "claude-opus-4-5"):
        self.system_prompt = system_prompt
        self.client = client
        self.model = model
        self.conversation_history = []
        self.turn_count = 0

    def chat(self, user_message: str) -> str:
        """Send a message and get the agent's response."""
        self.conversation_history.append({"role": "user", "content": user_message})
        self.turn_count += 1

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text.strip()
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def reset(self):
        """Reset conversation history (start a new prospect conversation)."""
        self.conversation_history = []
        self.turn_count = 0

    def get_conversation_summary(self, client: anthropic.Anthropic) -> str:
        """Ask Claude to summarize the conversation and suggest next steps."""
        if not self.conversation_history:
            return "No conversation to summarize."

        history_text = '\n'.join(
            f"{'AGENT' if msg['role'] == 'assistant' else 'PROSPECT'}: {msg['content']}"
            for msg in self.conversation_history
        )

        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": (
                    f"Summarize this sales conversation and provide:\n"
                    f"1. Where the prospect is in the buying journey\n"
                    f"2. Key pain points uncovered\n"
                    f"3. Objections raised\n"
                    f"4. Recommended next steps\n\n"
                    f"CONVERSATION:\n{history_text}"
                )
            }],
        )
        return response.content[0].text.strip()

    def export_conversation(self) -> dict:
        """Export conversation history and metadata."""
        return {
            "turn_count": self.turn_count,
            "conversation": self.conversation_history,
            "system_prompt_preview": self.system_prompt[:300] + "...",
        }


def run_interactive_agent(agent: SalesAgent):
    """
    Run the sales agent in an interactive terminal loop.

    The user plays the role of the prospect; the agent plays the salesperson.
    """
    print("\n" + "="*65)
    print("  INTERACTIVE SALES AGENT  (you are the PROSPECT)")
    print("  Commands: /summary | /reset | /export | /quit")
    print("="*65)
    print("\nAgent is starting the conversation...\n")

    # Agent opens the call
    opener = agent.chat("Hi, I just picked up the phone.")
    print(f"AGENT: {opener}\n")

    while True:
        try:
            user_input = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() == "/quit":
            print("Session ended.")
            break
        elif user_input.lower() == "/summary":
            print("\n--- CONVERSATION SUMMARY ---")
            print(agent.get_conversation_summary(agent.client))
            print("----------------------------\n")
            continue
        elif user_input.lower() == "/reset":
            agent.reset()
            print("\n[Conversation reset — new prospect]\n")
            opener = agent.chat("Hi, I just picked up the phone.")
            print(f"AGENT: {opener}\n")
            continue
        elif user_input.lower() == "/export":
            data = agent.export_conversation()
            print("\n--- CONVERSATION EXPORT ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("---------------------------\n")
            continue

        response = agent.chat(user_input)
        print(f"\nAGENT: {response}\n")
