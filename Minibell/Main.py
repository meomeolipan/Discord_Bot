import discord
import os
import asyncio
import logging
from discord.ext import commands
from dotenv import load_dotenv
from google import genai
from google.genai import types
from gtts import gTTS
import static_ffmpeg

# 렌더 서버 환경 설정
static_ffmpeg.add_paths()
load_dotenv()

# 환경 변수
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID', 0))

client = genai.Client(api_key=GEMINI_API_KEY)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 자동 퇴장 타이머 변수
disconnect_task = None

async def voice_disconnect_after_delay(vc, delay=10.0):
    await asyncio.sleep(delay)
    if vc and vc.is_connected():
        await vc.disconnect()

@bot.event
async def on_ready():
    print(f'✅ 봇 로그인 완료: {bot.user.name}')

@bot.event
async def on_message(message):
    global disconnect_task
    if message.author.bot: return

    # 1. AI 명령어 (!질문, !생성) 우선 처리
    if message.content.startswith(('!질문', '!생성')):
        await bot.process_commands(message)
        return

    # 2. 일반 채팅 실시간 TTS 읽기 (설정된 채널에서만)
    if message.channel.id == VOICE_CHANNEL_ID and message.author.voice:
        channel = message.author.voice.channel
        
        # 봇 연결 확인
        if bot.voice_clients == []:
            vc = await channel.connect()
        else:
            vc = bot.voice_clients[0]
            if vc.channel != channel: await vc.move_to(channel)

        # 타이머 초기화
        if disconnect_task: disconnect_task.cancel()

        # TTS 생성 및 재생
        tts = gTTS(text=message.content, lang='ko')
        file_name = f"tts_{message.author.id}.mp3"
        tts.save(file_name)
        
        if vc.is_playing(): vc.stop()
        vc.play(discord.FFmpegPCMAudio(file_name), after=lambda e: os.remove(file_name))
        
        disconnect_task = asyncio.create_task(voice_disconnect_after_delay(vc))

    await bot.process_commands(message)

# AI 답변 기능
@bot.command(name="질문")
async def ask_ai(ctx, *, question: str):
    thinking = await ctx.send("🤔 생각 중...")
    config = types.GenerateContentConfig(system_instruction="핵심만 500자 이내로 간결하고 귀엽게 답변해.")
    response = await client.aio.models.generate_content(model='gemini-flash-latest', contents=question, config=config)
    await thinking.edit(content=response.text)

# 이미지 생성 기능
@bot.command(name="생성")
async def generate_image(ctx, *, prompt: str):
    await ctx.send(f"🎨 '{prompt}' 그리는 중...")
    response = client.models.generate_images(model='imagen-3.0-generate-001', prompt=prompt, number_of_images=1)
    embed = discord.Embed(title=f"'{prompt}' 완성!")
    embed.set_image(url=response.generated_images[0].image.image_url)
    await ctx.send(embed=embed)

bot.run(BOT_TOKEN)
