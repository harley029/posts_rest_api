import asyncio
import nest_asyncio
import google.generativeai as genai

from src.config.config import GOOGLE_REPLY_API_KEY

genai.configure(api_key=GOOGLE_REPLY_API_KEY)

def generate_reply_sync(post_content: str, comment_content: str) -> str:
    async def _generate():
        prompt = f"""
        Пост: "{post_content}"
        Комментарий: "{comment_content}"
        Як автор посту, напиши відповідь на цей коментар, який буде релевантним та корисним.
        """.strip()

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating reply: {e}")
            return "Дякую за Ваш коментар!"

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        if loop.is_running():
            nest_asyncio.apply(loop)
        return loop.run_until_complete(_generate())
    except Exception as e:
        print(f"Error in event loop: {e}")
        return "Дякую за Ваш коментар!"
