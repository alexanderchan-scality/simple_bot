import os
import time
import json
import httplib
import urllib
import base64
import logging

from slackclient import SlackClient
from xml.dom import minidom

logger = logging.getLogger('root')
SENTIMENT_KEY = os.environ.get('SENTIMENT_KEY')
QNA_KEY = os.environ.get('QNA_KEY')
TRANS_KEY = os.environ.get('TRANS_KEY')
FILTER_KEY = os.environ.get('FILTER_KEY')
KB_ID = os.environ.get('KB_ID')

def get_token():
    '''
    Performs the request to get token for translation
    '''
    logger.info("Getting token")
    header = {}
    body = {}
    params = urllib.urlencode({
        'Subscription-Key': TRANS_KEY
    })
    conn = httplib.HTTPSConnection(
        'api.cognitive.microsoft.com')
    try:
        conn.request("POST", 
                     "/sts/v1.0/issueToken?%s"
                     % params, body, header)
        response = conn.getresponse()
        data = response.read()
        logger.info("Result: %s" % data)
        if response.status == 200:
            resp = data
        else:
            resp = None
    except:
        logger.error("Something went wrong")
        resp = None
    finally:
        logger.debug("Connection closed")
        conn.close()
    return resp

def check_language(command):
    '''
    Check if the message language
    '''
    logger.info("Requesting detect")
    token = get_token()
    if token:
        header = {
            'Content-Type': 'application/xml',
            'Authorization': 'Bearer %s' % token
        }
        body = {}
        params = urllib.urlencode({
            'text': unicode(command).encode('utf-8'),
        })
        conn = httplib.HTTPSConnection(
            'api.microsofttranslator.com')
        try:
            conn.request("GET",
                         "/v2/http.svc/Detect?%s"
                         % params, body, header)
            response = conn.getresponse()
            data = response.read()
            logger.info("Result: %s" % data)
            if response.status == 200:
                result = minidom.parseString(data)
                line = result.getElementsByTagName('string')
                resp = line[0].firstChild.data
            else:
                resp = None
        except:
            logger.error("Something went wrong")
            resp = None
        finally:
            logger.debug("Connection closed")
            conn.close()
        return token, resp
    else:
        logger.error("Unable to request token.")
        return None, None

def translate_req(token, command, lang_in, lang_out='en'):
    logger.info("Requesting translation")
    if token:
        header = {
            'Content-Type': 'application/xml',
            'Authorization': 'Bearer %s' % token
        }
        body = {}
        params = urllib.urlencode({
            # 'text': command,
            'text': unicode(command).encode('utf-8'),
            'from': lang_in,
            'to': lang_out
        })
        conn = httplib.HTTPSConnection(
            'api.microsofttranslator.com')
        params = params.replace('+', '%20')
        try:
            conn.request("GET",
                         "/v2/http.svc/Translate?%s"
                         % params, body, header)
            response = conn.getresponse()
            data = response.read()
            logger.info("Result: %s" % data)
            if response.status == 200:
                result = minidom.parseString(data)
                line = result.getElementsByTagName('string')
                resp = line[0].firstChild.data
            else:
                resp = None
        except:
            logger.error("Something went wrong")
            resp = None
        finally:
            logger.debug("Connection closed")
            conn.close()
        return resp
    else:
        logger.error("Unable to request token.")
        return None

def filter_req(command, lang_in='eng'):
    logger.info("Performing filtering")
    header = {
        'Content-Type': 'text/plain',
        'Ocp-Apim-Subscription-Key': FILTER_KEY
    }
    params = urllib.urlencode({
        'language': lang_in
    })
    conn = httplib.HTTPSConnection('westus.api.cognitive.microsoft.com')
    try:
        conn.request("POST",
                     "/contentmoderator/moderate/v1.0/ProcessText/Screen/?%s"
                     % params, command, header)
        response = conn.getresponse()
        data = response.read()
        logger.info("Result: %s" % data)
        data = json.loads(data)
        if response.status == 200:
            term_list = data['Terms']
            print term_list
            if term_list and len(term_list) > 0:
                resp = 1
            else:
                resp = 0
        else:
            resp = -1
    except:
        logger.error("Something went wrong")
        resp = -1
    finally:
        logger.debug("Connection closed")
        conn.close()
    return resp

def qna_req(command):
    logger.info("Requesting QNA")
    header = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': QNA_KEY,}
    params = urllib.urlencode({})
    body = (
        '{'
            '"question": "%s",'
            '"top": 1'
        '}'
        % command
    )
    conn = httplib.HTTPSConnection(
        'westus.api.cognitive.microsoft.com')
    try:
        conn.request("POST", 
                     "/qnamaker/v2.0/knowledgebases/%s/generateAnswer"
                     % KB_ID, body, header)
        response = conn.getresponse()
        data = response.read()
        logger.info("Result: %s" % data)
        data = json.loads(data)
        if response.status == 200:
            resp = data['answers'][0]['answer']
        else:
            resp = data['error']['message']
    except:
        logger.error("Something went wrong")
        resp = "Unable to connect."
    finally:
        logger.debug("Connection closed")
        conn.close()
    return resp


def sentiment_req(command):
    logger.info("Requesting sentiment")
    header = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': SENTIMENT_KEY,}
    params = urllib.urlencode({})
    body = (
        '{'
            '"documents": ['
                '{'
                    '"language": "en",'
                    '"id": "0",'
                    '"text": "%s"'
                '}'
            ']'
        '}'
        % command
    )
    conn = httplib.HTTPSConnection('westus.api.cognitive.microsoft.com')
    try:
        conn.request("POST", 
                     "/text/analytics/v2.0/sentiment?%s"
                     % params, body, header)
        response = conn.getresponse()
        data = response.read()
        logger.info("Result: %s" % data)
        data = json.loads(data)
        if response.status == 200:
            sentiment = float(data['documents'][0]['score'])
            if sentiment < .4:
                resp =  ":slightly_frowning_face:"
            elif sentiment > .6:
                resp = ":smile:"
            else:
                resp = ":simple_smile:"
        else:
            resp = data['error']['message']
    except:
        logger.error("Something went wrong")
        resp = "Unable to connect."
    finally:
        logger.debug("Connection closed")
        conn.close()
    return resp


