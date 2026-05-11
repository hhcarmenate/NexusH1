import requests, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')

# Check bot info
url = f'https://api.telegram.org/bot{token}/getMe'
resp = requests.get(url).json()
print('Bot:', resp.get('result', {}).get('username'))

# Check webhook
url2 = f'https://api.telegram.org/bot{token}/getWebhookInfo'
resp2 = requests.get(url2).json()
print('Webhook:', resp2.get('result', {}).get('url', 'None'))
print('Pending:', resp2.get('result', {}).get('pending_update_count', 0))

# Get ALL updates with offset=0
url3 = f'https://api.telegram.org/bot{token}/getUpdates'
resp3 = requests.get(url3, params={'offset': 0, 'limit': 100}).json()
updates = resp3.get('result', [])
print(f'Total updates in queue: {len(updates)}')
if updates:
    for u in updates[-3:]:
        msg = u.get('message', {})
        uid = u.get('update_id')
        text = msg.get('text', '')[:30]
        print(f'  [{uid}] {text}')