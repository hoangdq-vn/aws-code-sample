import urllib3 
import json
import logging
import boto3
from datetime import datetime, timedelta

http = urllib3.PoolManager() 

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 有効期限 (日)
expired_time_in = 7 #days
client = boto3.client('ssm')

# Retrieve the secret value
aws_access_key_id = client.get_parameter(Name='send_presigned_url_aws_access_key_id',WithDecryption=True)
aws_secret_access_key = client.get_parameter(Name='send_presigned_url_aws_secret_access_key',WithDecryption=True)
webhook_url = client.get_parameter(Name='send_presigned_url_webhook_url',WithDecryption=True)

session = boto3.Session(aws_access_key_id = aws_access_key_id['Parameter']['Value'], aws_secret_access_key = aws_secret_access_key['Parameter']['Value'])
s3 = session.client('s3')

def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key_name = event['Records'][0]['s3']['object']['key']

    presigned_url = s3.generate_presigned_url('get_object', Params = {'Bucket': bucket_name, 'Key': key_name}, ExpiresIn = expired_time_in*86400)

    file_name = key_name.split('/')[-1]


    expired_time = (datetime.now() + timedelta(hours=9) + timedelta(days=expired_time_in)).strftime('%Y/%m/%d, %H:%M')
    noti_time = (datetime.now() + timedelta(hours=9)).strftime('%Y/%m/%d')

    # メッセージ案
    title_text = noti_time + 'の引当て依頼レポートのダウンロードリンクです。\n'
    message = json.dumps(
        {
            'title': title_text,
            'text': 'ファイル名： {file_name}<br>URL： [ファイルダウンロードするにはここをクリックしてください]({url})<br>有効期限：{expired_time}迄<br>※有効期限後は取得できなくなります。'.format(
                file_name=file_name,
                url=presigned_url,
                expired_time=expired_time
            )
        }
    )

    # 署名付きURLをWebhookでTeamsに送信する
    encoded_msg = message.encode('utf-8')
    response = http.request('POST', webhook_url['Parameter']['Value'], body=encoded_msg)

    logger.info('Status Code: {}'.format(response.status))
    logger.info('Response: {}'.format(response.data))

    if response.status == 200 :
        logger.info('Send ' + file_name + '\'s URL successfully!')
    else :
        logger.error('An error occurred while sending the URL.')
