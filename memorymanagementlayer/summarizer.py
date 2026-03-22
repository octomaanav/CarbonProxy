# summarizer.py
async def summarize_to_memory(prompt, response, client):
    summary_prompt = (
        "In one sentence (max 30 words), summarize the key fact or decision "
        f"from this exchange.\nUser: {prompt}\nAssistant: {response}\nSummary:"
    )
    result = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=60
    )
    return result.choices[0].message.content.strip()