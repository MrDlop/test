import openai
from openai import OpenAI

openai.api_key = input()
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-3.5-turbo-1106",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "Say hi"},
    ]
)
print(response)
