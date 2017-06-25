import os
import time
import signal
import base64
import logging

from slackclient import SlackClient

import log
import req

logger = log.configure_log('root')
BOT_NAME = 'marvin'
BOT_ID = os.environ.get('BOT_ID')
AT_BOT = '<@' + BOT_ID + '>'
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))



def direct_handler(message):
    '''
    Calls for Azure QnA request.
    '''
    response = req.qna_req(message['text'])
    if response == "open_sesame":
        os.system("curl http://127.0.0.1:5000/open")
        slack_client.api_call("chat.postMessage", channel=message['channel'],
                              text="Come on in.", as_user=True)
    elif response == "No good match found in the KB":
        response = "Sorry, can't help you with that. Please try rephrasing the question"
        slack_client.api_call("chat.postMessage", channel=message['channel'],
                              text=response, as_user=True)
    else:
        if not response:
            response = "Unable to pull answer from knowledge base."
        slack_client.api_call("chat.postMessage", channel=message['channel'],
                              text=response, as_user=True)

def sentiment_handler(message):
    '''
    Calls for Azure sentiment request.
    response will be sad, ok, happy(or equivalent emojis) and error message
    if something went wrong with the request.
    '''
    response = req.sentiment_req(message['text'])
    if not response:
        response = "Unable to perform sentiment analysis."
    slack_client.api_call("chat.postMessage", channel=message['channel'],
                          text=response, as_user=True)

def translate_handler(token, message, lang_in, lang_out='en'):
    '''
    Performs languanges from all languages to english
    '''
    result = req.translate_req(token, message['text'], lang_in, lang_out)
    if not result:
        response = "Unable to perform translation."
    else:
        response = ("I have detected that a message was not in english."
                    " Here's the translation:\n")
        response += result
    slack_client.api_call("chat.postMessage", channel=message['channel'],
                          text=response, as_user=True)

def perform_filtering(message):
    '''
    Removes bad texts and replaces with a safe message
    U5YJPQDQ9
    ''' 
    ts = message['ts']
    channel = message['channel']
    response = ("I sense a disturbance in the force.:disappointed:\n"
                "<@staff> has been notified")
    slack_client.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)

def parse_slack_output(slack_rtm_output):
    '''
    Parses through entries and does something with them.
    If @<BOT_ID> occurs anywhere in the sentence. It is intepreted as a
    QnA request. Otherwise, the bot will just measure the sentiment. 
    '''
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output:
                if AT_BOT in output['text']:
                    output['text'] = output['text'].replace(AT_BOT, '')
                    return True, output
                else:
                    if output['user'] != BOT_ID:
                        return False, output 
    return None, None


def ctrl_c_handler(signum, frame):
    print("Turning off %s" % BOT_NAME)
    exit(1)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_c_handler)
    READ_WEBSOCKET_DELAY = .2
    if slack_client.rtm_connect():
        while True:
            try:
                direct, message = (
                    parse_slack_output(slack_client.rtm_read()))
                if message and message['text'] and message['channel']:
                    token, lang = req.check_language(message['text'])
                    if token and lang == 'en':
                        '''
                        if token was generated and language is in en(english)
                        go with normal requests
                        '''
                        is_bad = req.filter_req(message['text'])
                        if not is_bad:
                            if direct:
                                direct_handler(message)
                            # else:
                            #     sentiment_handler(message)
                        elif is_bad > 0:
                            perform_filtering(message)
                    else:
                        '''
                        otherwise, perform a translation
                        '''
                        translated = req.translate_req(token, message['text'],
                                                       lang_in=lang)
                        is_bad = req.filter_req(translated)
                        if not is_bad:
                            translate_handler(token, message, lang)
                        elif is_bad > 0:
                            perform_filtering(message)
            except:
                pass
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print "Connection Failed."
