# 修改后的官方示例代码
import os
import json
from datetime import datetime

from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()  # 新增

#读取日志（正常）
def read_log_file(filename):
    """读取日志文件内容"""
    try:
        with open(filename,'r',encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"文件未找到：{filename}")
        return None
    except Exception as e:
        print(f"读取文件错误：{e}")
        return None

#读取日志（只读前200行）
def read_log_tail(filename, n=200):
    """只读取日志最后 n 行，避免 token 爆掉"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        return ''.join(lines[-n:])
    except Exception as e:
        print(f"读取文件失败：{e}")
        return None

#保存结果
def save_analysis_result(log_filename, analysis_result, output_dir="logs/error-log"):
    """保存分析结果到文件"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 基于原日志文件名生成结果文件名
    base_name = os.path.basename(log_filename)
    name_without_ext = os.path.splitext(base_name)[0]
    result_filename = f"{name_without_ext}_analysis.json"
    result_path = os.path.join(output_dir, result_filename)

    # 创建结果数据
    result_data = {
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_log": log_filename,
        "analysis_result": analysis_result
    }

    # 保存到文件
    try:
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 分析结果已保存到: {result_path}")
        return result_path
    except Exception as e:
        print(f"❌ 保存分析结果失败: {e}")
        return None

#1. 定义工具函数
tools = [
    {
        "type" : "function",
        "function" : {
            "name" : "read_nginx_error_log",
            "description" : "读取在logs/目录下面的Nginx错误日志文件内容",
            "parameters" : {
                "type" : "object",
                "properties":{
                    "filename":{
                        "type":"string",
                        "desctiption":"日志文件路径，例如 logs/error_log_3.log 默认 logs/error_log_3.log"
                    },
                    "lines":{
                        "type":"number",
                        "description":"读取的行数，默认200行"
                    }
                },
                "required":["filename"]
            }
        }
    }
]

#3. 实现工具调用流程
#处理工具调用响应
def handle_tool_calls(response):
    """处理工具调用响应"""
    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        #解析工具调用
        for tool_call in tool_calls:
            #函数名
            function_name = tool_call.function.name
            #函数参数（从JSON转为Python）
            function_args = json.loads(tool_call.function.arguments)

            # 添加调试信息
            print(f"📝 函数名: {function_name}")
            print(f"📝 函数参数: {function_args}")
            print(f"📝 参数类型: {type(function_args)}")
            print(f"📝 是否有filename参数: {'filename' in function_args}")
            #调用对应的工具函数
            if function_name == "read_nginx_error_log":
                #如果filename中没有传参，那么使用后面的默认日志名
                filename  = function_args.get("filename")

                if not os.path.exists(filename):
                    print(f"⚠️ 文件不存在：{filename}，将使用默认文件 logs/error_log_3.log")
                    filename = "logs/error_log_3.log"

                print(f"📝 最终使用的文件名: {filename}")
                lines = function_args.get("lines",200)
                log_content = read_log_tail(filename,lines)

                return log_content
    return None

#创建OpenAI客户端实例
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),  # 现在这个能正常工作了
    base_url="https://api.deepseek.com"
)

def analyze_nginx_logs():

    system_prompt = """
    你是一名 Nginx 运维专家。你的行为必须遵守以下规则：

    1. 当用户请求“分析 Nginx 日志 / 诊断错误日志 / 查看错误日志”等类似任务时，你必须调用工具 read_nginx_error_log —— 即使用户没有提供 filename。
    
    2. 如果用户没有提供 filename，你也不能向用户询问路径，而是必须直接触发工具调用，并在 arguments 中仅填入空参数或默认值，例如：
    {
      "filename": "logs/error.log",
      "lines": 200
    }
    
    3. 工具执行结果返回后，你才会进行分析，并输出严格 JSON：
    {
      "error_log": "...",
      "reason": "..."
    }
    
    4. 除非 DEBUG 或 SYSTEM 指令要求，否则不允许你在未调用工具的情况下直接回复内容。

    """

    #第一次调用 - 期望大模型返回工具调用响应（因为未指定具体文件）
    response = client.chat.completions.create(
        model = "deepseek-chat",
        messages = [
            {"role" : "system","content" : system_prompt},
            {"role" : "user","content":"帮我诊断nginx的错误日志"},
        ],
        tools = tools,
        stream = False
    )

    # 打印第一次响应，查看是否有工具调用
    print("第一次响应：", response.choices[0].message)
    log_content = handle_tool_calls(response)

    if(log_content):
        #第二次调用 - 提供工具调用结果给大模型
        second_response = client.chat.completions.create(
            model = "deepseek-chat",
            messages = [
                {"role" : "system","content" : system_prompt},
                {"role" : "user","content":"帮我诊断nginx的错误日志"},
                #助手角色：大模型的历史回答
                {"role" : "assistant",
                 "content" : None,
                 "tool_calls":response.choices[0].message.tool_calls},

                {"role" : "tool",
                 "content" : log_content,
                 "tool_call_id":response.choices[0].message.tool_calls[0].id
                }
            ]
        )

        final_result = second_response.choices[0].message.content
        print("分析结果：")
        print(final_result)
        save_analysis_result("error_log_1.log",final_result)
        return final_result
    else:
        #如果没有工具调用，直接使用结果
        result = response.choices[0].message.content
        print("分析结果；")
        print(result)
        save_analysis_result("error_log_2.log", result)
        return result

if __name__ == "__main__":
    analyze_nginx_logs()