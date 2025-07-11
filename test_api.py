import os
import requests
import json

# 设置API密钥
API_KEY = "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

def test_api():
    """测试API连接"""
    print("🧪 测试Silicon Flow API连接...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": "请简单介绍一下自己，用中文回答，不超过50字。"
            }
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print("✅ API测试成功！")
            print(f"回复: {content}")
            return True
        else:
            print(f"❌ API测试失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API测试异常: {e}")
        return False

if __name__ == "__main__":
    test_api()
