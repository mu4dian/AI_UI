import os
import tempfile
import wave
import pyaudio
import threading
import speech_recognition as sr
import pyttsx3
import PyPDF2
import docx
import pygame
import time
from io import BytesIO

class AudioHandler:
    """处理语音输入输出和文件文本提取"""
    
    def __init__(self):
        """初始化音频处理器"""
        # 语音识别
        self.recognizer = sr.Recognizer()
        
        # 文本到语音
        self.tts_lock = threading.RLock()  # 添加线程锁，防止多线程同时访问TTS引擎
        self.engine = None  # 不在初始化时创建引擎，改为按需创建
        
        # 录音相关变量
        self.is_recording = False
        self.audio_frames = []
        self.sample_rate = 44100  # 调整为更标准的采样率，提高兼容性
        self.channels = 1
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.temp_file = None
        
        # 初始化pygame用于播放音频
        pygame.mixer.init()
    
    def _get_tts_engine(self):
        """获取或创建TTS引擎"""
        with self.tts_lock:
            if self.engine is None:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 180)  # 语速
                self.engine.setProperty('volume', 1.0)  # 音量
            return self.engine
    
    def start_recording(self):
        """开始录音"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.audio_frames = []
        
        # 创建临时文件用于保存录音
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self.temp_file.close()  # 立即关闭文件，避免资源问题
        
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
            self.stream = None
        
        # 将录音数据写入临时文件
        try:
            with wave.open(self.temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.audio_frames))
            
            # 确保文件完全写入
            time.sleep(0.1)
        except Exception as e:
            print(f"保存音频文件时出错: {str(e)}")
    
    def get_audio_file_path(self):
        """获取录制的音频文件路径"""
        if self.temp_file and os.path.exists(self.temp_file.name):
            return self.temp_file.name
        return None
    
    def speech_to_text(self):
        """将录音转换为文本"""
        if not self.temp_file or not os.path.exists(self.temp_file.name):
            return "未找到录音文件"
        
        file_path = self.temp_file.name
            
        try:
            # 确保文件已完全写入并关闭
            time.sleep(0.2)
            
            # 创建一个新的识别器实例，避免潜在的状态问题
            recognizer = sr.Recognizer()
            
            # 尝试使用本地语音识别
            with sr.AudioFile(file_path) as source:
                audio_data = recognizer.record(source)
                
                # 首选中文识别，fallback到英文
                try:
                    text = recognizer.recognize_google(audio_data, language='zh-CN')
                    return text
                except sr.UnknownValueError:
                    try:
                        # 尝试英文识别
                        text = recognizer.recognize_google(audio_data, language='en-US')
                        return text
                    except:
                        return "无法识别语音内容"
                except sr.RequestError as e:
                    return f"语音识别服务错误: {str(e)}"
        except sr.UnknownValueError:
            return "无法识别语音"
        except sr.RequestError as e:
            return f"语音识别服务错误: {str(e)}"
        except Exception as e:
            # 保存更详细的错误信息
            error_msg = f"转换语音时出错: {str(e)}"
            print(error_msg)
            # 检查文件状态
            try:
                file_size = os.path.getsize(file_path)
                print(f"音频文件大小: {file_size} 字节")
                if file_size == 0:
                    return "录音文件为空，请重新录制"
            except:
                pass
            return error_msg
    
    def clean_temp_files(self):
        """清理临时文件"""
        if self.temp_file and os.path.exists(self.temp_file.name):
            try:
                os.unlink(self.temp_file.name)
            except Exception as e:
                print(f"删除临时文件时出错: {str(e)}")
            self.temp_file = None
    
    def text_to_speech(self, text):
        """将文本转换为语音输出，使用本地TTS引擎"""
        # 使用pygame代替pyttsx3进行语音合成，避免run loop already started的问题
        try:
            # 使用临时文件存储合成的语音
            temp_dir = os.path.join(os.path.dirname(__file__), "temp")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            temp_file = os.path.join(temp_dir, f"tts_{int(time.time())}.mp3")
            
            # 在单独的线程中运行TTS引擎，避免阻塞主线程
            def synthesize_speech():
                with self.tts_lock:
                    try:
                        engine = self._get_tts_engine()
                        engine.save_to_file(text, temp_file)
                        engine.runAndWait()
                        
                        # 等待文件写入完成
                        time.sleep(0.5)
                        
                        # 播放合成的音频文件
                        if os.path.exists(temp_file):
                            self.play_audio_file(temp_file)
                            
                            # 播放完成后删除临时文件
                            try:
                                os.unlink(temp_file)
                            except:
                                pass
                    except Exception as e:
                        print(f"语音合成错误: {str(e)}")
            
            # 启动语音合成线程
            speech_thread = threading.Thread(target=synthesize_speech)
            speech_thread.daemon = True
            speech_thread.start()
            return True
        except Exception as e:
            print(f"语音合成错误: {str(e)}")
            return False
    
    def play_audio_file(self, file_path):
        """播放音频文件"""
        if not file_path or not os.path.exists(file_path):
            print("音频文件不存在")
            return False
            
        try:
            # 使用pygame播放音频
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            return True
        except Exception as e:
            print(f"播放音频文件时出错: {str(e)}")
            return False
    
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