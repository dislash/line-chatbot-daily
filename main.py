#-*- coding: utf-8 -*-

from flask import Flask, request, abort
from elasticsearch import Elasticsearch
import os
import datetime
import time

# connect to the Elasticsearch cluster
elastic = Elasticsearch([{'host': '34.97.218.155', 'port': 9200}])

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, 
    ButtonsTemplate, ConfirmTemplate, MessageTemplateAction
)

app = Flask(__name__)

#環境変数取得
YOUR_CHANNEL_ACCESS_TOKEN = os.environ["YOUR_CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["YOUR_CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(event)
    if event.reply_token == "00000000000000000000000000000000":
        return

    req_message = event.message.text
    if req_message == 'daily':
        button_template = TemplateSendMessage(
            alt_text='Button alt text',
            template=ButtonsTemplate(
                text="please select a category",
                title="daily input start",
                image_size="cover",
                thumbnail_image_url="https://www.actioned.com/wp-content/uploads/2018/03/daily-action-list.png",
                actions=[
                    {
                        "type": "message",
                        "label": "reading",
                        "text": "1"
                    },
                    {
                        "type": "message",
                        "label": "exercise",
                        "text": "2"
                    },
                    {
                        "type": "message",
                        "label": "coding",
                        "text": "3"
                    },
                    {
                        "type": "message",
                        "label": "english",
                        "text": "4"
                    }
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token, button_template)

        @handler.add(MessageEvent, message=TextMessage)
        def handle_button(event):
            print(event)
            category = event.message.text
            if category in ["1","2","3","4"]:
                confirm_template = ConfirmTemplate(
                    text='please select am or pm?', 
                    actions=[
                        MessageTemplateAction(label='AM', text='am'),
                        MessageTemplateAction(label='PM', text='pm'),
                    ]
                )
                template_message = TemplateSendMessage(
                    alt_text='Confirm alt text', template=confirm_template)
                line_bot_api.reply_message(
                    event.reply_token, template_message)

                @handler.add(MessageEvent, message=TextMessage)
                def handle_confirm(event):
                    print(event)
                    am_pm = event.message.text
                    if am_pm in ["am","pm"]:
                        line_bot_api.reply_message(
                            event.reply_token, TextSendMessage(text='please input time'))

                        @handler.add(MessageEvent, message=TextMessage)
                        def handle_text(event):
                            print(event)
                            category_time = event.message.text
                            if(category_time.isdigit()):
                                dt_now = datetime.datetime.now()
                                source_to_update = {
                                    "date" : dt_now.strftime('%Y-%m-%d'),
                                    "category" : int(category),
                                    "time" : int(category_time),
                                    "am_pm" : am_pm 
                                }

                                index_id = dt_now.strftime('%Y%m%d') + category + am_pm
                                # catch API errors
                                try:
                                    # call the Update method
                                    response = elastic.index(
                                        index='daily',
                                        id=index_id,
                                        body=source_to_update
                                    )

                                    # print the response to screen
                                    print (response, '\n\n')
                                    if response['result'] == "updated":
                                        print ("result:", response['result'])
                                        print ("Update was a success for ID:", response['_id'])
                                        print ("New data:", source_to_update)
                                    else:
                                        print ("result:", response['result'])
                                        print ("Response failed:", response['_shards']['failed'])
                                except Exception as err:
                                    print ('Elasticsearch API error:', err)

                                time.sleep(1)
                                result = elastic.search(
                                    index='daily',
                                    body={'query': {'match': {'date': dt_now.strftime('%Y-%m-%d')}}})
                                hits = result['hits']['total']['value']
                                result_hits = 'ヒット数 : ' + str(hits)

                                line_bot_api.reply_message(
                                    event.reply_token,
                                    TextSendMessage(text=result_hits))
                                return
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=req_message))
if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
