import requests
import json
import os
import io
import discord
from PIL import Image
from pathlib import Path
import re
import base64
from dotenv import load_dotenv
from discord.ext import commands

# get .env variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ENDPOINT = os.getenv("ENDPOINT")
PERIOD_IGNORE = os.getenv("PERIOD_IGNORE")

# Generation parameters
# Reference: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
params = {
    'max_new_tokens': 200,
    'do_sample': True,
    'temperature': 0.5,
    'top_p': 1,
    'typical_p': 1,
    'repetition_penalty': 1.1,
    'top_k': 3,
    'min_length': 0,
    'no_repeat_ngram_size': 0,
    'num_beams': 1,
    'penalty_alpha': 0.6,
    'length_penalty': 1,
    'early_stopping': False,
}

def split_text(text):
    parts = re.split(r'\n[a-zA-Z]', text)
    return parts
def upload_character(json_file, img, tavern=False):
    json_file = json_file if type(json_file) == str else json_file.decode('utf-8')
    data = json.loads(json_file)
    outfile_name = data["char_name"]
    i = 1
    while Path(f'characters/{outfile_name}.json').exists():
        outfile_name = f'{data["char_name"]}_{i:03d}'
        i += 1
    if tavern:
        outfile_name = f'TavernAI-{outfile_name}'
    with open(Path(f'characters/{outfile_name}.json'), 'w') as f:
        f.write(json_file)
    if img is not None:
        img = Image.open(io.BytesIO(img))
        img.save(Path(f'characters/{outfile_name}.png'))
    print(f'New character saved to "characters/{outfile_name}.json".')
    return outfile_name

def upload_tavern_character(img, name1, name2):
    _img = Image.open(io.BytesIO(img))
    _img.getexif()
    decoded_string = base64.b64decode(_img.info['chara'])
    _json = json.loads(decoded_string)
    _json = {"char_name": _json['name'], "char_persona": _json['description'], "char_greeting": _json["first_mes"], "example_dialogue": _json['mes_example'], "world_scenario": _json['scenario']}
    _json['example_dialogue'] = _json['example_dialogue'].replace('{{user}}', name1).replace('{{char}}', _json['char_name'])
    return upload_character(json.dumps(_json), img, tavern=True)

def get_reply(prompt):
    response = requests.post(f"https://{ENDPOINT}/run/textgen", json={
        "data": [
            prompt,
            params['max_new_tokens'],
            params['do_sample'],
            params['max_new_tokens'],
            params['temperature'],
            params['top_p'],
            params['typical_p'],
            params['repetition_penalty'],
            params['top_k'],
            params['min_length'],
            params['no_repeat_ngram_size'],
            params['num_beams'],
            params['penalty_alpha'],
            params['length_penalty'],
            params['early_stopping'],
        ]
    })

    if response.status_code == 200:
        reply = response.json()["data"][0]
        print(f"\n\n{reply}\n--------------------\n")
        return reply.replace(prompt, '', 1)
    else:
        return f"Error {response.status_code}"

characters_folder = 'Characters'
cards_folder = 'Cards'
characters = []
# Check the Cards folder for cards and convert them to characters
try:
    for filename in os.listdir(cards_folder):
        if filename.endswith('.png'):
            with open(os.path.join(cards_folder, filename), 'rb') as read_file:
                img = read_file.read()
                name1 = 'User'
                name2 = 'Character'
                tavern_character_data = upload_tavern_character(img, name1, name2)
            with open(os.path.join(characters_folder, tavern_character_data + '.json')) as read_file:
                character_data = json.load(read_file)
                # characters.append(character_data)
            read_file.close()
            os.rename(os.path.join(cards_folder, filename), os.path.join(cards_folder, 'Converted', filename))
except:
    pass
# Load character data from JSON files in the character folder
for filename in os.listdir(characters_folder):
    if filename.endswith('.json'):
        with open(os.path.join(characters_folder, filename)) as read_file:
            character_data = json.load(read_file)
            # Check if there is a corresponding image file for the character
            image_file_jpg = f"{os.path.splitext(filename)[0]}.jpg"
            image_file_png = f"{os.path.splitext(filename)[0]}.png"
            if os.path.exists(os.path.join(characters_folder, image_file_jpg)):
                character_data['char_image'] = image_file_jpg
            elif os.path.exists(os.path.join(characters_folder, image_file_png)):
                character_data['char_image'] = image_file_png
            characters.append(character_data)

def gen_conversation_history():
    conversation_history = f"{char_name}'s Persona: {data['char_persona']}\n" + \
                            f"World Scenario: {data['world_scenario']}\n" + \
                            f'<START>\n' + \
                            f'{char_dialogue}\n' + \
                            f'<START>\n' + \
                            f'{char_name}: {char_greeting}\n'
    return conversation_history

# Print a list of characters and let the user choose one
for i, character in enumerate(characters):
    print(f"{i+1}. {character['char_name']}")
selected_char = int(input("Please select a character: ")) - 1
data = characters[selected_char]
# Get the character name, greeting, and image
char_name = data["char_name"]
char_greeting = data["char_greeting"]
char_dialogue = data["char_greeting"]
char_image = data.get("char_image")

num_lines_to_keep = 20
intents = discord.Intents.all()
prefix="$"
bot = commands.Bot(command_prefix=prefix, intents=intents)
conversation_history = gen_conversation_history()
last_message = ""
last_reply = None

@bot.event
async def on_ready():
    global char_greeting
    # try:
    #     with open(f"Characters/{char_image}", 'rb') as f:
    #         avatar_data = f.read()
    #     await bot.user.edit(username=char_name, avatar=avatar_data)
    # except FileNotFoundError:
    #     with open(f"Characters/default.png", 'rb') as f:
    #         avatar_data = f.read()
    #     await bot.user.edit(username=char_name, avatar=avatar_data)
    #     print(f"No image found for {char_name}. Setting image to default.")
    # except discord.errors.HTTPException as error:
    #     if error.code == 50035 and 'Too many users have this username, please try another' in error.text:
    #         await bot.user.edit(username=char_name + "BOT", avatar=avatar_data)
    #     elif error.code == 50035 and 'You are changing your username or Discord Tag too fast. Try again later.' in error.text:
    #         pass
    #     else:
    #         raise error
    await bot.get_channel(1005942828611928147).send(char_greeting)
    print(f'{bot.user} has connected to Discord!')

async def send_reply(channel,regen=False):
    global conversation_history

    if regen:
        conversation_history = conversation_history.replace(f"You: {last_message}\n{char_name}: {last_reply.content}",'',1).replace("\n\n",'',1)
        conversation_history = conversation_history + f"\nYou: {last_message}\n{char_name}:"

    async with channel.typing():
        reply = get_reply(conversation_history)
        try:
            await channel.send(reply)
            conversation_history = conversation_history + f'{reply}\n'
        except Exception as ex:
            await channel.send(f"ermmmmmmmm...\n{ex}")


@bot.command()
async def reset(ctx):
    global conversation_history
    conversation_history = gen_conversation_history()
    await ctx.send(char_greeting)

@bot.command()
async def regen(ctx):
    global conversation_history

    await ctx.message.add_reaction("✅")
    await last_reply.delete(delay=0)
    await send_reply(ctx.channel,True)

@bot.event
async def on_message(message):
    print(prefix)
    msg = message.content
    if (PERIOD_IGNORE and msg.startswith(".")) or msg.startswith(prefix):
        await bot.process_commands(message)
        return
    else:
        global conversation_history, last_message, last_reply
        if message.author == bot.user:
            last_reply = message
            return

        last_message = msg
        conversation_history = conversation_history + f"You: {msg}\n{char_name}:"
        await send_reply(message.channel)

bot.run(DISCORD_BOT_TOKEN)