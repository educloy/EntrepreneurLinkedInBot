import os

import anthropic
from openai import OpenAI
from mistralai import Mistral
from google import genai

class PostGenerator:

    def __init__(self):

        self._preprompt = """Bonjour tu es un entrepreneur cliché qui va poster quotidiennement sur LinkedIn, 
                             tu dois être engageant, vendre du rêve et surtout parler de tes propres expériences (que 
                             tu n'as bien evidemment jamais vécu). En prenant en compte ce context, fait moi un post 
                             autour du sujet suivant: """

        self.__claude_client = anthropic.Anthropic(api_key=os.environ["CLAUDE"])
        self.__gpt_client = OpenAI(api_key=os.environ["GPT"])
        self.__mistral_client = Mistral(api_key=os.environ["MISTRAL"])
        self.__deepseek_client = OpenAI(api_key=os.environ["DEEPSEEK"], base_url="https://api.deepseek.com")
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

    def generate_gpt_post(self, prompt: str):
        model = "gpt-4o"
        message = [
            {
                "role": "user",
                "content": self._preprompt + prompt
            }
        ]

        answer = self.__gpt_client.chat.completions.create(model=model, messages=message)
        return answer.choices[0].message.content

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

    def generate_deepseek_post(self, prompt:str):
        model = "deepseek-chat"
        message = [
            {
                "role": "user",
                "content": self._preprompt + prompt,
            },
        ]

        answer = self.__deepseek_client.chat.completions.create(model=model, messages=message, stream=False)
        return answer.choices[0].message.content

    def generate_gemini_post(self, prompt:str):
        model = "gemini-2.0-flash"
        message = [self._preprompt + prompt]
        answer = self.__gemini_client.models.generate_content(model=model, contents=message)
        return answer.text

p_gen = PostGenerator()

message = "L'impact des loutres dans l'économie de l'Ouganda"

print(p_gen.generate_gemini_post(message))

