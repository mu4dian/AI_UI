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
    
    def set_model(self, model_name):
        """设置模型名称"""
        self.model = model_name
    
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
        for message in messages:
            if message["role"] == "user":
                # 用户消息可能包含文本或语音
                if message.get("audio_file"):
                    # 如果包含语音文件路径，进行语音输入
                    audio_file = message["audio_file"]
                    try:
                        with open(audio_file, "rb") as f:
                            audio_data = base64.b64encode(f.read()).decode("utf-8")
                        
                        content = [
                            {
                                "type": "text",
                                "text": message["content"]
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
                    # 纯文本输入
                    content = [
                        {
                            "type": "text",
                            "text": message["content"]
                        }
                    ]
                
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
            elif message["role"] == "assistant" and "audio_id" in message:
                # 如果是助手的语音消息，使用audio_id维持对话
                formatted_messages.append({
                    "role": "assistant",
                    "audio": {
                        "id": message["audio_id"]
                    }
                })
            else:
                # 普通的助手消息
                formatted_messages.append({
                    "role": "user" if message["role"] == "user" else "assistant",
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
                # 从响应中提取回复内容和语音
                reply = response_json.get("choices", [{}])[0].get("message", {})
                text_content = reply.get("content", "无回复内容")
                
                # 获取语音数据
                audio = reply.get("audio", {})
                audio_data = audio.get("data")
                audio_id = audio.get("id")
                
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

# 扩展支持的API，只需继承AIModelAPI并实现相应方法
# 例如: class BaiduAI(AIModelAPI):
#           ...