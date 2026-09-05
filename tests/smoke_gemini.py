"""Smoke test for Gemini API connectivity.

Loads GEMINI_API_KEY from environment variables, initializes the Gemini client,
sends a hardcoded test prompt, and prints the response.
Supports both `google-genai` (official new SDK) and `google-generativeai` (legacy SDK).
"""

import os
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        print("[ERROR] Missing or placeholder environment variable: GEMINI_API_KEY")
        print("Please configure GEMINI_API_KEY in your .env file before running this script.")
        sys.exit(1)

    prompt = "Hello! Please reply in one concise sentence confirming that the Gemini API connection works."
    print(f"[INFO] Connecting to Gemini API with prompt: '{prompt}'...")

    # Attempt official google-genai SDK first
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        print("\n[SUCCESS] Connected to Gemini API successfully!")
        print("-" * 60)
        print(f"Response:\n{response.text}")
        print("-" * 60)
        return
    except ImportError:
        pass
    except Exception as ex:
        print(f"[WARN] Failed with google-genai SDK: {ex}")
        print("[INFO] Attempting fallback to google-generativeai...")

    # Fallback to google-generativeai SDK if installed
    try:
        import google.generativeai as gai
        gai.configure(api_key=api_key)
        model = gai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        print("\n[SUCCESS] Connected to Gemini API successfully (via legacy SDK)!")
        print("-" * 60)
        print(f"Response:\n{response.text}")
        print("-" * 60)
        return
    except ImportError:
        print("[ERROR] Neither 'google-genai' nor 'google-generativeai' library is installed.")
        print("Install dependencies with: pip install google-genai (or pip install -r requirements.txt)")
        sys.exit(1)
    except Exception as ex:
        print(f"[ERROR] Gemini API request failed: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
