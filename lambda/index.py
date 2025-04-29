# lambda/index.py
import json
import os
import re  # 正規表現モジュールをインポート
import urllib.request
import urllib.error

FASTAPI_URL = "https://38ac-106-180-171-177.ngrok-free.app".rstrip("/")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # Cognito 認証情報
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディ解析
        body             = json.loads(event.get("body", "{}"))
        message          = body.get("message", "")
        max_new_tokens   = body.get("max_new_tokens", 512)
        do_sample        = body.get("do_sample", True)
        temperature      = body.get("temperature", 0.7)
        top_p            = body.get("top_p", 0.9)

        if not message:
            raise ValueError("`message` field is required")

        # ここで生成パラメータも含める
        payload = {
            "prompt":         message,
            "max_new_tokens": max_new_tokens,
            "do_sample":      do_sample,
            "temperature":    temperature,
            "top_p":          top_p
        }
        data = json.dumps(payload).encode("utf-8")

        url = FASTAPI_URL + "/generate"
        print("Calling FastAPI endpoint:", url, "with payload:", payload)

        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode("utf-8")
            print("FastAPI response body:", resp_body)
            result = json.loads(resp_body)

        assistant_response = result.get("generated_text")
        response_time      = result.get("response_time")

        if assistant_response is None:
            raise RuntimeError("FastAPI did not return `generated_text`")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type":                "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,"
                    "X-Api-Key,X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success":       True,
                "response":      assistant_response,
                "response_time": response_time
            })
        }

    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.reason)
        return {
            "statusCode": e.code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error":   f"HTTP error calling FastAPI: {e.code} {e.reason}"
            })
        }

    except Exception as e:
        print("Error in lambda_handler:", str(e))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type":                "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,"
                    "X-Api-Key,X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error":   str(e)
            })
        }

