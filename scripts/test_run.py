import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google.antigravity import Agent, LocalAgentConfig
from src.job_app_agent import read_cv, search_job_postings, log_application, SYSTEM_INSTRUCTIONS

async def main():
    config = LocalAgentConfig(
        tools=[read_cv, search_job_postings, log_application],
        system_instructions=SYSTEM_INSTRUCTIONS,
    )
    
    print("Bắt đầu kiểm thử tự động với Agent...")
    async with Agent(config) as agent:
        # Gửi yêu cầu tự động
        prompt = "Hãy tìm việc thực tập Python và viết Cover Letter ứng tuyển, sau đó lưu vào file log."
        print(f"Yêu cầu gửi đi: '{prompt}'")
        
        response = await agent.chat(prompt)
        
        print("\nKết quả phản hồi từ Agent:")
        async for chunk in response:
            print(chunk, end="", flush=True)
        print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())
