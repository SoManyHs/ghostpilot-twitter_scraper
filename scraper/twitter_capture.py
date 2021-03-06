#!/usr/bin/env python3

from time import sleep
from os import getenv
from ssm import SSM
import twitter
import json


class TwitterCapture(object):

    def __init__(self, woe_id='23424977'):
        self.woe_id = getenv('WORLD_ID') or woe_id
        self.since_date = getenv('SINCE_DATE') or '2020-10-26'
        self.twitter_term = getenv('TWITTER_KEYWORD') or '#awscopilot'
        self.param_name = getenv('CHECKPOINT_PARAMETER_NAME')
        self.api = self.instantiate_api()

    def instantiate_api(self):
        consumer_key, consumer_secret, access_token, access_token_secret = getenv('TWITTER_CONSUMER_API_KEY'), getenv('TWITTER_CONSUMER_API_SECRET'),\
        getenv('TWITTER_ACCESS_TOKEN'), getenv('TWITTER_ACCESS_TOKEN_SECRET')
        return twitter.Api(consumer_key=consumer_key,
                           consumer_secret=consumer_secret,
                           access_token_key=access_token,
                           access_token_secret=access_token_secret,
                           tweet_mode='extended',
                           sleep_on_rate_limit=False)

    def get_trends(self, woe_id):
        return self.api.GetTrendsWoeid(woeid=woe_id)
    
    def search(self, since_date=None, result_type='recent', count=100, include_entities=False, last_item=None, retries=0):
        print('Searching twitter for term \'{}\', since date of \'{}\', and since last tweet id of \'{}\''.format(self.twitter_term, since_date, last_item))
        try:
            if last_item is not None: last_item = int(last_item)
            return self.api.GetSearch(term=self.twitter_term, result_type=result_type, count=count, include_entities=include_entities, since=since_date, since_id=last_item)
        except Exception as e:
            # Backoff with rate limit
            print(e)
            print('WARNING: backing off, hit rate limit. Counter == {}'.format(retries))
            retries = retries + 1
            sleep(2 ** retries)
            self.search(since_date=since_date, last_item=last_item, retries=retries)
            
    def parse_tweet(self, raw_data):
        retweet_data = raw_data.retweeted_status
        return_json = json.dumps({
            'id': str(raw_data.id),
            'username': str(raw_data.user.screen_name),
            'tweet_content': str(raw_data.full_text),
            'metadata': {
                'media': str(raw_data.media),
                'hashtags': str(raw_data.hashtags),
                'created_date': str(raw_data.created_at),
                'retweet_data': str(raw_data.retweeted_status)
            }
        })
        if getenv('DEBUG'):
            print("Payload to ship to API: {}".format(return_json))
        return return_json
        
    def get_parameter(self):
        parameter = SSM().get_parameter(self.param_name, None)['Parameter']['Value']
        if parameter == 'None': parameter = None
        return parameter
        
    def main(self):
        checkpoint_value = self.get_parameter()
        print("CHECKPOINT_VALUE: {}".format(checkpoint_value))
        results = self.search(last_item=checkpoint_value)
        result_list = list()
        for tweet in results:
            if getenv('DEBUG'):
                print('RAW TWEET DATA: {}'.format(self.parse_tweet(raw_data=tweet)))
            result_list.append(self.parse_tweet(raw_data=tweet))
            
        return result_list


if __name__ == '__main__':
    TwitterCapture().main()