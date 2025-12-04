# test_env.py
from dotenv import load_dotenv
import os

load_dotenv()

print("测试环境变量加载...")
print(f"DEEPSEEK_API_KEY 是否存在: {'是' if os.getenv('DEEPSEEK_API_KEY') else '否'}")
print(f"密钥前10位: {os.getenv('DEEPSEEK_API_KEY', '未找到')[:10]}...")