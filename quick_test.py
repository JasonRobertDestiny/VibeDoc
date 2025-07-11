import requests

# 测试API功能
def test_generate():
    API_KEY = "sk-eeqxcykxvmomeunmpbbgdsqgvrxqksyapauxzexphsiflgsy"
    API_URL = "https://api.siliconflow.cn/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [{"role": "user", "content": "请简单介绍一下Python，不超过100字"}],
        "max_tokens": 200,
        "temperature": 0.7,
        "stream": False
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print("✅ API测试成功")
            print(f"回复: {content}")
        else:
            print(f"❌ API错误: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    test_generate()
