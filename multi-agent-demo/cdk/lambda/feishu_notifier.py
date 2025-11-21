import json
import urllib3
import os

def lambda_handler(event, context):
    """Send notification to Feishu webhook"""
    
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'FEISHU_WEBHOOK_URL not configured'})
        }
    
    message = event.get('message', 'AIOps Investigation Update')
    title = event.get('title', 'AIOps Alert')
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": message,
                        "tag": "lark_md"
                    }
                }
            ],
            "header": {
                "title": {
                    "content": title,
                    "tag": "plain_text"
                }
            }
        }
    }
    
    http = urllib3.PoolManager()
    try:
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Notification sent successfully',
                'feishu_response': response.status
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
