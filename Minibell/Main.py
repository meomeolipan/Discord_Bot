import discord
import os
import sys
import logging
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from google import genai

# TTS(음성 송출)를 위한 필수 패키지
from gtts import gTTS
import static_ffmpeg

# 렌더 서버에서 음성 송출 도구(FFmpeg) 경로를 인식하도록 설정
static_ffmpeg.add_paths()

# 상위 폴더 경로 추가 (keep_alive.py 위치 찾기)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 렌더용 24시간 호스팅 스위치
from keep_alive import keep_alive 

# ==========================================
# 1. 환경 변수 및 설정
# ==========================================
load_dotenv()
discord_token = os.getenv('DISCORD_TOKEN')
gemini_api_key = os.getenv('GEMINI_API_KEY')

# 제미나이 클라이언트 생성
client = genai.Client(api_key=gemini_api_key)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 음성 채널 접속을 위해 필수

bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# 2. 봇 접속 완료 알림
# ==========================================
@bot.event
async def on_ready():
    print(f'✅ 디스코드 봇 로그인 완료: {bot.user.name}')

# ==========================================
# 3. 제미나이 AI 텍스트 답변 기능 (!질문)
# ==========================================
@bot.event
async def on_message(message):
    # 봇 자신의 메시지는 무시
    if message.author == bot.user:
        return

    # '!질문 '으로 시작하는 채팅을 쳤을 때
    if message.content.startswith('!질문 '):
        user_question = message.content[4:] 
        
        thinking_msg = await message.channel.send("🤔 생각 중...")
        max_retries = 3 
        
        for attempt in range(max_retries):
            try:
                response = await client.aio.models.generate_content(
                    model='gemini-flash-latest', 
                    contents=user_question,
                )
                
                answer = response.text
                
                # 디스코드 글자 수 제한(2000자) 해결: 1900자씩 분할 전송
                if len(answer) <= 1900:
                    await thinking_msg.edit(content=answer)
                else:
                    await thinking_msg.edit(content=answer[:1900] + "...\n\n*(내용이 길어서 다음 메시지로 이어집니다!)*")
                    for i in range(1900, len(answer), 1900):
                        await message.channel.send(answer[i:i+1900])
                
                break # 성공했으므로 반복문 탈출
                
            except Exception as e:
                error_str = str(e)
                
                # 구글 서버 혼잡(503) 에러 시 친절한 안내 및 5초 대기 후 재시도
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    if attempt < max_retries - 1:
                        await thinking_msg.edit(content=f"⏳ 구글 서버에 사람이 많네요! 다시 답변을 가져오는 중... (재시도 {attempt+1}/{max_retries})")
                        await asyncio.sleep(5)
                    else:
                        await thinking_msg.edit(content="😅 지금 전 세계적으로 구글 AI 서버가 너무 바빠서 답변을 가져오지 못했어요. 1~2분 뒤에 다시 `!질문` 해주세요!")
                else:
                    print(f"오류 발생: {e}") 
                    await thinking_msg.edit(content="앗, 생각하다가 머리가 꼬였어요! 조금 이따가 다시 질문해 주시겠어요? 🥲")
                    break

    # 중요: on_message 이벤트 안에서 아래 코드를 호출해야 다른 명령어(!tts 등)가 정상 작동함.
    await bot.process_commands(message)

# ==========================================
# 4. 음성 채널 TTS 기능 (!tts 할말)
# ==========================================
@bot.command(name="tts")
async def speak_tts(ctx, *, text: str):
    # 사용자가 음성 채널에 들어가 있는지 확인
    if not ctx.author.voice:
        await ctx.send("😅 먼저 수다 채널(음성 채널)에 들어가신 후 명령어를 입력해주세요!")
        return

    voice_channel = ctx.author.voice.channel

    # 봇을 음성 채널로 부르기
    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client
        await vc.move_to(voice_channel)

    # 텍스트를 mp3 파일로 변환
    tts = gTTS(text=text, lang='ko')
    file_name = f"tts_{ctx.author.id}.mp3"
    tts.save(file_name)

    # 음성 송출
    if not vc.is_playing():
        await ctx.send(f"🗣️ 봇이 읽어줍니다: `{text}`")
        vc.play(discord.FFmpegPCMAudio(file_name))
        
        # 말이 끝날 때까지 대기 후 파일 삭제
        while vc.is_playing():
            await asyncio.sleep(1)
        os.remove(file_name)
    else:
        await ctx.send("잠시만요! 아직 다른 말을 하고 있어요.")
        os.remove(file_name) # 혹시 파일이 꼬이는 것을 방지해 삭제

# ==========================================
# 5. 음성 채널 퇴장 기능 (!나가)
# ==========================================
@bot.command(name="나가")
async def leave_voice(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 수다를 마치고 채널에서 나갑니다!")
    else:
        await ctx.send("저 지금 아무 채널에도 없는데요?")

# ==========================================
# 6. 24시간 호스팅 실행
# ==========================================
keep_alive()
bot.run(discord_token, log_handler=handler)
