import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT_TEMPLATE = """You are a helpful hotel concierge assistant for {hotel_name}.
Your job is to answer guest questions using the hotel information provided below.

HOTEL CONTACT INFO:
- Email: {hotel_email}
- Phone: {hotel_phone}

HOTEL WEBSITE CONTENT:
{hotel_content}

INSTRUCTIONS:
1. Answer questions ONLY based on the hotel information provided above.
2. Always respond in the SAME LANGUAGE the guest is using.
3. Be friendly, professional, and concise.
4. If you cannot find the answer in the hotel information, respond politely saying you don't have that specific information and invite the guest to contact the hotel directly using the email and phone provided above.
5. When you cannot answer, end your reply with a clear section like: "For more information, please contact us: {hotel_email} / {hotel_phone}"
6. NEVER invent information not present in the hotel content.
7. Keep responses focused and helpful.

CANNOT_ANSWER_SIGNAL: If you truly cannot answer the question from the provided content, include the exact text "CANNOT_ANSWER" somewhere in your response (it will be removed before showing to the guest).
"""


async def get_chat_response(
    hotel_name: str,
    hotel_email: str,
    hotel_phone: str,
    hotel_content: str,
    conversation_history: list,
    user_message: str,
) -> tuple[str, bool]:
    """
    Returns (response_text, cannot_answer_flag)
    """
    system = SYSTEM_PROMPT_TEMPLATE.format(
        hotel_name=hotel_name,
        hotel_email=hotel_email or "N/A",
        hotel_phone=hotel_phone or "N/A",
        hotel_content=hotel_content[:15000] if hotel_content else "No content available yet.",
    )

    messages = []
    for msg in conversation_history[-10:]:  # Last 10 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=system,
        messages=messages,
    )

    response_text = response.content[0].text
    cannot_answer = "CANNOT_ANSWER" in response_text
    clean_response = response_text.replace("CANNOT_ANSWER", "").strip()

    return clean_response, cannot_answer
