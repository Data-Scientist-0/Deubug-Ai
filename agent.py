import os
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT

load_dotenv()


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Add it to your .env file.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )


def analyze_code(code: str, traceback: str = "", stack: str = "Auto-detect", workflow: str = "Auto-detect") -> dict:
    try:
        model = get_client()

        user_content = f"**AI Stack:** {stack}\n**Workflow:** {workflow}\n\n**Code:**\n```python\n{code}\n```"

        if traceback.strip():
            user_content += f"\n\n**Error Traceback:**\n```\n{traceback}\n```"

        response = model.generate_content(user_content)

        return {"response": response.text, "error": None}

    except ValueError as e:
        return {"response": None, "error": str(e)}
    except Exception as e:
        return {"response": None, "error": f"Gemini API Error: {str(e)}"}


def chat_response(messages: list) -> str:
    try:
        model = get_client()

        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)
        last_msg = messages[-1]["content"]
        response = chat.send_message(last_msg)

        return response.text

    except Exception as e:
        return f"Error getting response: {str(e)}"