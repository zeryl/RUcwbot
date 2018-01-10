from discordWebhooks import *
import urllib2
import json

data = {
    'username': 'Zeryl',
    'content':  'This is a test message',
}

url = "https://discordapp.com/api/webhooks/360110323467943938/8QijtZ6nQu-iRzo2yGag75kBSATLFV_xAVdoaExJmuAKRSODdsx1wN3gm1jS7Usvezbs"

wh = Webhook (url, 'Testing Python', 'This is from Python')
wh.post()
