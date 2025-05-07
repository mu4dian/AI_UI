import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import os
import json
import time
from api_handler import ZhipuAI, DeepseekAI
from audio_handler import AudioHandler

class AIAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 助手")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 设置主题颜色
        self.bg_color = "#f5f5f5"
        self.accent_color = "#4a6fa5"
        self.text_color = "#333333"
        
        # 创建并配置样式
        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TButton", background=self.accent_color, foreground="white", padding=6)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        
        # 设置API实例
        self.zhipu_ai = ZhipuAI()
        self.deepseek_ai = DeepseekAI()
        self.current_api = self.zhipu_ai  # 默认使用智谱AI
        
        # 音频处理
        self.audio_handler = AudioHandler()
        
        # 对话历史记录
        self.conversation_history = []
        
        # 创建UI
        self.create_widgets()
        
        # 加载配置
        self.load_config()
    
    def create_widgets(self):
        # 主界面框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 模型选择区域
        model_frame = ttk.LabelFrame(control_frame, text="模型选择")
        model_frame.pack(side=tk.LEFT, padx=5)
        
        # 模型选择下拉菜单
        self.model_var = tk.StringVar(value="智谱AI-GLM-4")
        model_options = [
            "智谱AI-GLM-4", 
            "智谱AI-GLM-3-Turbo", 
            "Deepseek-Coder", 
            "Deepseek-Chat"
        ]
        model_menu = ttk.OptionMenu(model_frame, self.model_var, model_options[0], *model_options, command=self.change_model)
        model_menu.pack(padx=5, pady=5)
        
        # 输入/输出模式选择区域
        io_frame = ttk.LabelFrame(control_frame, text="输入/输出模式")
        io_frame.pack(side=tk.LEFT, padx=5)
        
        # 语音输入开关
        self.voice_input_var = tk.BooleanVar(value=False)
        voice_input_check = ttk.Checkbutton(io_frame, text="语音输入", variable=self.voice_input_var)
        voice_input_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 语音输出开关
        self.voice_output_var = tk.BooleanVar(value=False)
        voice_output_check = ttk.Checkbutton(io_frame, text="语音输出", variable=self.voice_output_var)
        voice_output_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # API 设置按钮
        settings_button = ttk.Button(control_frame, text="API设置", command=self.open_settings)
        settings_button.pack(side=tk.RIGHT, padx=5)
        
        # 清空按钮
        clear_button = ttk.Button(control_frame, text="清空对话", command=self.clear_conversation)
        clear_button.pack(side=tk.RIGHT, padx=5)
        
        # 对话区域
        conversation_frame = ttk.Frame(main_frame)
        conversation_frame.pack(fill=tk.BOTH, expand=True)
        
        # 对话显示区域
        self.conversation_text = scrolledtext.ScrolledText(conversation_frame, wrap=tk.WORD, bg="#ffffff", font=("Microsoft YaHei", 10))
        self.conversation_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.conversation_text.config(state=tk.DISABLED)
        
        # 底部输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 文件上传按钮
        upload_button = ttk.Button(input_frame, text="上传文件", command=self.upload_file)
        upload_button.pack(side=tk.LEFT, padx=5)
        
        # 开始语音输入按钮
        self.voice_button_text = tk.StringVar(value="开始语音")
        self.voice_button = ttk.Button(input_frame, textvariable=self.voice_button_text, command=self.toggle_voice_input)
        self.voice_button.pack(side=tk.LEFT, padx=5)
        
        # 文本输入区域
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=3, font=("Microsoft YaHei", 10))
        self.input_text.pack(fill=tk.X, expand=True, padx=5, pady=5, side=tk.LEFT)
        
        # 发送按钮
        send_button = ttk.Button(input_frame, text="发送", command=self.send_message)
        send_button.pack(side=tk.RIGHT, padx=5)
        
        # 绑定回车键发送消息
        self.input_text.bind("<Control-Return>", lambda event: self.send_message())
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def change_model(self, selection):
        """更改当前使用的AI模型"""
        if "智谱AI" in selection:
            self.current_api = self.zhipu_ai
            if "GLM-4" in selection:
                self.zhipu_ai.set_model("glm-4")
            else:
                self.zhipu_ai.set_model("glm-3-turbo")
        elif "Deepseek" in selection:
            self.current_api = self.deepseek_ai
            if "Coder" in selection:
                self.deepseek_ai.set_model("deepseek-coder")
            else:
                self.deepseek_ai.set_model("deepseek-chat")
        
        self.status_var.set(f"已切换到 {selection}")
    
    def send_message(self):
        """发送消息到AI模型并获取回复"""
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        # 清空输入框
        self.input_text.delete("1.0", tk.END)
        
        # 在对话框中添加用户消息
        self.add_message("用户", user_input)
        
        # 更新状态
        self.status_var.set("正在生成回复...")
        
        # 在新线程中发送请求以避免阻塞UI
        threading.Thread(target=self.process_request, args=(user_input,), daemon=True).start()
    
    def process_request(self, user_input):
        """处理AI请求的线程"""
        try:
            # 将消息添加到历史记录
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # 发送请求给AI
            response = self.current_api.generate_response(self.conversation_history)
            
            # 将AI的回复添加到历史记录
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # 在对话框中显示回复
            self.add_message("AI 助手", response)
            
            # 如果启用了语音输出，将回复转换为语音
            if self.voice_output_var.get():
                threading.Thread(target=self.audio_handler.text_to_speech, args=(response,), daemon=True).start()
            
            # 更新状态
            self.status_var.set("回复完成")
        except Exception as e:
            error_message = f"生成回复时出错: {str(e)}"
            messagebox.showerror("错误", error_message)
            self.status_var.set("错误")
            
    def add_message(self, sender, message):
        """将消息添加到对话框"""
        self.conversation_text.config(state=tk.NORMAL)
        
        # 添加发送者信息
        self.conversation_text.insert(tk.END, f"\n{sender}: ", "sender")
        
        # 添加消息内容
        self.conversation_text.insert(tk.END, f"{message}\n", "message")
        
        # 应用标签样式
        self.conversation_text.tag_config("sender", foreground=self.accent_color, font=("Microsoft YaHei", 10, "bold"))
        self.conversation_text.tag_config("message", foreground=self.text_color, font=("Microsoft YaHei", 10))
        
        # 滚动到底部
        self.conversation_text.see(tk.END)
        self.conversation_text.config(state=tk.DISABLED)
    
    def toggle_voice_input(self):
        """切换语音输入状态"""
        if self.voice_button_text.get() == "开始语音":
            self.voice_button_text.set("停止语音")
            self.status_var.set("正在录音...")
            
            # 在新线程中启动录音
            threading.Thread(target=self.record_audio, daemon=True).start()
        else:
            self.voice_button_text.set("开始语音")
            self.status_var.set("录音已停止，正在处理...")
            self.audio_handler.stop_recording()
    
    def record_audio(self):
        """录制音频并转换为文本"""
        # 开始录音
        self.audio_handler.start_recording()
        
        # 等待录音停止
        while self.audio_handler.is_recording:
            time.sleep(0.1)
        
        # 将录音转换为文本
        text = self.audio_handler.speech_to_text()
        
        if text:
            # 将转换后的文本添加到输入框
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", text)
            self.status_var.set("语音已转换为文本")
        else:
            self.status_var.set("语音转换失败")
    
    def upload_file(self):
        """上传文件处理"""
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=(
                ("文本文件", "*.txt"), 
                ("PDF文件", "*.pdf"),
                ("Word文件", "*.docx"),
                ("所有文件", "*.*")
            )
        )
        
        if not file_path:
            return
            
        try:
            file_content = self.audio_handler.extract_text_from_file(file_path)
            if file_content:
                # 将文件内容添加到输入框
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", f"文件内容:\n{file_content}")
                self.status_var.set(f"已加载文件: {os.path.basename(file_path)}")
            else:
                self.status_var.set("无法提取文件内容")
        except Exception as e:
            messagebox.showerror("文件处理错误", str(e))
            self.status_var.set("文件处理错误")
    
    def open_settings(self):
        """打开API设置对话框"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("API设置")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 智谱AI设置
        zhipu_frame = ttk.LabelFrame(settings_window, text="智谱AI设置")
        zhipu_frame.pack(fill=tk.X, padx=10, pady=5, ipadx=5, ipady=5)
        
        ttk.Label(zhipu_frame, text="API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.zhipu_key_entry = ttk.Entry(zhipu_frame, width=30)
        self.zhipu_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.zhipu_key_entry.insert(0, self.zhipu_ai.api_key)
        
        # Deepseek设置
        deepseek_frame = ttk.LabelFrame(settings_window, text="Deepseek设置")
        deepseek_frame.pack(fill=tk.X, padx=10, pady=5, ipadx=5, ipady=5)
        
        ttk.Label(deepseek_frame, text="API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.deepseek_key_entry = ttk.Entry(deepseek_frame, width=30)
        self.deepseek_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.deepseek_key_entry.insert(0, self.deepseek_ai.api_key)
        
        # 保存按钮
        save_button = ttk.Button(settings_window, text="保存", command=lambda: self.save_settings(settings_window))
        save_button.pack(pady=10)
    
    def save_settings(self, window):
        """保存API设置"""
        self.zhipu_ai.api_key = self.zhipu_key_entry.get()
        self.deepseek_ai.api_key = self.deepseek_key_entry.get()
        
        # 保存配置到文件
        config = {
            "zhipu_api_key": self.zhipu_ai.api_key,
            "deepseek_api_key": self.deepseek_ai.api_key
        }
        
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("成功", "设置已保存")
            window.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时出错: {str(e)}")
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                self.zhipu_ai.api_key = config.get("zhipu_api_key", "")
                self.deepseek_ai.api_key = config.get("deepseek_api_key", "")
        except Exception as e:
            print(f"加载配置时出错: {str(e)}")
    
    def clear_conversation(self):
        """清空对话历史"""
        self.conversation_history = []
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.delete("1.0", tk.END)
        self.conversation_text.config(state=tk.DISABLED)
        self.status_var.set("对话已清空")

def main():
    root = tk.Tk()
    app = AIAssistantApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()