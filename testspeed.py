import openai
import time
import numpy as np


def measure_time_openai():
    client_openai = openai.OpenAI()

    start_time_openai = time.time()
    sentence_end_time_openai = None
    text_buffer_openai = ""

    stream = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system", "content":"Answer with only one sentence at a time."},
                  {"role": "user", "content": "Hello, how are you?"}],
        stream=True,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            current_time = time.time()
            text_buffer_openai += chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="")

            if '.' in text_buffer_openai or '!' in text_buffer_openai or '?' in text_buffer_openai:
                sentence_end_time_openai = (current_time - start_time_openai) * 1000  # Convert to milliseconds
                break

    return sentence_end_time_openai, text_buffer_openai

# Run the tests 10 times for each service

openai_times = []
openai_texts = []

for i in range(10):
    print(f"Running test {i+1}/10 for OpenAI...")
    openai_time, openai_text = measure_time_openai()
    openai_times.append(openai_time)
    openai_texts.append(openai_text)

# Calculate statistics

openai_avg = np.mean(openai_times)
openai_std = np.std(openai_times)
openai_min = np.min(openai_times)
openai_max = np.max(openai_times)


print(f"\nOpenAI - Avg: {openai_avg:.2f} ms, Std: {openai_std:.2f} ms, Min: {openai_min:.2f} ms, Max: {openai_max:.2f} ms")
print("Returned texts from OpenAI:")
for text in openai_texts:
    print(f"- {text}")
