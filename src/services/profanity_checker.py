import aiohttp

from src.config.config import API_KEY, PERSPECTIVE_API_URL


async def contains_profanity(text: str) -> bool:
    """
    Checks if the given text contains profanity or not.

    Args:
        - text (str): The input text to be checked for profanity.

    Returns:
        - bool: Returns True if the text contains profanity, otherwise False.

    Raises:
        - Exception: If there is an error while checking the profanity.

    This function sends a POST request to the Perspective API with the input text and checks if the text contains any profanity.
    It uses the aiohttp library to make the HTTP request and handles any errors that may occur during the process.
    The function returns True if the text contains profanity, and False otherwise.
    """
    data = {
        "comment": {"text": text},
        "languages": ["ru"],
        "requestedAttributes": {
            "PROFANITY": {},
            "INSULT": {},
            "THREAT": {},
            "TOXICITY": {},
        },
    }
    params = {"key": API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                PERSPECTIVE_API_URL, params=params, json=data
            ) as response:
                response_text = await response.text()
                if response.status != 200:
                    print(f"Perspective API Error: {response.status}, {response_text}")
                    result = True  # Считаем текст небезопасным
                else:
                    result_json = await response.json()
                    print(f"Response JSON: {result_json}")
                    result = False
                    scores = result_json["attributeScores"]
                    for attribute in ["PROFANITY", "INSULT", "THREAT", "TOXICITY"]:
                        if attribute in scores:
                            score = scores[attribute]["summaryScore"]["value"]
                            if score >= 0.5:
                                result = True
                                break
    except Exception as e:
        print(f"Error checking profanity: {e}")
        result = True  # Считаем текст небезопасным
    return result
