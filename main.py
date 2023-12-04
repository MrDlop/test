import openai
openai.api_key = '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'

# list engines
engines = openai.Engine.list()

# print the first engine's id
print(engines.data[0].id)

# create a completion
completion = openai.Completion.create(engine="ada", prompt="Hello world")

# print the completion
print(completion.choices[0].text)
Источник: https://openai.by/applications/openai-python-library
