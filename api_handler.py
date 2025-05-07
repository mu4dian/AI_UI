import requests
import json
import time
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