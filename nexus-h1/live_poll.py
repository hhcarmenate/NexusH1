import requests, os, time
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
url = f'https://api.telegram.org/bot{token}/getUpdates'

print('Polling for 30 seconds... Send a message to @nexusH1bot NOW!')
offset = 0
for i in range(15):
    resp = requests.get(url, params={'offset': offset, 'limit': 10}, timeout=10).json()
    if resp.get('ok'):
        updates = resp.get('result', [])
        if updates:
            print(f'\nGot {len(updates)} updates!')
            for u in updates:
                offset = u['update_id'] + 1
                msg = u.get('message', {})
                text = msg.get('text', '')[:40]
                print(f'  -> {text}')
        else:
            print(f'[{i}] ...', end='\r')
    time.sleep(2)
print('\nDone')