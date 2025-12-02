import edge_tts
import asyncio

async def test():
    text = "سلام، حالت چطوره؟ من روژان هستم."
    voice = "en-US-AvaMultilingualNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save("test_output.mp3")
    print("✅ فایل test_output.mp3 ساخته شد!")

asyncio.run(test())
