import os
import time

import anthropic
from mistralai import Mistral
from google import genai

from playwright.sync_api import Page
from bs4 import BeautifulSoup

from dotenv import load_dotenv

load_dotenv()

class PostGenerator:

    def __init__(self):

        with open(os.path.join(os.path.dirname(__file__), "preprompt.txt"), "r") as f:
            self._preprompt = f.read()

        self.__claude_client = anthropic.Anthropic(api_key=os.environ["CLAUDE"])
        # self.__gpt_client = OpenAI(api_key=os.environ["GPT"])
        self.__mistral_client = Mistral(api_key=os.environ["MISTRAL"])
        # self.__deepseek_client = OpenAI(api_key=os.environ["DEEPSEEK"], base_url="https://api.deepseek.com")
        self.__gemini_client = genai.Client(api_key=os.environ["GEMINI"])

    def generate_claude_post(self, prompt: str):
        model = "claude-3-7-sonnet-20250219"
        max_tokens = 20000
        temperature = 1
        message = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self._preprompt + prompt
                    }
                ]
            }
        ]

        answer = self.__claude_client.messages.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                                      messages=message)
        return answer.content[0].text

    def generate_gpt_post(self, prompt: str, page:Page):
        page.goto("https://chatgpt.com/")
        time.sleep(2)
        page.locator("#prompt-textarea").fill(self._preprompt + prompt)
        time.sleep(2)
        page.get_by_label("Envoyer le prompt").click()
        # Waits for GPT to finish generating its answer
        page.wait_for_selector("button[aria-label='Copier']", state="visible", timeout=60000)
        # Get the answer
        soup = BeautifulSoup(page.content(), "html.parser")
        page.close()
        answer = soup.find("div", attrs={"data-message-author-role": "assistant"}).text
        return answer

    def generate_mistral_post(self, prompt: str):
        model = "mistral-large-latest"

        message = [
            {
                "role": "user",
                "content": self._preprompt + prompt,
            },
        ]

        answer = self.__mistral_client.chat.complete(model=model,
                                                     messages=message)
        return answer.choices[0].message.content

    def generate_gemini_post(self, prompt:str):
        model = "gemini-2.0-flash"
        message = [self._preprompt + prompt]
        answer = self.__gemini_client.models.generate_content(model=model, contents=message)
        return answer.text

