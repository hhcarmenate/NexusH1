import os
from dotenv import load_dotenv
load_dotenv()
from integrations.telegram import get_me
bot = get_me()
print(f'Bot username: @{bot.get("username")}')
print(f'Bot ID: {bot.get("id")}')
print(f'Bot name: {bot.get("first_name")}')