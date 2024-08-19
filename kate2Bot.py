import discord  # Discord APIを利用するためのライブラリ
from discord.ext import commands, tasks  # コマンドとタスクをサポートするDiscord拡張機能
from openai import OpenAI  # OpenAI APIを利用するためのライブラリ
import base64, os, pytz  # base64エンコード/デコード、OS環境変数操作、タイムゾーン処理
from datetime import datetime, time  # 日時と時間を扱うモジュール
from dotenv import load_dotenv  # .envファイルから環境変数を読み込むためのライブラリ

load_dotenv()  # .envファイルから環境変数を読み込む
token = os.getenv("BOT_TOKEN")  # 環境変数からDiscordボットのトークンを取得
PREFIX = '/'  # ボットのコマンドプレフィックスを設定

intents = discord.Intents.default()  # デフォルトのIntentsを作成
intents.messages = True  # メッセージ関連のイベントを受け取る
intents.reactions = True  # リアクション関連のイベントを受け取る
intents.guilds = True  # ギルド関連のイベントを受け取る
intents.message_content = True  # メッセージの内容にアクセスする
intents.voice_states = True  # ボイスチャットの状態にアクセスする

bot = commands.Bot(command_prefix=PREFIX, intents=intents)  # ボットインスタンスを作成し、指定したIntentsで起動

copy_channel_ids = {}  # サーバーごとのコピー先チャンネル
ai_channel_ids = {} # サーバーごとの対話AIチャンネル
img_channel_ids = {} # サーバーごとの画像生成AIチャンネル
remain_counts = {} # ユーザーごとのAI残り使用回数

# 対話AI API関数
def get_ai_response(prompt):
    client = OpenAI(api_key=os.getenv("API_KEY"))
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"
    
# 画像生成AI API関数
def get_img_response(prompt):
    client = OpenAI(api_key=os.getenv("API_KEY"))
    try:
        # APIリクエストを送信
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        image_url = response.data[0].url
        return image_url
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

#　00:00に使用回数をリセット
@tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.timezone('Asia/Tokyo')))
async def daily_task():
    global remain_counts
    remain_counts = {}

@bot.event
async def on_ready():
    daily_task.start()

# メーセージ送信時
@bot.event
async def on_message(message):
    # 画像をコピー
    global copy_channel_ids
    if message.attachments:
        if str(message.guild.id) in copy_channel_ids:
            target_channel = bot.get_channel(copy_channel_ids[str(message.guild.id)])
            for attachment in message.attachments:
                file_url = attachment.url
                await target_channel.send(file_url)
        else:
            print("Target channel ID is not set.")
    await bot.process_commands(message)

    # AI呼び出し
    if message.author != bot.user and message.content.startswith('/') and not message.content.startswith(('/ai', '/img', '/copy', '/reset')):
        return_message = "**以下のいずれかが原因でエラーが発生しました。**\n" + "- 上限回数超過(1日3回)\n" + "- チャンネルIDの不一致\n"
        if str(message.author.id) in remain_counts:
            remain_counts[str(message.author.id)]-=1
        else:
            remain_counts[str(message.author.id)] = 3
        if remain_counts[str(message.author.id)] > 0:
            if message.channel.id == ai_channel_ids.get(str(message.guild.id)):
                return_message = get_ai_response(message.content[1:])
            elif message.channel.id == img_channel_ids.get(str(message.guild.id)):
                return_message = get_img_response(message.content[1:])
        await message.channel.send(return_message)

# 入室時にサーバーミュートを解除
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and before.channel == None:
        guild_member = member.guild.get_member(member.id)
        await guild_member.edit(mute=False)

# /copy コピー先チャンネル設定コマンド
@bot.command()
async def copy(ctx, channel_id: int):
    global copy_channel_ids
    copy_channel_ids[str(ctx.guild.id)] = channel_id
    await ctx.send('コピー先のチャンネルを設定しました。')

# /ai 対話AIチャンネル設定コマンド
@bot.command()
async def ai(ctx, channel_id: int):
    global ai_channel_ids
    ai_channel_ids[str(ctx.guild.id)] = channel_id
    await ctx.send('AI用のチャンネルを設定しました。')

# /img 画像生成AIチャンネル設定コマンド
@bot.command()
async def img(ctx, channel_id: int):
    global img_channel_ids
    img_channel_ids[str(ctx.guild.id)] = channel_id
    await ctx.send('画像生成用のチャンネルを設定しました。')

# /reset 使用回数リセットコマンド（開発者専用）
@bot.command()
async def reset(ctx, user_id: int):
    if ctx.author.id == 1086540294394237008:
        global remain_counts
        if str(user_id) in remain_counts:
            del remain_counts[str(user_id)]
        await ctx.send('ユーザーの上限回数をリセットしました。')
    else:
        await ctx.send('権限がありません。')

# ボットを起動
bot.run(token)
