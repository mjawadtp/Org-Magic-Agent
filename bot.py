from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
import ssl
import certifi
from cumulusci.core.runtime import BaseCumulusCI

from dotenv import load_dotenv
from talk_to_agent import talk_to_agent
load_dotenv()

SLACK_BOT_TOKEN=os.environ.get('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN=os.environ.get('SLACK_APP_TOKEN')

app=App(token=SLACK_BOT_TOKEN)
print(app)
@app.event("app_mention")
def mention_handler(body,say):
    print(body)
    say('Hello World')

@app.event("message")
def respond_message(message, say):
    print(message)
    # --- Extract Message Information ---
    channel_id = message.get('channel')
    user_id = message.get('user')
    text = message.get('text', '')
    event_ts = message.get('ts')
    thread_ts = message.get('thread_ts')
    files = message.get('files', [])
    print(channel_id, user_id, text, event_ts, thread_ts, files)
    try:
        app.client.reactions_add(channel=channel_id, name='eyes', timestamp=event_ts)
    except Exception as e:
        print(f"  Warning: Failed to add :eyes: reaction: {e}")
    if thread_ts:
        response = talk_to_agent(text,system_instructions="Check if the user has provided the username, password, and url of the Salesforce org they want to connect to.If not, ask them for the information.If yes call the connect_to_salesforce_org tool to connect to the org.")
    else:
        response = talk_to_agent(text,system_instructions="This is initial message.Always ask the user for the username, password, and url of the Salesforce org they want to connect to.")
    # response = talk_to_agent(text)
    reply_thread_ts = thread_ts or event_ts
    app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=reply_thread_ts,
                text=response
    )
    app.client.reactions_remove(channel=channel_id, name='eyes', timestamp=event_ts)

if __name__=="__main__":
    handler=SocketModeHandler(app,SLACK_APP_TOKEN)
    handler.start()
