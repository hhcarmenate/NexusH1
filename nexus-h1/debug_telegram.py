import requests, os
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')
if token:
    url = f'https://api.telegram.org/bot{token}/getUpdates'
    resp = requests.get(url, params={'limit': 5}).json()
    print('Updates response:', resp.get('ok'))
    updates = resp.get('result', [])
    print(f'Found {len(updates)} updates')
    for u in updates:
        msg = u.get('message', {})
        txt = msg.get('text', '')[:30]
        uid = u.get('update_id')
        print(f'  Update {uid}: {txt}')
else:
    print('No token found')