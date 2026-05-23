"""SMS notification tool via Twilio."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config.settings import twilio_client, TWILIO_SENDER_PHONE


class SmsArgs(BaseModel):
    """SMS notification parameters."""
    to_number: str = Field(description="Recipient phone in E.164 format (+15551234567)")
    message: str = Field(description="SMS text message")


@tool(args_schema=SmsArgs)
def send_sms_notification(to_number: str, message: str) -> str:
    """Send SMS notification via Twilio."""
    if not twilio_client or not TWILIO_SENDER_PHONE:
        mock_message = f"SMS (Mock): TO={to_number}, MSG={message}"
        print(mock_message)
        return "SMS sent successfully (Mock)."

    try:
        sent_message = twilio_client.messages.create(
            to=to_number,
            from_=TWILIO_SENDER_PHONE,
            body=message,
        )
        print(f"SMS sent: SID={sent_message.sid}")
        return "SMS notification sent successfully."
    except Exception as e:
        print(f"Twilio error: {e}")
        return f"Failed to send SMS: {e}"
