import json
from pyexpat.errors import messages

import anthropic


class PostGenerator:

    def __init__(self):
        with open("api_key.json", "r") as f:
            key = json.load(f)

        self._preprompt = """Bonjour tu es un entrepreneur cliché qui va poster quotidiennement sur LinkedIn, 
                             tu dois être engageant, vendre du rêve et surtout parler de tes propres expériences (que 
                             tu n'as bien evidemment jamais vécu). En prenant en compte ce context, fait moi un post 
                             autour de ce sujet suivant: """

        self.__claude_client = anthropic.Anthropic(api_key=key["claude"])

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


p_gen = PostGenerator()

message = "L'impact des loutres dans l'économie de l'Ouganda"

print(p_gen.generate_claude_post(message))
