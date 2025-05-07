import requests
import json
import time
import base64
import os
from abc import ABC, abstractmethod

class AIModelAPI(ABC):
    """AI模型API的抽象基类"""

    @abstractmethod
    def generate_response(self, messages):
        """生成回复的抽象方法"""
        pass
    
    @abstractmethod
    def set_model(self, model_name):
        """设置模型的抽象方法"""
        pass

class ZhipuAI(AIModelAPI):
    """智谱AI API处理类"""
    
    def __init__(self, api_key="", model="glm-4"):
        """初始化智谱AI API"""
        self.api_key = api_key
        self.model = model
        self.api_base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        # 记录最后一次语音回复的 audio_id，用于处理未设置 audio_id 的情况
        self.last_audio_id = None
    
    def set_model(self, model_name):
        """设置模型名称"""
        self.model = model_name
        # 切换模型时重置 audio_id
        if model_name != "glm-4-voice":
            self.last_audio_id = None
    
    def generate_response(self, messages):
        """调用智谱AI API生成回复"""
        if not self.api_key:
            return "请先在设置中配置智谱AI的API密钥"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 检查是否是语音模型
        if self.model == "glm-4-voice":
            return self._generate_voice_response(messages, headers)
        
        # 格式化消息为智谱AI API所需的格式
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        data = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        try:
            response = requests.post(self.api_base_url, headers=headers, json=data)
            response_json = response.json()
            
            if response.status_code == 200:
                # 从响应中提取回复内容
                return response_json.get("choices", [{}])[0].get("message", {}).get("content", "无回复内容")
            else:
                error_message = response_json.get("error", {}).get("message", "未知错误")
                return f"API调用错误: {error_message}"
        except Exception as e:
            return f"API调用错误: {str(e)}"
    
    def _generate_voice_response(self, messages, headers):
        """调用智谱AI语音模型API生成语音回复"""
        # 格式化消息为智谱语音API所需的格式
        formatted_messages = []
        has_assistant_with_audio = False
        
        # 首先检查是否有至少一轮对话和一个带audio_id的助手消息
        for message in messages:
            if message["role"] == "assistant" and "audio_id" in message:
                has_assistant_with_audio = True
                break
        
        for message in messages:
            if message["role"] == "user":
                # 用户消息可能包含文本或语音
                if message.get("audio_file"):
                    # 如果包含语音文件路径，进行语音输入
                    audio_file = message["audio_file"]
                    try:
                        with open(audio_file, "rb") as f:
                            audio_data = base64.b64encode(f.read()).decode("utf-8")
                        
                        # 确保文本内容不为空，如果为空则提供默认值
                        text_content = message["content"]
                        if not text_content or text_content.strip() == "":
                            text_content = "请处理这段语音"
                        
                        content = [
                            {
                                "type": "text",
                                "text": text_content
                            },
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_data,
                                    "format": "wav"
                                }
                            }
                        ]
                    except Exception as e:
                        return f"处理语音文件时出错: {str(e)}"
                else:
                    # 纯文本输入，确保文本不为空
                    text_content = message["content"]
                    if not text_content or text_content.strip() == "":
                        text_content = "您好，请回答我的问题"
                    
                    content = [
                        {
                            "type": "text",
                            "text": text_content
                        }
                    ]
                
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
            elif message["role"] == "assistant":
                if "audio_id" in message:
                    # 使用audio_id维持对话
                    formatted_messages.append({
                        "role": "assistant",
                        "audio": {
                            "id": message["audio_id"]
                        }
                    })
                    # 更新最后一个有效的 audio_id
                    self.last_audio_id = message["audio_id"]
                elif self.last_audio_id and has_assistant_with_audio:
                    # 如果没有指定audio_id但有上一次的audio_id，使用上一次的
                    formatted_messages.append({
                        "role": "assistant",
                        "audio": {
                            "id": self.last_audio_id
                        }
                    })
                else:
                    # 首次对话，没有audio_id，使用文本格式
                    # 确保content不为空
                    content = message.get("content", "")
                    if not content or content.strip() == "":
                        content = "我很乐意帮助您"
                    formatted_messages.append({
                        "role": "assistant",
                        "content": content
                    })
            else:
                # 其他角色消息，如system
                formatted_messages.append({
                    "role": message["role"],
                    "content": message["content"] if message.get("content") else ""
                })
        
        data = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        try:
            response = requests.post(self.api_base_url, headers=headers, json=data)
            response_json = response.json()
            
            if response.status_code == 200:
                # 从响应中提取回复内容和语音
                reply = response_json.get("choices", [{}])[0].get("message", {})
                text_content = reply.get("content", "无回复内容")
                
                # 获取语音数据
                audio = reply.get("audio", {})
                audio_data = audio.get("data")
                audio_id = audio.get("id")
                
                # 更新最后一个有效的 audio_id
                if audio_id:
                    self.last_audio_id = audio_id
                
                # 如果有语音数据，保存到临时文件
                audio_file = None
                if audio_data:
                    try:
                        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
                        if not os.path.exists(temp_dir):
                            os.makedirs(temp_dir)
                        
                        audio_file = os.path.join(temp_dir, f"{audio_id}.wav")
                        with open(audio_file, "wb") as f:
                            f.write(base64.b64decode(audio_data))
                    except Exception as e:
                        print(f"保存语音文件时出错: {str(e)}")
                
                return {
                    "text": text_content,
                    "audio_file": audio_file,
                    "audio_id": audio_id
                }
            else:
                error_message = response_json.get("error", {}).get("message", "未知错误")
                return f"API调用错误: {error_message}"
        except Exception as e:
            return f"API调用错误: {str(e)}"

class DeepseekAI(AIModelAPI):
    """Deepseek AI API处理类"""
    
    def __init__(self, api_key="", model="deepseek-chat"):
        """初始化Deepseek AI API"""
        self.api_key = api_key
        self.model = model
        self.api_base_url = "https://api.deepseek.com/v1/chat/completions"
    
    def set_model(self, model_name):
        """设置模型名称"""
        self.model = model_name
    
    def generate_response(self, messages):
        """调用Deepseek AI API生成回复"""
        if not self.api_key:
            return "请先在设置中配置Deepseek的API密钥"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 格式化消息为Deepseek API所需的格式
        formatted_messages = []
        for message in messages:
            formatted_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        data = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_base_url, headers=headers, json=data)
            response_json = response.json()
            
            if response.status_code == 200:
                # 从响应中提取回复内容
                return response_json.get("choices", [{}])[0].get("message", {}).get("content", "无回复内容")
            else:
                error_message = response_json.get("error", {}).get("message", "未知错误")
                return f"API调用错误: {error_message}"
        except Exception as e:
            return f"API调用错误: {str(e)}"


# 如果直接运行此文件，执行简单的API测试
if __name__ == "__main__":
    # 尝试从config.json加载API密钥
    api_key = ""
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("zhipu_api_key", "")
    except Exception as e:
        print(f"加载配置时出错: {str(e)}")
    
    # 初始化智谱AI
    zhipu_ai = ZhipuAI(api_key=api_key)
    
    # 检查API密钥是否有效
    if not api_key:
        print("错误: 未找到智谱AI API密钥，请在config.json文件中配置。")
    else:
        print(f"已找到API密钥: {api_key[:8]}...{api_key[-4:]}")
        
        # 测试文本模型
        print("\n测试智谱AI文本模型 (GLM-4)...")
        response = zhipu_ai.generate_response([
            {"role": "user", "content": "你好，请做个自我介绍。"}
        ])
        print(f"模型回复: {response}\n")
        
        # 如果想测试语音模型，需要有音频文件
        print("API处理器测试完成。要测试完整功能，请运行app.py。")