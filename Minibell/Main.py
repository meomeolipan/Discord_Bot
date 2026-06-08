import discord
import os
import sys
import logging
from discord.ext import commands
from dotenv import load_dotenv
from google import genai

# ==========================================
# 1. 파일 경로 및 환경 설정
# ==========================================
# 부모 폴더(Discord_bot) 경로를 추가하여 keep_alive.py를 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 💡 현재 내 컴퓨터에서 당장 테스트할 때는 아래 한 줄을 # 으로 주석 처리하세요. 
# (나중에 Render 서버에 올릴 때만 #을 지우고 사용합니다!)
# from keep_alive import keep_alive

load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
gemini_api_key = os.getenv('GEMINI_API_KEY')

# 제미나이 클라이언트 생성
client = genai.Client(api_key=gemini_api_key)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# ==========================================
# 2. 디스코드 봇 객체 설정
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# 3. 봇 이벤트 및 로직
# ==========================================
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!질문 '):
        user_question = message.content[4:] 
        
        thinking_msg = await message.channel.send("🤔 생각 중...")
        
        try:
            # 🚨 핵심 수정: 디스코드 봇이 멈추지 않도록 await와 .aio.를 추가!
            response = await client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_question,
            )
            
            await thinking_msg.edit(content=response.text)
            
        except Exception as e:
            # 터미널 창에도 에러의 원인을 빨간 글씨로 출력해 줍니다.
            print(f"제미나이 API 에러 원인: {e}")
            await thinking_msg.edit(content=f"오류가 발생했어요: {e}")

    await bot.process_commands(message)

# ==========================================
# 4. 봇 실행
# ==========================================
# 💡 아래 keep_alive() 도 현재 컴퓨터 테스트 중에는 # 으로 꺼두세요!
# keep_alive()

bot.run(discord_token, log_handler=handler)