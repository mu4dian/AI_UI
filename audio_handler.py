import os
import tempfile
import wave
import pyaudio
import threading
import speech_recognition as sr
import pyttsx3
import PyPDF2
import docx

class AudioHandler:
    """处理语音输入输出和文件文本提取"""
    
    def __init__(self):
        """初始化音频处理器"""
        # 语音识别
        self.recognizer = sr.Recognizer()
        
        # 文本到语音
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)  # 语速
        self.engine.setProperty('volume', 1.0)  # 音量
        
        # 录音相关变量
        self.is_recording = False
        self.audio_frames = []
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.temp_file = None
    
    def start_recording(self):
        """开始录音"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.audio_frames = []
        
        # 创建临时文件用于保存录音
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        # 创建录音流
        self.stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._record_callback
        )
        
        # 开始录音
        self.stream.start_stream()
    
    def _record_callback(self, in_data, frame_count, time_info, status):
        """录音回调函数"""
        self.audio_frames.append(in_data)
        return (in_data, pyaudio.paContinue)
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # 停止录音流
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        
        # 将录音数据写入临时文件
        with wave.open(self.temp_file.name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.audio_frames))
    
    def speech_to_text(self):
        """将录音转换为文本"""
        if not self.temp_file:
            return ""
            
        try:
            # 使用speech_recognition库进行语音识别
            with sr.AudioFile(self.temp_file.name) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language='zh-CN')
                return text
        except sr.UnknownValueError:
            return "无法识别语音"
        except sr.RequestError as e:
            return f"语音识别服务错误: {str(e)}"
        except Exception as e:
            return f"转换语音时出错: {str(e)}"
        finally:
            # 清理临时文件
            if os.path.exists(self.temp_file.name):
                os.unlink(self.temp_file.name)
            self.temp_file = None
    
    def text_to_speech(self, text):
        """将文本转换为语音输出"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"语音合成错误: {str(e)}")
    
    def extract_text_from_file(self, file_path):
        """从文件中提取文本内容"""
        # 获取文件扩展名
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        try:
            # 根据文件类型调用不同的提取方法
            if ext == '.txt':
                return self._extract_from_txt(file_path)
            elif ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif ext == '.docx':
                return self._extract_from_docx(file_path)
            else:
                return f"不支持的文件类型: {ext}"
        except Exception as e:
            return f"提取文本时出错: {str(e)}"
    
    def _extract_from_txt(self, file_path):
        """从txt文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试GBK
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
    
    def _extract_from_pdf(self, file_path):
        """从PDF文件提取文本"""
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            num_pages = len(pdf_reader.pages)
            
            # 读取每一页内容
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
                
                # 如果文本太长，只提取前10页
                if page_num >= 9:
                    text += "\n... (文档较长，只显示前10页) ..."
                    break
        
        return text
    
    def _extract_from_docx(self, file_path):
        """从Word文档提取文本"""
        doc = docx.Document(file_path)
        text = ""
        
        # 读取文档的段落
        for para in doc.paragraphs:
            text += para.text + "\n"
            
            # 如果文本太长，只提取部分内容
            if len(text) > 5000:
                text += "\n... (文档较长，只显示部分内容) ..."
                break
        
        return text