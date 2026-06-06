import asyncio
import os
from google.antigravity import Agent, LocalAgentConfig

async def test_agent():
    # Kiểm tra xem API Key đã được cấu hình hay chưa
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("CẢNH BÁO: Biến môi trường GEMINI_API_KEY chưa được thiết lập!")
        print("Vui lòng lấy một API key tại: https://aistudio.google.com/app/api-keys")
        print("Sau đó chạy lệnh: export GEMINI_API_KEY='your_api_key'")
        return

    print("Đang khởi tạo Agent...")
    async with Agent(LocalAgentConfig()) as agent:
        print("Đang gửi tin nhắn thử nghiệm...")
        response = await agent.chat("Hãy trả lời bằng tiếng Việt: Hello!")
        print("\nKết quả phản hồi từ Agent:")
        print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_agent())
