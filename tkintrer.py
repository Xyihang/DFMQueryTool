import http.client
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, font
from datetime import datetime, timedelta
import urllib.parse
import threading
import os
import ast
import configparser
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import logging
import traceback
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import time
import socket


class QueryStatus(Enum):
    """查询状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class QueryResult:
    """查询结果数据类"""
    status: QueryStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    cached: bool = False


class ErrorHandler:
    """统一的错误处理类"""
    
    @staticmethod
    def handle_exception(func_name: str, exception: Exception, 
                        show_ui: bool = True, log_error: bool = True) -> str:
        """统一处理异常"""
        error_msg = f"{func_name} 发生错误: {str(exception)}"
        
        if log_error:
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
        
        if show_ui:
            # 避免在主线程外显示UI错误
            try:
                if threading.current_thread() == threading.main_thread():
                    messagebox.showerror("错误", error_msg)
            except:
                pass
        
        return error_msg
    
    @staticmethod
    def safe_execute(func, *args, **kwargs):
        """安全执行函数，捕获并处理异常"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return ErrorHandler.handle_exception(func.__name__, e)


def parse_dict_like_string(s: str) -> Dict[str, Any]:
    """优化的字典字符串解析函数"""
    if not s or s == '{}':
        return {}

    s = s.strip()
    if s.startswith('{') and s.endswith('}'):
        s = s[1:-1]

    result = {}
    if not s:
        return result

    # 使用更高效的解析方法
    pairs = []
    start = 0
    in_quotes = False
    quote_char = None

    for i, char in enumerate(s):
        if char in ('"', "'") and (i == 0 or s[i - 1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
        elif char == ',' and not in_quotes:
            pairs.append(s[start:i].strip())
            start = i + 1

    if start < len(s):
        pairs.append(s[start:].strip())

    for pair in pairs:
        if not pair or ':' not in pair:
            continue

        try:
            key_part, value_part = pair.split(':', 1)
            key = key_part.strip().strip("'\"")
            value_str = value_part.strip()

            # 优化值解析
            if (value_str.startswith("'") and value_str.endswith("'")) or \
               (value_str.startswith('"') and value_str.endswith('"')):
                result[key] = ast.literal_eval(value_str)
            else:
                result[key] = ast.literal_eval(value_str)
        except (ValueError, SyntaxError):
            # 如果解析失败，使用原始字符串
            result[key] = value_part.strip()

    return result


class ThemeManager:
    def __init__(self):
        # 定义浅色和深色主题
        self.themes = {
            'light': {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'entry_bg': '#ffffff',
                'entry_fg': '#000000',
                'button_bg': '#e0e0e0',
                'button_fg': '#000000',
                'frame_bg': '#e8e8e8',
                'tab_bg': '#d0d0d0',
                'active_tab_bg': '#f0f0f0',
                'scrollbar_bg': '#d0d0d0',
                'scrollbar_handle': '#b0b0b0',
                'highlight': '#4a7aed',
                'highlight_light': '#6a8aed'
            },
            'dark': {
                'bg': '#1a1a1a',
                'fg': '#4ade80',  # 鲜艳的绿色
                'entry_bg': '#2d2d2d',
                'entry_fg': '#4ade80',  # 鲜艳的绿色
                'button_bg': '#4d4d4d',
                'button_fg': '#4ade80',  # 鲜艳的绿色
                'frame_bg': '#353535',
                'tab_bg': '#3a3a3a',
                'active_tab_bg': '#2d2d2d',
                'scrollbar_bg': '#3a3a3a',
                'scrollbar_handle': '#5a5a5a',
                'highlight': '#5a8aed',
                'highlight_light': '#7a9aed'
            }
        }
        self.current_theme = 'light'
        self.style = None
        self._widget_cache = {}  # 添加控件缓存
        self._style_cache = {}   # 添加样式缓存
    
    def initialize_style(self):
        """初始化ttk样式"""
        if self.style is None:
            self.style = ttk.Style()
        self._configure_ttk_styles()
    
    def _configure_ttk_styles(self):
        """配置所有ttk控件的样式，使用缓存优化性能"""
        theme = self.get_theme()
        theme_key = self.current_theme
        
        # 检查样式缓存
        if theme_key in self._style_cache:
            return
        
        # 配置滚动条样式
        self.style.configure(
            "Vertical.TScrollbar",
            background=theme['scrollbar_bg'],
            troughcolor=theme['scrollbar_bg'],
            arrowcolor=theme['fg'],
            bordercolor=theme['scrollbar_bg']
        )
        self.style.configure(
            "Horizontal.TScrollbar",
            background=theme['scrollbar_bg'],
            troughcolor=theme['scrollbar_bg'],
            arrowcolor=theme['fg'],
            bordercolor=theme['scrollbar_bg']
        )
        
        # 配置其他ttk控件样式
        self.style.configure(
            "TButton",
            background=theme['button_bg'],
            foreground=theme['button_fg'],
            borderwidth=1,
            relief="solid",
            padding=6
        )
        self.style.map(
            "TButton",
            background=[
                ("disabled", theme['button_bg']),
                ("active", theme['frame_bg'])
            ],
            foreground=[
                ("disabled", theme['fg']),
                ("active", theme['button_fg'])
            ]
        )
        
        self.style.configure(
            "TEntry",
            fieldbackground=theme['entry_bg'],
            foreground=theme['entry_fg']
        )
        
        self.style.configure(
            "TCombobox",
            fieldbackground=theme['entry_bg'],
            background=theme['button_bg'],
            foreground=theme['entry_fg'],
            arrowcolor=theme['fg']
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", theme['entry_bg'])],
            background=[("readonly", theme['button_bg'])],
            foreground=[("readonly", theme['entry_fg'])]
        )
        
        self.style.configure(
            "TLabel",
            background=theme['bg'],
            foreground=theme['fg']
        )
        
        self.style.configure(
            "TFrame",
            background=theme['frame_bg']
        )
        
        self.style.configure(
            "TNotebook",
            background=theme['bg']
        )
        self.style.configure(
            "TNotebook.Tab",
            background=theme['tab_bg'],
            foreground=theme['fg']
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", theme['active_tab_bg'])]
        )
        
        self.style.configure(
            "Treeview",
            background=theme['entry_bg'],
            foreground=theme['fg'],
            fieldbackground=theme['entry_bg'],
            rowheight=25
        )
        self.style.configure(
            "Treeview.Heading",
            background=theme['tab_bg'],
            foreground=theme['fg']
        )
        self.style.map(
            "Treeview",
            background=[("selected", theme['highlight'])],
            foreground=[("selected", "white")]
        )
        
        # 缓存已配置的样式
        self._style_cache[theme_key] = True
    
    def get_theme(self):
        """获取当前主题配置"""
        return self.themes[self.current_theme]
    
    def toggle_theme(self):
        """切换主题并更新样式，使用批量更新优化性能"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        
        # 清除缓存，强制重新应用主题
        self._widget_cache.clear()
        self._style_cache.clear()
        
        if self.style:
            self._configure_ttk_styles()
        return self.get_theme()
    
    def apply_theme_to_widget(self, widget, recursive=True):
        """将主题应用到指定控件及其子控件，使用缓存优化性能"""
        # 检查控件缓存
        widget_id = str(widget)
        if widget_id in self._widget_cache and self._widget_cache[widget_id] == self.current_theme:
            return
        
        theme = self.get_theme()
        
        # 应用主题到当前控件
        try:
            # 区分处理ttk控件和tk原生控件
            if isinstance(widget, ttk.Widget):
                # ttk控件通过样式设置，不要直接设置fg/bg属性
                widget_class = widget.winfo_class()
                style_map = {
                    'TButton': "TButton",
                    'TEntry': "TEntry", 
                    'TLabel': "TLabel",
                    'TCombobox': "TCombobox",
                    'TFrame': "TFrame",
                    'TNotebook': "TNotebook",
                    'Treeview': "Treeview",
                    'Vertical.TScrollbar': "Vertical.TScrollbar",
                    'Horizontal.TScrollbar': "Horizontal.TScrollbar",
                    'TCheckbutton': "TCheckbutton",
                    'TRadiobutton': "TRadiobutton"
                }
                
                if widget_class in style_map:
                    widget.configure(style=style_map[widget_class])
            else:
                # tk原生控件可以直接设置属性
                widget_name = widget.winfo_class()
                config_map = {
                    'Tk': {'bg': theme['bg']},
                    'Toplevel': {'bg': theme['bg']},
                    'Frame': {'bg': theme['bg']},
                    'Text': {'bg': theme['entry_bg'], 'fg': theme['entry_fg']},
                    'ScrolledText': {'bg': theme['entry_bg'], 'fg': theme['entry_fg']},
                    'Button': {'bg': theme['button_bg'], 'fg': theme['button_fg']},
                    'Label': {'bg': theme['bg'], 'fg': theme['fg']},
                    'Entry': {'bg': theme['entry_bg'], 'fg': theme['entry_fg']},
                    'Listbox': {'bg': theme['bg'], 'fg': theme['fg']},
                    'Scrollbar': {'bg': theme['scrollbar_bg'], 'troughcolor': theme['scrollbar_bg']},
                    'Scale': {'bg': theme['scrollbar_bg'], 'troughcolor': theme['scrollbar_bg']}
                }
                
                if widget_name in config_map and hasattr(widget, 'config'):
                    for key, value in config_map[widget_name].items():
                        if key in widget.config():
                            widget.config(**{key: value})
        except Exception as e:
            # 记录异常但继续执行，避免一个控件的错误影响整体主题应用
            self.logger.error(f"应用主题到控件 {widget.winfo_class()} 时出错: {str(e)}")
        
        # 缓存已处理的控件
        self._widget_cache[widget_id] = self.current_theme
        
        # 递归应用到所有子控件
        if recursive:
            for child in widget.winfo_children():
                self.apply_theme_to_widget(child, recursive)


class FHZDDataQueryTool:
    def __init__(self, root):
        self.root = root
        self.root.title("烽火地带数据查询工具 v3.0")
        self.root.geometry("1050x850")
        self.root.minsize(1000, 800)
        # 设置窗口图标（如果有）
        # self.root.iconbitmap("icon.ico")
        # 设置窗口在屏幕上居中
        self.root.eval('tk::PlaceWindow . center')
        
        # 启用窗口关闭确认
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 主题管理器
        self.theme_manager = ThemeManager()
        self.theme_manager.initialize_style()  # 初始化样式
        self.current_theme = self.theme_manager.get_theme()
        
        # 保存所有创建的框架引用，用于主题切换
        self.all_frames = []
        
        # 设置字体以支持中文
        self.font_config = {
            'normal': ('Microsoft YaHei UI', 10),
            'title': ('Microsoft YaHei UI', 12, 'bold'),
            'small': ('Microsoft YaHei UI', 9),
            'large': ('Microsoft YaHei UI', 14, 'bold'),
            'label': ('Microsoft YaHei UI', 10),
            'entry': ('Microsoft YaHei UI', 9),
            'button': ('Microsoft YaHei UI', 10),
            'monospace': ('Consolas', 9)  # 等宽字体用于代码和JSON显示
        }

        self.default_openid = "332908108AE3BCD62DCE9843072E00FE"
        self.default_token = "AB2D3762FEE0C5DA0D9D3B8DD867394F"
        
        # 查询状态跟踪
        self.current_query_function = None
        self.current_query_args = ()
        self.current_tab_index = 0
        self.current_query_result = None
        self.current_view_mode = "text"  # 默认视图模式

        self.operator_map = {
            "10007": "红狼",
            "10010": "威龙",
            "10011": "无名",
            "20003": "蜂医",
            "20004": "蛊",
            "30008": "牧羊人",
            "30010": "深蓝",
            "40005": "露娜",
            "40010": "骇爪",
            "40011": "银翼",
            "30009": "乌鲁鲁",
            "10012": "疾风",
            "20005": "未知干员(20005)"
        }

        self.item_mapping = {}
        
        # 用于存储配置
        self.config = {
            'timeout': 30.0,              # API请求超时时间（秒）
            'retry_count': 3,              # API请求重试次数
            'cache_expiry': 300,           # 缓存过期时间（秒）
            'auto_refresh': False,         # 是否启用自动刷新
            'refresh_interval': 60,        # 自动刷新间隔（秒）
            'show_detailed_logs': False,   # 是否显示详细日志
            'export_format': 'txt',        # 默认导出格式
            'openid': self.default_openid, # 用户OpenID
            'token': self.default_token,   # 用户Token
            'acctype': 'qc'                # 账号类型（qc:QQ, wx:微信）
        }
        
        # 初始化日志系统
        self._setup_logging()
        
        # 现在可以安全地加载物品映射，因为logger已初始化
        self.load_item_mapping('return.txt')
        
        # 用于缓存查询结果
        self.result_cache = {}
        self.cache_timestamps = {}
        
        # 自动刷新相关变量
        self.auto_refresh_timer = None
        self.setup_auto_refresh()
        
        # 设置UI界面，这会初始化所有UI变量
        self.setup_ui()
        
        # 加载配置，此时UI变量已存在
        self.load_config()

        # 定义所有可导出的模块
        self.module_definitions = {
            "昨日日报-烽火地带": {
                "fetch_func": self._get_daily_report_data,
                "fetch_args": ["sol"],
                "process_func": lambda data: self._process_daily_data(data, "sol")
            },
            "昨日日报-全面战场": {
                "fetch_func": self._get_daily_report_data,
                "fetch_args": ["mp"],
                "process_func": lambda data: self._process_daily_data(data, "mp")
            },
            "战场周报-烽火地带": {
                "fetch_func": self._get_weekly_report_data,
                "fetch_args": ["sol"],
                "extra_args": ["stat_date", "s_area"],
                "process_func": lambda data: self._process_weekly_data(data, "sol")
            },
            "战场周报-全面战场": {
                "fetch_func": self._get_weekly_report_data,
                "fetch_args": ["mp"],
                "extra_args": ["stat_date", "s_area"],
                "process_func": lambda data: self._process_weekly_data(data, "mp")
            },
            "周报队友-烽火地带": {
                "fetch_func": self._get_friend_report_data,
                "fetch_args": ["sol"],
                "extra_args": ["stat_date", "s_area"],
                "process_func": lambda data: self._process_friend_data(data, "sol")
            },
            "周报队友-全面战场": {
                "fetch_func": self._get_friend_report_data,
                "fetch_args": ["mp"],
                "extra_args": ["stat_date", "s_area"],
                "process_func": lambda data: self._process_friend_data(data, "mp")
            },
            "烽火周报": {
                "fetch_func": self._get_fire_weekly_report_data,
                "fetch_args": [],
                "extra_args": ["stat_date", "s_area"],
                "process_func": self._process_fire_weekly_data
            },
            "哈夫币资产": {
                "fetch_func": self._get_currency_data,
                "fetch_args": ["17020000010"],
                "process_func": lambda data: self._process_currency_data(data, "17020000010")
            },
            "三角券资产": {
                "fetch_func": self._get_currency_data,
                "fetch_args": ["17888808889"],
                "process_func": lambda data: self._process_currency_data(data, "17888808889")
            },
            "三角币资产": {
                "fetch_func": self._get_currency_data,
                "fetch_args": ["17888808888"],
                "process_func": lambda data: self._process_currency_data(data, "17888808888")
            },
            "每日密码": {
                "fetch_func": self._get_secret_data,
                "fetch_args": [],
                "process_func": self._process_secret_data
            },
            "特勤处状态": {
                "fetch_func": self._get_special_duty_data,
                "fetch_args": [],
                "process_func": self._process_special_duty_data
            }
        }
    
    def load_config(self):
        """加载配置文件，增强错误恢复和备份机制"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        backup_path = config_path + '.backup'
        
        # 尝试加载主配置文件
        if os.path.exists(config_path):
            try:
                config = configparser.ConfigParser()
                config.read(config_path, encoding='utf-8')
                if 'Settings' in config:
                    self.config = {
                        'timeout': config.getfloat('Settings', 'timeout', fallback=30.0),
                        'retry_count': config.getint('Settings', 'retry_count', fallback=3),
                        'theme': config.get('Settings', 'theme', fallback='light'),
                        'cache_expiry': config.getint('Settings', 'cache_expiry', fallback=300),
                        'auto_refresh': config.getboolean('Settings', 'auto_refresh', fallback=False),
                        'refresh_interval': config.getint('Settings', 'refresh_interval', fallback=60),
                        # 添加认证信息的加载
                        'openid': config.get('Settings', 'openid', fallback=self.default_openid),
                        'token': config.get('Settings', 'token', fallback=self.default_token),
                        'acctype': config.get('Settings', 'acctype', fallback='qc'),
                        'export_format': config.get('Settings', 'export_format', fallback='txt'),
                        'show_detailed_logs': config.getboolean('Settings', 'show_detailed_logs', fallback=False)
                    }
                    # 应用主题设置
                    self.theme_manager.current_theme = self.config.get('theme', 'light')
                    self.current_theme = self.theme_manager.get_theme()
                    
                    # 更新UI中的认证信息
                    self.openid_var.set(self.config['openid'])
                    self.token_var.set(self.config['token'])
                    self.acctype_var.set(self.config['acctype'])
                    
                    # 成功加载后创建备份
                    self._create_config_backup()
                    return
            except Exception as e:
                self.logger.error(f"主配置文件加载失败: {str(e)}")
                
                # 尝试从备份文件恢复
                if os.path.exists(backup_path):
                    try:
                        self.logger.info("尝试从备份文件恢复配置")
                        config = configparser.ConfigParser()
                        config.read(backup_path, encoding='utf-8')
                        # 使用备份文件内容恢复
                        with open(config_path, 'w', encoding='utf-8') as f:
                            config.write(f)
                        # 重新加载
                        self.load_config()
                        return
                    except Exception as backup_error:
                        self.logger.error(f"备份文件恢复也失败: {str(backup_error)}")
        
        # 如果主配置不存在或加载失败，使用默认配置
        self.logger.info("使用默认配置")
        self.config = {
            'timeout': 30.0,
            'retry_count': 3,
            'theme': 'light',
            'cache_expiry': 300,
            'auto_refresh': False,
            'refresh_interval': 60,
            'openid': self.default_openid,
            'token': self.default_token,
            'acctype': 'qc',
            'export_format': 'txt',
            'show_detailed_logs': False
        }
        
        # 也检查是否存在旧的认证配置文件，如果存在则迁移数据
        old_auth_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth_config.ini')
        if os.path.exists(old_auth_config):
            try:
                config = configparser.ConfigParser()
                config.read(old_auth_config, encoding='utf-8')
                if 'Auth' in config:
                    # 如果主配置中没有认证信息，则从旧配置迁移
                    if not self.config.get('openid') or self.config['openid'] == self.default_openid:
                        self.config['openid'] = config.get('Auth', 'openid', fallback=self.default_openid)
                        self.config['token'] = config.get('Auth', 'token', fallback=self.default_token)
                        self.config['acctype'] = config.get('Auth', 'acctype', fallback='qc')
                        
                        # 更新UI
                        self.openid_var.set(self.config['openid'])
                        self.token_var.set(self.config['token'])
                        self.acctype_var.set(self.config['acctype'])
                        
                        # 保存到主配置
                        self.save_config()
            except Exception as e:
                self.logger.warning(f"迁移旧认证配置失败: {str(e)}")
    
    def _create_config_backup(self):
        """创建配置文件备份"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        backup_path = config_path + '.backup'
        try:
            import shutil
            shutil.copy2(config_path, backup_path)
            self.logger.debug("配置文件备份已创建")
        except Exception as e:
            self.logger.warning(f"创建配置文件备份失败: {str(e)}")
    
    def save_config(self):
        """保存配置到文件，增强错误处理和备份机制"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
        temp_path = config_path + '.tmp'
        backup_path = config_path + '.backup'
        
        try:
            # 首先创建临时文件
            config = configparser.ConfigParser()
            config['Settings'] = {
                'timeout': str(self.config.get('timeout', 30.0)),
                'retry_count': str(self.config.get('retry_count', 3)),
                'theme': self.theme_manager.current_theme,
                'cache_expiry': str(self.config.get('cache_expiry', 300)),
                'auto_refresh': str(self.config.get('auto_refresh', False)),
                'refresh_interval': str(self.config.get('refresh_interval', 60)),
                'openid': self.config.get('openid', self.default_openid),
                'token': self.config.get('token', self.default_token),
                'acctype': self.config.get('acctype', 'qc'),
                'export_format': self.config.get('export_format', 'txt'),
                'show_detailed_logs': str(self.config.get('show_detailed_logs', False))
            }
            
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 验证临时文件
            test_config = configparser.ConfigParser()
            test_config.read(temp_path, encoding='utf-8')
            if 'Settings' not in test_config:
                raise ValueError("配置文件验证失败")
            
            # 备份原文件
            if os.path.exists(config_path):
                try:
                    import shutil
                    shutil.copy2(config_path, backup_path)
                except Exception as backup_error:
                    self.logger.warning(f"创建配置备份失败: {str(backup_error)}")
            
            # 原子替换
            import shutil
            shutil.move(temp_path, config_path)
            
            self.logger.info("配置文件保存成功")
            
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            error_msg = f"无法保存配置文件: {str(e)}\n配置文件路径: {config_path}"
            self.logger.error(error_msg)
            messagebox.showerror("配置保存错误", error_msg)
            
            # 尝试从备份恢复
            if os.path.exists(backup_path):
                try:
                    self.logger.info("尝试从备份恢复配置")
                    shutil.copy2(backup_path, config_path)
                    messagebox.showinfo("配置恢复", "配置保存失败，已从备份文件恢复")
                except Exception as restore_error:
                    self.logger.error(f"从备份恢复也失败: {str(restore_error)}")

    def load_item_mapping(self, filename):
        """加载物品ID到名称的映射"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data['data']['keywords']:
                    object_id = str(item['objectID'])
                    object_name = item['objectName']
                    self.item_mapping[object_id] = object_name
                self.logger.info(f'成功加载 {len(self.item_mapping)} 个物品映射')
            else:
                self.logger.warning(f'文件 {filename} 不存在')
        except Exception as e:
            self.logger.error(f'加载物品映射失败: {e}')

    def get_item_name(self, item_id):
        """根据物品ID获取物品名称"""
        if isinstance(item_id, (int, str)):
            str_id = str(item_id)
            return self.item_mapping.get(str_id, str_id)
        return str(item_id)

    def setup_ui(self):
        """设置用户界面，采用现代化设计风格"""
        # 设置窗口属性
        self.root.title("烽火地带数据查询工具")
        self.root.minsize(900, 700)  # 设置最小窗口大小
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=(15, 15, 15, 10))
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重，使界面可响应式扩展
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 标题和主题切换按钮区域
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 12))
        title_frame.columnconfigure(0, weight=1)
        
        # 创建标题标签
        title_label = ttk.Label(title_frame, text="烽火地带数据查询工具", font=("Microsoft YaHei", 18, "bold"))
        title_label.grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # 创建主题切换按钮
        self.theme_button = ttk.Button(title_frame, text="切换主题", command=self.toggle_theme, width=12)
        self.theme_button.grid(row=0, column=1, sticky=tk.E, padx=10)

        # 创建标签页控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)  # 添加标签切换事件

        # 创建各个标签页
        auth_frame = ttk.LabelFrame(self.notebook, text="认证设置", padding=(20, 15, 20, 15))
        daily_frame = ttk.LabelFrame(self.notebook, text="昨日日报", padding=(20, 15, 20, 15))
        weekly_frame = ttk.LabelFrame(self.notebook, text="战场周报", padding=(20, 15, 20, 15))
        friend_frame = ttk.LabelFrame(self.notebook, text="周报队友", padding=(20, 15, 20, 15))
        fire_weekly_frame = ttk.LabelFrame(self.notebook, text="烽火周报", padding=(20, 15, 20, 15))
        currency_frame = ttk.LabelFrame(self.notebook, text="货币查询", padding=(20, 15, 20, 15))
        secret_frame = ttk.LabelFrame(self.notebook, text="每日密码", padding=(20, 15, 20, 15))
        special_duty_frame = ttk.LabelFrame(self.notebook, text="特勤处状态", padding=(20, 15, 20, 15))

        # 添加标签页到notebook
        self.notebook.add(auth_frame, text="认证设置")
        self.notebook.add(daily_frame, text="昨日日报")
        self.notebook.add(weekly_frame, text="战场周报")
        self.notebook.add(friend_frame, text="周报队友")
        self.notebook.add(fire_weekly_frame, text="烽火周报")
        self.notebook.add(currency_frame, text="货币查询")
        self.notebook.add(secret_frame, text="每日密码")
        self.notebook.add(special_duty_frame, text="特勤处状态")

        # 配置所有标签页的列权重，实现统一的响应式布局
        for frame in [auth_frame, daily_frame, weekly_frame, fire_weekly_frame, currency_frame, secret_frame]:
            frame.columnconfigure(1, weight=1)
        friend_frame.columnconfigure(1, weight=1)
        friend_frame.columnconfigure(3, weight=1)

        # ===== 认证设置页面 =====
        # 输入框容器，实现更好的对齐和布局
        auth_input_frame = ttk.Frame(auth_frame)
        auth_input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # OpenID输入
        ttk.Label(auth_input_frame, text="OpenID:", font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(10, 8))
        self.openid_var = tk.StringVar(value=self.default_openid)
        openid_entry = ttk.Entry(auth_input_frame, textvariable=self.openid_var, font=self.font_config['entry'])
        openid_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(10, 8), padx=(15, 10))
        ttk.Label(auth_input_frame, text="游戏账号的唯一标识符", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(10, 8))

        # Token输入
        ttk.Label(auth_input_frame, text="Token:", font=self.font_config['label']).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.token_var = tk.StringVar(value=self.default_token)
        token_entry = ttk.Entry(auth_input_frame, textvariable=self.token_var, font=self.font_config['entry'])
        token_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=8, padx=(15, 10))
        ttk.Label(auth_input_frame, text="访问令牌", font=self.font_config['small']).grid(row=1, column=2, sticky=tk.W, pady=8)

        # 账号类型选择
        ttk.Label(auth_input_frame, text="账号类型:", font=self.font_config['label']).grid(row=2, column=0, sticky=tk.W, pady=8)
        self.acctype_var = tk.StringVar(value="qc")
        acctype_combo = ttk.Combobox(auth_input_frame, textvariable=self.acctype_var, width=15, state="readonly",
                                     font=self.font_config['entry'])
        acctype_combo['values'] = ('qc', 'wx')
        acctype_combo.grid(row=2, column=1, sticky=tk.W, pady=8, padx=(15, 10))
        ttk.Label(auth_input_frame, text="qc:QQ账号 wx:微信账号", font=self.font_config['small']).grid(row=2, column=2, sticky=tk.W, pady=8)
        
        # 保存按钮
        save_auth_btn = ttk.Button(auth_frame, text="保存认证信息", command=self.save_auth_info, width=25)
        save_auth_btn.pack(pady=10)
        save_auth_btn.configure(cursor="hand2")  # 鼠标悬停显示手形指针

        # ===== 昨日日报页面 =====
        daily_input_frame = ttk.Frame(daily_frame)
        daily_input_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(daily_input_frame, text="资源类型:", font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(10, 8))
        self.daily_resource_var = tk.StringVar(value="sol")
        daily_resource_combo = ttk.Combobox(daily_input_frame, textvariable=self.daily_resource_var, width=20,
                                            state="readonly", font=self.font_config['entry'])
        daily_resource_combo['values'] = ('sol', 'mp')
        daily_resource_combo.grid(row=0, column=1, sticky=tk.W, pady=(10, 8), padx=(15, 10))
        ttk.Label(daily_input_frame, text="sol:烽火地带 mp:全面战场", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(10, 8))

        ttk.Label(daily_input_frame, text="战区:", font=self.font_config['label']).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.daily_area_var = tk.StringVar(value="36")
        daily_area_entry = ttk.Entry(daily_input_frame, textvariable=self.daily_area_var, width=15, font=self.font_config['entry'])
        daily_area_entry.grid(row=1, column=1, sticky=tk.W, pady=8, padx=(15, 10))
        ttk.Label(daily_input_frame, text="默认:36(华东)", font=self.font_config['small']).grid(row=1, column=2, sticky=tk.W, pady=8)

        # 查询按钮区域
        daily_query_btn = ttk.Button(daily_frame, text="查询昨日日报", command=self.query_daily_report, width=20)
        daily_query_btn.pack(pady=10, anchor=tk.W)
        daily_query_btn.configure(cursor="hand2")

        # ===== 战场周报页面 =====
        last_sunday = datetime.now() - timedelta(days=(datetime.now().weekday() + 1) % 7)
        default_date = last_sunday.strftime("%Y%m%d")
        
        weekly_input_frame = ttk.Frame(weekly_frame, padding=(10, 10, 10, 15))
        weekly_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 统一标签宽度，保持对齐
        label_width = 8
        
        ttk.Label(weekly_input_frame, text="统计日期:", width=label_width, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(5, 8))
        self.weekly_date_var = tk.StringVar(value=default_date)
        weekly_date_entry = ttk.Entry(weekly_input_frame, textvariable=self.weekly_date_var, width=20, font=self.font_config['entry'])
        weekly_date_entry.grid(row=0, column=1, sticky=tk.W, pady=(5, 8), padx=(10, 15))
        ttk.Label(weekly_input_frame, text="格式: YYYYMMDD", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(5, 8))

        ttk.Label(weekly_input_frame, text="战区:", width=label_width, font=self.font_config['label']).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.weekly_area_var = tk.StringVar(value="36")
        weekly_area_entry = ttk.Entry(weekly_input_frame, textvariable=self.weekly_area_var, width=15, font=self.font_config['entry'])
        weekly_area_entry.grid(row=1, column=1, sticky=tk.W, pady=8, padx=(10, 15))

        ttk.Label(weekly_input_frame, text="模式:", width=label_width, font=self.font_config['label']).grid(row=2, column=0, sticky=tk.W, pady=8)
        self.weekly_mode_var = tk.StringVar(value="sol")
        weekly_mode_combo = ttk.Combobox(weekly_input_frame, textvariable=self.weekly_mode_var, width=20, state="readonly",
                                         font=self.font_config['entry'])
        weekly_mode_combo['values'] = ('sol', 'mp')
        weekly_mode_combo.grid(row=2, column=1, sticky=tk.W, pady=8, padx=(10, 15))
        ttk.Label(weekly_input_frame, text="sol:烽火地带 mp:全面战场", font=self.font_config['small']).grid(row=2, column=2, sticky=tk.W, pady=8)

        # 查询按钮
        btn_frame = ttk.Frame(weekly_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        weekly_query_btn = ttk.Button(btn_frame, text="查询战场周报", command=self.query_weekly_report, width=18)
        weekly_query_btn.pack(anchor=tk.W)
        weekly_query_btn.configure(cursor="hand2")

        # ===== 队友周报页面 =====
        friend_input_frame = ttk.Frame(friend_frame, padding=(10, 10, 10, 15))
        friend_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(friend_input_frame, text="统计日期:", width=label_width, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(5, 8))
        self.friend_date_var = tk.StringVar(value=default_date)
        friend_date_entry = ttk.Entry(friend_input_frame, textvariable=self.friend_date_var, width=20, font=self.font_config['entry'])
        friend_date_entry.grid(row=0, column=1, sticky=tk.W, pady=(5, 8), padx=(10, 15))
        ttk.Label(friend_input_frame, text="格式: YYYYMMDD", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(5, 8))

        # 第二行使用网格布局，确保对齐
        row2_frame = ttk.Frame(friend_input_frame)
        row2_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=8)
        
        ttk.Label(row2_frame, text="战区:", width=5, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.friend_area_var = tk.StringVar(value="36")
        friend_area_entry = ttk.Entry(row2_frame, textvariable=self.friend_area_var, width=15, font=self.font_config['entry'])
        friend_area_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 30))
        
        ttk.Label(row2_frame, text="模式:", width=5, font=self.font_config['label']).grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.friend_mode_var = tk.StringVar(value="sol")
        friend_mode_combo = ttk.Combobox(row2_frame, textvariable=self.friend_mode_var, width=20, state="readonly",
                                         font=self.font_config['entry'])
        friend_mode_combo['values'] = ('sol', 'mp')
        friend_mode_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        ttk.Label(row2_frame, text="sol:烽火地带 mp:全面战场", font=self.font_config['small']).grid(row=0, column=4, sticky=tk.W)

        # 查询按钮
        btn_frame = ttk.Frame(friend_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        friend_query_btn = ttk.Button(btn_frame, text="查询周报队友", command=self.query_friend_report, width=18)
        friend_query_btn.pack(anchor=tk.W)
        friend_query_btn.configure(cursor="hand2")

        # ===== 烽火周报页面 =====
        fire_weekly_input_frame = ttk.Frame(fire_weekly_frame, padding=(10, 10, 10, 15))
        fire_weekly_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(fire_weekly_input_frame, text="统计日期:", width=label_width, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(5, 8))
        self.fire_weekly_date_var = tk.StringVar(value=default_date)
        fire_weekly_date_entry = ttk.Entry(fire_weekly_input_frame, textvariable=self.fire_weekly_date_var, width=20,
                                           font=self.font_config['entry'])
        fire_weekly_date_entry.grid(row=0, column=1, sticky=tk.W, pady=(5, 8), padx=(10, 15))
        ttk.Label(fire_weekly_input_frame, text="格式: YYYYMMDD", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(5, 8))

        ttk.Label(fire_weekly_input_frame, text="战区:", width=label_width, font=self.font_config['label']).grid(row=1, column=0, sticky=tk.W, pady=8)
        self.fire_weekly_area_var = tk.StringVar(value="36")
        fire_weekly_area_entry = ttk.Entry(fire_weekly_input_frame, textvariable=self.fire_weekly_area_var, width=15,
                                           font=self.font_config['entry'])
        fire_weekly_area_entry.grid(row=1, column=1, sticky=tk.W, pady=8, padx=(10, 15))

        # 查询按钮
        btn_frame = ttk.Frame(fire_weekly_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        fire_weekly_query_btn = ttk.Button(btn_frame, text="查询烽火周报", 
                                           command=self.query_fire_weekly_report, width=18)
        fire_weekly_query_btn.pack(anchor=tk.W)
        fire_weekly_query_btn.configure(cursor="hand2")

        # ===== 货币资产页面 =====
        currency_input_frame = ttk.Frame(currency_frame, padding=(10, 10, 10, 15))
        currency_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(currency_input_frame, text="货币类型:", width=label_width, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(5, 8))
        self.currency_type_var = tk.StringVar(value="17020000010")
        currency_combo = ttk.Combobox(currency_input_frame, textvariable=self.currency_type_var, width=20,
                                      state="readonly", font=self.font_config['entry'])
        currency_combo['values'] = ('17020000010', '17888808889', '17888808888')
        currency_combo.grid(row=0, column=1, sticky=tk.W, pady=(5, 8), padx=(10, 15))
        
        # 创建货币类型说明框架，更美观的布局
        currency_info_frame = ttk.Frame(currency_input_frame)
        currency_info_frame.grid(row=0, column=2, sticky=tk.W, pady=(5, 8), padx=(5, 0))
        ttk.Label(currency_info_frame, text="17020000010 - 哈夫币", font=self.font_config['small']).pack(anchor=tk.W, pady=1)
        ttk.Label(currency_info_frame, text="17888808889 - 三角券", font=self.font_config['small']).pack(anchor=tk.W, pady=1)
        ttk.Label(currency_info_frame, text="17888808888 - 三角币", font=self.font_config['small']).pack(anchor=tk.W, pady=1)

        # 查询按钮
        btn_frame = ttk.Frame(currency_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        currency_query_btn = ttk.Button(btn_frame, text="查询货币资产", command=self.query_currency, width=18)
        currency_query_btn.pack(anchor=tk.W)
        currency_query_btn.configure(cursor="hand2")

        # ===== 每日密码页面 =====
        secret_input_frame = ttk.Frame(secret_frame, padding=(10, 10, 10, 15))
        secret_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(secret_input_frame, text="来源:", width=label_width, font=self.font_config['label']).grid(row=0, column=0, sticky=tk.W, pady=(5, 8))
        self.secret_source_var = tk.StringVar(value="2")
        secret_source_entry = ttk.Entry(secret_input_frame, textvariable=self.secret_source_var, width=15, font=self.font_config['entry'])
        secret_source_entry.grid(row=0, column=1, sticky=tk.W, pady=(5, 8), padx=(10, 15))
        ttk.Label(secret_input_frame, text="默认为2", font=self.font_config['small']).grid(row=0, column=2, sticky=tk.W, pady=(5, 8))

        # 查询按钮
        btn_frame = ttk.Frame(secret_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        secret_query_btn = ttk.Button(btn_frame, text="查询每日密码", command=self.query_secret, width=18)
        secret_query_btn.pack(anchor=tk.W)
        secret_query_btn.configure(cursor="hand2")

        # ===== 特勤处状态页面 =====
        special_duty_input_frame = ttk.Frame(special_duty_frame, padding=(10, 20, 10, 20))
        special_duty_input_frame.pack(fill=tk.X)
        special_duty_query_btn = ttk.Button(special_duty_input_frame, text="查询特勤处状态", 
                                           command=self.query_special_duty, width=18)
        special_duty_query_btn.pack(anchor=tk.W)
        special_duty_query_btn.configure(cursor="hand2")

        # ===== 结果展示区域 =====
        result_frame = ttk.LabelFrame(main_frame, text="查询结果", padding=(12, 10, 12, 12))
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10), padx=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)
        
        # 设置窗口最大高度，避免超出屏幕
        screen_height = self.root.winfo_screenheight()
        self.root.maxsize(height=int(screen_height * 0.9))  # 限制为屏幕高度的90%

        # 状态栏和进度指示器
        status_bar_frame = ttk.Frame(main_frame)
        status_bar_frame.grid(row=3, column=0, sticky=tk.EW, pady=(0, 2), padx=5)
        status_bar_frame.columnconfigure(0, weight=1)
        
        # 状态栏标签
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(status_bar_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, font=self.font_config['small'])
        status_bar.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=1)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, sticky=tk.EW, pady=(0, 3), padx=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=1)
        self.progress_bar.grid_remove()  # 初始隐藏
        
        # 结果视图选择器
        view_selector_frame = ttk.Frame(result_frame)
        view_selector_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        
        ttk.Label(view_selector_frame, text="显示方式:", font=self.font_config['small']).pack(side=tk.LEFT, padx=5)
        self.view_mode_var = tk.StringVar(value="table")
        ttk.Radiobutton(view_selector_frame, text="表格视图", variable=self.view_mode_var, 
                       value="table", command=self._switch_view_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(view_selector_frame, text="文本视图", variable=self.view_mode_var, 
                       value="text", command=self._switch_view_mode).pack(side=tk.LEFT, padx=5)
        
        # 添加分隔线提升视觉效果
        separator = ttk.Separator(result_frame, orient='horizontal')
        separator.grid(row=0, column=0, sticky=tk.EW, pady=(20, 0))

        # 创建结果容器框架
        result_content_frame = ttk.Frame(result_frame)
        result_content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_content_frame.columnconfigure(0, weight=1)
        result_content_frame.rowconfigure(0, weight=1)
        
        # 文本显示区域 - 用于非结构化数据
        self.result_text = scrolledtext.ScrolledText(result_content_frame, height=20, wrap=tk.WORD, 
                                                   font=self.font_config['monospace'])
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.result_text.grid_remove()  # 初始隐藏
        
        # 创建表格框架和滚动条
        self.table_frame = ttk.Frame(result_content_frame)
        self.table_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 表格滚动条
        table_vscroll = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL)
        table_hscroll = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL)
        
        # 创建表格
        self.tree = ttk.Treeview(
            self.table_frame, 
            yscrollcommand=table_vscroll.set,
            xscrollcommand=table_hscroll.set,
            show="headings",
            selectmode="extended"
        )
        
        # 配置表格样式
        self.tree.tag_configure('even', background='#f0f0f0')
        self.tree.tag_configure('odd', background='#ffffff')
        
        table_vscroll.config(command=self.tree.yview)
        table_hscroll.config(command=self.tree.xview)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_vscroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        table_hscroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.table_frame.rowconfigure(0, weight=1)
        self.table_frame.columnconfigure(0, weight=1)
        
        # ===== 功能按钮区域 =====
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, sticky=tk.EW, pady=(5, 0), padx=5)
        
        # 左侧按钮组 - 优化间距和样式
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT, fill=tk.X)
        
        clear_btn = ttk.Button(left_buttons, text="清空结果", command=self.clear_results, width=12)
        clear_btn.pack(side=tk.LEFT, padx=4)
        clear_btn.configure(cursor="hand2")

        refresh_btn = ttk.Button(left_buttons, text="刷新数据", command=self.refresh_data, width=12)
        refresh_btn.pack(side=tk.LEFT, padx=4)
        refresh_btn.configure(cursor="hand2")

        export_btn = ttk.Button(left_buttons, text="导出数据", command=self.export_data, width=12)
        export_btn.pack(side=tk.LEFT, padx=4)
        export_btn.configure(cursor="hand2")
        export_btn.configure(cursor="hand2")

        # 右侧按钮组
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        export_all_btn = ttk.Button(right_buttons, text="一键导出所有数据", command=self.show_export_selection, width=15)
        export_all_btn.pack(side=tk.RIGHT, padx=5)
        export_all_btn.configure(cursor="hand2")

        help_btn = ttk.Button(right_buttons, text="使用帮助", command=self.show_help, width=10)
        help_btn.pack(side=tk.RIGHT, padx=5)
        help_btn.configure(cursor="hand2")
        
        # 保存框架引用，用于主题切换
        self.all_frames = []
        self.all_frames.extend([main_frame, auth_frame, daily_frame, weekly_frame, friend_frame, 
                               fire_weekly_frame, currency_frame, secret_frame, special_duty_frame,
                               result_frame, button_frame, title_frame, status_bar_frame, view_selector_frame,
                               auth_input_frame, daily_input_frame, weekly_input_frame, fire_weekly_input_frame,
                               currency_input_frame, secret_input_frame, currency_info_frame, result_content_frame])

        # 配置权重，使界面可响应式扩展
        main_frame.rowconfigure(2, weight=1)  # 结果区域占主要空间
        main_frame.rowconfigure(1, weight=1)  # 标签页区域可扩展
        
        # 初始化当前查询状态（用于刷新功能）
        self.current_query_function = None
        self.current_query_args = ()
        
        # 应用默认主题
        self.theme_manager.apply_theme_to_widget(self.root)

    def save_auth_info(self):
        """保存认证信息到配置文件"""
        try:
            # 验证输入
            openid = self.openid_var.get().strip()
            token = self.token_var.get().strip()
            
            if not openid or not token:
                messagebox.showerror("错误", "OpenID和Token不能为空")
                return
            
            # 保存认证信息到主配置文件，与其他配置保持一致
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
            config = configparser.ConfigParser()
            
            # 如果配置文件存在，先读取现有配置
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
            
            # 确保Settings节存在
            if 'Settings' not in config:
                config['Settings'] = {}
            
            # 添加认证信息到Settings节
            config['Settings']['openid'] = openid
            config['Settings']['token'] = token
            config['Settings']['acctype'] = self.acctype_var.get().strip()
            
            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 同时更新内存中的配置
            self.config['openid'] = openid
            self.config['token'] = token
            self.config['acctype'] = self.acctype_var.get().strip()
            
            messagebox.showinfo("成功", "认证信息已保存")
        except Exception as e:
            # 更详细的错误信息，包含文件路径
            error_msg = f"保存认证信息失败: {str(e)}\n配置文件路径: {config_path}"
            self.logger.error(error_msg)  # 记录错误日志
            messagebox.showerror("错误", error_msg)
    
    def toggle_theme(self):
        """切换应用主题"""
        self.current_theme = self.theme_manager.toggle_theme()
        
        # 应用主题到所有保存的框架
        for frame in self.all_frames:
            self.theme_manager.apply_theme_to_widget(frame)
        
        # 应用主题到根窗口
        self.theme_manager.apply_theme_to_widget(self.root)
        
        # 保存主题设置
        self.config['theme'] = self.theme_manager.current_theme
        self.save_config()
    
    def get_cookie(self):
        """获取Cookie信息，增强错误处理和验证"""
        openid = self.openid_var.get().strip()
        token = self.token_var.get().strip()
        acctype = self.acctype_var.get().strip()

        # 输入验证
        if not openid:
            error_msg = "OpenID不能为空"
            self.logger.error(error_msg)
            messagebox.showerror("输入错误", error_msg)
            if hasattr(self, '_update_query_status'):
                self._update_query_status(False)
            return None
            
        if not token:
            error_msg = "Token不能为空"
            self.logger.error(error_msg)
            messagebox.showerror("输入错误", error_msg)
            if hasattr(self, '_update_query_status'):
                self._update_query_status(False)
            return None
        
        # 格式验证
        if len(openid) < 10:
            error_msg = "OpenID格式不正确（长度至少10位）"
            self.logger.warning(error_msg)
            messagebox.showwarning("格式警告", error_msg)
            
        if len(token) < 20:
            error_msg = "Token格式不正确（长度至少20位）"
            self.logger.warning(error_msg)
            messagebox.showwarning("格式警告", error_msg)
        
        # 账号类型验证
        if acctype not in ['qc', 'wx']:
            error_msg = f"账号类型不正确: {acctype}"
            self.logger.error(error_msg)
            messagebox.showerror("输入错误", error_msg)
            if hasattr(self, '_update_query_status'):
                self._update_query_status(False)
            return None

        cookie = f"openid={openid}; acctype={acctype}; appid=101491592; access_token={token}"
        self.logger.debug(f"Cookie生成成功，长度: {len(cookie)}")
        return cookie
    
    def _make_api_request(self, host, params, headers=None, timeout=30, max_retries=3):
        """通用API请求方法，增强错误处理和恢复机制"""
        
        # 参数验证
        if not host or not params:
            error_msg = "API请求参数无效：host或params为空"
            self.logger.error(error_msg)
            messagebox.showerror("参数错误", error_msg)
            return None
        
        # 生成缓存键
        cache_key = f"{host}:{hash(str(sorted(params.items())))}"
        
        # 检查缓存
        if hasattr(self, 'api_cache') and cache_key in self.api_cache:
            cached_result, cache_time = self.api_cache[cache_key]
            if time.time() - cache_time < self.config.get('cache_expiry', 300):
                self.logger.debug(f"使用缓存数据: {cache_key}")
                return cached_result
        
        # 初始化缓存
        if not hasattr(self, 'api_cache'):
            self.api_cache = {}
        
        # 重试逻辑
        for attempt in range(max_retries):
            conn = None
            try:
                # 设置默认请求头
                if headers is None:
                    headers = {}
                
                # 统一Content-Type
                headers['content-type'] = 'application/x-www-form-urlencoded;'
                
                # 验证请求参数
                if not all(isinstance(v, (str, int, float)) for v in params.values()):
                    raise ValueError("请求参数包含无效类型")
                
                # 执行请求
                conn = http.client.HTTPSConnection(host, timeout=timeout)
                payload = ''
                
                # 构建查询字符串
                query_string = urllib.parse.urlencode(params)
                full_path = f"/ide/?{query_string}"
                
                self.logger.debug(f"API请求: {host}{full_path}")
                conn.request("POST", full_path, payload, headers)
                
                # 获取响应
                res = conn.getresponse()
                
                # 检查HTTP响应状态码
                if res.status != 200:
                    error_msg = f"HTTP请求失败，状态码: {res.status} {res.reason}"
                    self.set_status(error_msg)
                    self.logger.error(error_msg)
                    
                    # 详细的错误处理
                    if res.status == 401:
                        messagebox.showerror("认证错误", "Token无效或已过期，请重新输入")
                        return None
                    elif res.status == 403:
                        messagebox.showerror("权限错误", "访问被拒绝，请检查账号权限")
                        return None
                    elif res.status == 404:
                        messagebox.showerror("资源错误", "请求的资源不存在")
                        return None
                    elif 400 <= res.status < 500:
                        messagebox.showerror("客户端错误", f"请求参数错误: {res.status}")
                        return None
                    
                    # 5xx错误，继续重试
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 指数退避
                        self.logger.warning(f"5xx错误，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        messagebox.showerror("服务器错误", f"服务器错误 ({res.status})，请稍后重试")
                        return None
                
                data = res.read()
                result = data.decode("utf-8")
                
                # 验证响应数据
                if not result or len(result) < 10:
                    self.logger.warning("响应数据异常短小")
                    
                # 缓存成功的结果
                self.api_cache[cache_key] = (result, time.time())
                self.logger.info(f"API请求成功: {host}")
                return result
                
            except (http.client.HTTPException, TimeoutError, ConnectionError, socket.timeout) as e:
                error_msg = f"网络请求错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                self.set_status("网络请求错误")
                self.logger.warning(error_msg)
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    final_error = f"请求失败，请检查网络连接: {str(e)}"
                    self.set_status(final_error)
                    self.logger.error(final_error)
                    messagebox.showerror("网络错误", final_error)
                    return None
            except Exception as e:
                error_msg = f"发生未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                self.set_status("未知错误")
                self.logger.error(error_msg)
                self.logger.error(traceback.format_exc())
                
                if attempt < max_retries - 1:
                    wait_time = 1
                    time.sleep(wait_time)
                    continue
                else:
                    messagebox.showerror("未知错误", error_msg)
                    return None
            finally:
                # 确保连接总是被关闭
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
        
        return None

    def set_status(self, message):
        """设置状态栏消息和进度指示，使用队列机制避免UI阻塞"""
        # 确保消息包含前缀
        if not message.startswith("状态:"):
            message = f"状态: {message}"
        
        # 使用after方法避免直接更新UI，提高响应性
        def update_status():
            self.status_var.set(message)
            self.root.update_idletasks()
        
        self.root.after(0, update_status)
        
        # 记录状态历史，限制最近10条
        timestamp = datetime.now().strftime("%H:%M:%S")
        history_entry = f"[{timestamp}] {message}"
        if not hasattr(self, 'query_history'):
            self.query_history = []
        self.query_history.append(history_entry)
        if len(self.query_history) > 10:
            self.query_history.pop(0)
            
    def update_progress(self, value):
        """更新进度条，使用异步更新避免UI阻塞"""
        if hasattr(self, 'progress_bar') and hasattr(self, 'progress_var'):
            # 使用after方法异步更新进度条，提高响应性
            def update_progress_value():
                # 确保进度条可见
                if not self.progress_bar.winfo_ismapped():
                    self.progress_bar.grid()
                    
                # 更新进度值，范围0-100
                self.progress_var.set(min(100, max(0, value)))
                
                # 如果进度达到100%，延迟隐藏进度条
                if value >= 100:
                    self.root.after(1000, self._hide_progress)
            
            self.root.after(0, update_progress_value)
                
    def _hide_progress(self):
        """隐藏进度条"""
        if hasattr(self, 'progress_bar') and self.progress_bar.winfo_ismapped():
            self.progress_var.set(0)
            self.progress_bar.grid_remove()
    
    def _update_query_status(self, is_querying=True):
        """更新查询状态，控制按钮可用性"""
        self.is_querying = is_querying
        
        # 更新UI按钮状态
        button_names = ['clear_button', 'refresh_button', 'export_button', 'clear_btn', 'refresh_btn', 'export_btn']
        
        for btn_name in button_names:
            if hasattr(self, btn_name):
                button = getattr(self, btn_name)
                button.config(state=tk.DISABLED if is_querying else tk.NORMAL)
                
        # 更新进度条初始状态
        if is_querying:
            self.update_progress(10)  # 初始进度10%
        else:
            self.update_progress(100)  # 完成时进度100%

    def query_daily_report(self):
        # 保存当前查询状态
        self.current_query_function = self.query_daily_report
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询昨日日报...")
        threading.Thread(target=self._query_daily_report).start()

    def query_weekly_report(self):
        # 保存当前查询状态
        self.current_query_function = self.query_weekly_report
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询战场周报...")
        threading.Thread(target=self._query_weekly_report).start()

    def query_friend_report(self):
        # 保存当前查询状态
        self.current_query_function = self.query_friend_report
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询周报队友...")
        threading.Thread(target=self._query_friend_report).start()

    def query_fire_weekly_report(self):
        # 保存当前查询状态
        self.current_query_function = self.query_fire_weekly_report
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询烽火周报...")
        threading.Thread(target=self._query_fire_weekly_report).start()

    def query_currency(self):
        # 保存当前查询状态
        self.current_query_function = self.query_currency
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询货币资产...")
        threading.Thread(target=self._query_currency).start()

    def query_secret(self):
        # 保存当前查询状态
        self.current_query_function = self.query_secret
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询每日密码...")
        threading.Thread(target=self._query_secret).start()

    def query_special_duty(self):
        # 保存当前查询状态
        self.current_query_function = self.query_special_duty
        self.current_query_args = ()
        
        # 更新查询状态
        self._update_query_status(True)
        self.set_status("正在查询特勤处状态...")
        threading.Thread(target=self._query_special_duty).start()

    # ==================== 选择导出对话框 ====================

    def show_export_selection(self):
        """显示模块选择对话框"""
        selection_window = tk.Toplevel(self.root)
        selection_window.title("选择导出模块")
        selection_window.geometry("500x600")
        selection_window.transient(self.root)
        selection_window.grab_set()

        # 标题
        ttk.Label(selection_window, text="请选择要导出的数据模块（可多选）：", font=("Arial", 12, "bold")).pack(
            pady=15, padx=20, anchor=tk.W)

        # 创建滚动框架
        canvas = tk.Canvas(selection_window)
        scrollbar = ttk.Scrollbar(selection_window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # 全选/全不选框架
        select_all_frame = ttk.Frame(selection_window)
        select_all_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # 复选框变量
        self.module_vars = {}

        # 创建全选/全不选按钮
        def select_all():
            for var in self.module_vars.values():
                var.set(True)

        def select_none():
            for var in self.module_vars.values():
                var.set(False)

        ttk.Button(select_all_frame, text="全选", command=select_all, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_all_frame, text="全不选", command=select_none, width=10).pack(side=tk.LEFT, padx=5)

        # 为每个模块创建复选框
        for module_name in self.module_definitions.keys():
            var = tk.BooleanVar(value=True)  # 默认全部选中
            self.module_vars[module_name] = var

            cb = ttk.Checkbutton(scrollable_frame, text=module_name, variable=var)
            cb.pack(anchor=tk.W, padx=20, pady=5)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20))

        # 按钮框架
        button_frame = ttk.Frame(selection_window)
        button_frame.pack(pady=20)

        def confirm_selection():
            # 获取选中的模块
            selected_modules = [name for name, var in self.module_vars.items() if var.get()]
            if not selected_modules:
                messagebox.showwarning("警告", "请至少选择一个模块！")
                return

            selection_window.destroy()
            self.set_status("正在导出选中的数据...")
            threading.Thread(target=self._export_selected_data, args=(selected_modules,)).start()

        def cancel_selection():
            selection_window.destroy()

        ttk.Button(button_frame, text="确认导出", command=confirm_selection, width=15).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=cancel_selection, width=15).pack(side=tk.LEFT, padx=10)

    def _export_selected_data(self, selected_modules):
        """导出选中的模块数据，支持多种格式"""
        try:
            all_data = self._collect_selected_data(selected_modules)
            if all_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                module_count = len(selected_modules)
                
                # 根据配置确定默认导出格式
                default_format = self.config.get('export_format', 'json')
                default_filename = f"三角洲行动_{module_count}个模块_{timestamp}.{default_format}"

                # 定义支持的文件类型
                filetypes = [
                    ("JSON文件", "*.json"),
                    ("CSV表格文件", "*.csv"),
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ]

                filename = filedialog.asksaveasfilename(
                    defaultextension="." + default_format,
                    filetypes=filetypes,
                    title="导出选中数据",
                    initialfile=default_filename
                )

                if filename:
                    _, ext = os.path.splitext(filename)
                    ext = ext.lower()
                    
                    # 根据不同格式导出数据
                    if ext == '.json':
                        # 原始的JSON格式导出
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(all_data, f, ensure_ascii=False, indent=2)
                    elif ext == '.csv':
                        # 导出为CSV格式
                        csv_content = self._convert_data_to_csv(all_data)
                        with open(filename, "w", encoding="utf-8-sig") as f:
                            f.write(csv_content)
                    else:
                        # 导出为文本格式
                        text_content = self._convert_data_to_text(all_data)
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(text_content)
                    
                    self.set_status(f"选中数据已导出到: {filename}")
                    messagebox.showinfo("成功", f"已导出 {module_count} 个模块的数据！\n文件: {filename}")
                else:
                    self.set_status("导出已取消")
            else:
                self.set_status("数据收集失败")
                messagebox.showwarning("警告", "未能收集到任何数据，请检查认证信息是否正确")

        except Exception as e:
            self.set_status("导出失败")
            messagebox.showerror("错误", f"导出过程中发生错误: {str(e)}")
    
    def _convert_data_to_csv(self, data):
        """将收集的数据转换为CSV格式"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(["模块名称", "数据内容"])
        
        # 写入各模块数据
        for module_name, module_data in data.items():
            # 尝试将字典转换为格式化字符串
            if isinstance(module_data, dict):
                content = "\n".join([f"{k}: {v}" for k, v in module_data.items()])
            elif isinstance(module_data, list):
                content = "\n".join([str(item) for item in module_data])
            else:
                content = str(module_data)
            
            writer.writerow([module_name, content])
        
        return output.getvalue()
    
    def _convert_data_to_text(self, data):
        """将收集的数据转换为文本格式"""
        lines = []
        
        for module_name, module_data in data.items():
            lines.append(f"\n{'='*50}")
            lines.append(f"模块: {module_name}")
            lines.append(f"{'='*50}")
            
            # 格式化数据
            if isinstance(module_data, dict):
                for k, v in module_data.items():
                    lines.append(f"{k}: {v}")
            elif isinstance(module_data, list):
                for idx, item in enumerate(module_data, 1):
                    lines.append(f"{idx}. {item}")
            else:
                lines.append(str(module_data))
        
        return '\n'.join(lines)

    def _collect_selected_data(self, selected_modules):
        """收集选中模块的格式化数据"""
        cookie = self.get_cookie()
        if not cookie:
            messagebox.showerror("错误", "OpenID和Token不能为空，请在认证设置中填写")
            return None

        s_area = self.daily_area_var.get().strip() or "36"
        stat_date = self.weekly_date_var.get().strip()
        if not stat_date or len(stat_date) != 8:
            stat_date = (datetime.now() - timedelta(days=(datetime.now().weekday() + 1) % 7)).strftime("%Y%m%d")

        all_data = {
            "导出时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "用户信息": {
                "openid": self.openid_var.get().strip(),
                "acctype": self.acctype_var.get().strip(),
                "战区": s_area,
                "统计日期": stat_date
            },
            "导出模块": selected_modules,
            "数据模块": {}
        }

        # 获取额外参数
        extra_params = {
            "stat_date": stat_date,
            "s_area": s_area
        }

        for module_name in selected_modules:
            try:
                self.set_status(f"正在获取: {module_name}...")
                module_def = self.module_definitions[module_name]

                # 准备参数
                args = module_def["fetch_args"].copy()
                if "extra_args" in module_def:
                    for arg_name in module_def["extra_args"]:
                        args.append(extra_params.get(arg_name, ""))

                # 获取并处理数据
                raw_data = module_def["fetch_func"](*args)
                processed_data = module_def["process_func"](raw_data)

                all_data["数据模块"][module_name] = {
                    "状态": "成功",
                    "数据": processed_data
                }
            except Exception as e:
                all_data["数据模块"][module_name] = {
                    "状态": "失败",
                    "错误信息": str(e)
                }

        self.set_status("数据收集完成，正在保存...")
        return all_data

    # ==================== 查询功能实现 ====================

    def _parse_api_response(self, result):
        """通用API响应解析函数，处理不同格式的API返回数据"""
        try:
            data = json.loads(result)
            
            # 检查不同的响应格式
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return False, f"请求失败: {data.get('sMsg', '未知错误')}"
            
            # 处理jData格式
            if 'jData' in data:
                jdata = data['jData']
                
                # 处理包含data字段的格式
                if 'data' in jdata:
                    response_data = jdata['data']
                    
                    # 处理包含code字段的格式
                    if isinstance(response_data, dict) and 'code' in response_data:
                        if response_data['code'] != 0:
                            return False, f"数据获取失败: {response_data.get('msg', response_data.get('message', '未知错误'))}"
                        return True, response_data.get('data', {})
                    
                    # 处理直接返回数据的格式
                    return True, response_data
                
                # 处理jData直接包含iRet和sMsg的格式
                if jdata.get('iRet') != '0':
                    return False, f"数据获取失败: {jdata.get('sMsg', '未知错误')}"
                return True, jdata.get('data', {})
            
            return True, data
        except json.JSONDecodeError:
            return False, "JSON解析错误"
        except Exception as e:
            return False, f"解析结果时发生错误: {str(e)}"
    
    def _perform_query(self, query_config):
        """通用查询方法，减少代码重复
        
        参数:
            query_config: 包含查询配置的字典，包括：
                - param_getter: 获取查询参数的函数
                - validate_func: 验证参数的函数（可选）
                - param_builder: 构建API参数的函数
                - host: API主机地址
                - display_func: 显示结果的函数
                - success_status: 查询成功的状态消息
        """
        # 初始化结果变量
        success = False
        
        try:
            # 获取cookie
            cookie = self.get_cookie()
            if not cookie:
                messagebox.showwarning("认证失败", "未找到有效的Cookie信息，请先进行身份验证")
                self.set_status("认证失败")
                return False
            
            # 获取查询参数
            try:
                query_params = query_config['param_getter']()
                self.logger.debug(f"获取查询参数成功: {query_params}")
            except Exception as e:
                error_msg = f"获取查询参数失败: {str(e)}"
                self.logger.error(error_msg)
                messagebox.showerror("参数错误", "获取查询参数时发生错误，请检查输入")
                self.set_status("参数获取失败")
                return False
            
            # 验证参数
            if 'validate_func' in query_config:
                try:
                    if query_config['validate_func'](query_params):
                        self.logger.debug("参数验证失败")
                        return False
                except Exception as e:
                    error_msg = f"参数验证函数执行错误: {str(e)}"
                    self.logger.error(error_msg)
                    messagebox.showerror("验证错误", "参数验证过程中发生错误")
                    self.set_status("参数验证失败")
                    return False
            
            # 显示加载状态
            try:
                self.root.config(cursor="wait")
                if hasattr(self, 'progress_bar'):
                    self.progress_bar.grid()
                    self.progress_var.set(20)
                    self.root.update_idletasks()
            except Exception as e:
                self.logger.error(f"更新UI状态失败: {str(e)}")
            
            # 构建API请求参数
            try:
                headers = {'Cookie': cookie}
                params = query_config['param_builder'](query_params)
                self.logger.debug(f"构建API参数成功: {params}")
                
                if hasattr(self, 'progress_var'):
                    self.progress_var.set(50)
                    self.root.update_idletasks()
            except Exception as e:
                error_msg = f"构建API参数失败: {str(e)}"
                self.logger.error(error_msg)
                messagebox.showerror("参数错误", "构建API请求参数时发生错误")
                self.set_status("参数构建失败")
                return False
            
            # 执行API请求
            try:
                result = self._make_api_request(query_config['host'], params, headers)
                
                if hasattr(self, 'progress_var'):
                    self.progress_var.set(80)
                    self.root.update_idletasks()
            except Exception as e:
                error_msg = f"API请求失败: {str(e)}"
                self.logger.error(error_msg)
                messagebox.showerror("网络错误", f"发送请求时发生错误: {str(e)}\n请检查网络连接或稍后重试")
                self.set_status("请求失败")
                return False
            
            # 处理结果
            if result:
                try:
                    query_config['display_func'](result, query_params)
                    self.set_status(query_config['success_status'])
                    self.logger.info(f"查询成功: {query_config['success_status']}")
                    
                    # 自动适应表格列宽
                    if hasattr(self, 'result_tree') and hasattr(self, 'view_mode_var') and self.view_mode_var.get() == 'table':
                        if hasattr(self, '_autofit_tree_columns'):
                            try:
                                self._autofit_tree_columns()
                            except Exception as e:
                                self.logger.warning(f"自动调整列宽失败: {str(e)}")
                    success = True
                except Exception as e:
                    error_msg = f"处理查询结果失败: {str(e)}"
                    self.logger.error(error_msg)
                    messagebox.showerror("处理错误", f"处理查询结果时发生错误: {str(e)}")
                    self.set_status("结果处理失败")
            else:
                self.logger.warning("API返回空结果")
                self.set_status("查询失败")
                messagebox.showwarning("查询失败", "无法获取数据，请检查网络连接或稍后重试\n可能是服务器暂时不可用")
        except Exception as e:
            # 捕获任何未预期的异常
            error_msg = f"查询执行错误: {str(e)}"
            self.logger.error(error_msg)
            messagebox.showerror("错误", f"查询过程中发生未预期的错误: {str(e)}")
            self.set_status("查询执行错误")
        finally:
            # 恢复界面状态
            try:
                self.root.config(cursor="")
                if hasattr(self, 'progress_bar'):
                    self.progress_var.set(0)
                    self.progress_bar.grid_remove()
                self._update_query_status(False)
            except Exception as e:
                self.logger.error(f"恢复界面状态失败: {str(e)}")
                
            if hasattr(self, 'progress_var'):
                self.progress_var.set(100)
                self.root.update_idletasks()
                
                # 延迟隐藏进度条，让用户看到完成状态
                self.root.after(300, lambda: self.progress_bar.grid_remove() if hasattr(self, 'progress_bar') else None)
            
            self._update_query_status(False)
            self.root.config(cursor="")
            
        return success

    def _query_daily_report(self):
        """查询昨日日报数据"""
        # 配置查询参数
        query_config = {
            'param_getter': lambda: {
                'resource_type': self.daily_resource_var.get(),
                's_area': self.daily_area_var.get().strip()
            },
            'param_builder': lambda p: {
                'iChartId': '316969',
                'iSubChartId': '316969',
                'sIdeToken': 'NoOapI',
                'method': 'dfm/center.recent.detail',
                'source': '2',
                'sArea': p['s_area'],
                'param': json.dumps({'resourceType': p['resource_type']})
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_daily_result(r, p['resource_type']),
            'success_status': '昨日日报查询完成'
        }
        
        self._perform_query(query_config)

    def _query_special_duty(self):
        """查询特勤处状态"""
        # 配置查询参数
        query_config = {
            'param_getter': lambda: {},  # 无需额外参数
            'param_builder': lambda p: {
                'iChartId': '365589',
                'iSubChartId': '365589',
                'sIdeToken': 'bQaMCQ',
                'source': '2'
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_special_duty_result(r),
            'success_status': '特勤处状态查询完成'
        }
        
        self._perform_query(query_config)

    def _query_weekly_report(self):
        """查询战场周报数据"""
        # 配置查询参数
        query_config = {
            'param_getter': lambda: {
                'stat_date': self.weekly_date_var.get().strip(),
                's_area': self.weekly_area_var.get().strip(),
                'mode': self.weekly_mode_var.get()
            },
            'validate_func': lambda p: (not p['stat_date'] or len(p['stat_date']) != 8 or not p['stat_date'].isdigit()) and messagebox.showerror("错误", "统计日期格式不正确，应为YYYYMMDD格式的8位数字"),
            'param_builder': lambda p: {
                'iChartId': '316969',
                'iSubChartId': '316969',
                'sIdeToken': 'NoOapI',
                'method': f"dfm/weekly.{p['mode']}.record",
                'source': '5',
                'sArea': p['s_area'],
                'param': json.dumps({'statDate': p['stat_date']})
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_weekly_result(r, p['mode']),
            'success_status': '战场周报查询完成'
        }
        
        self._perform_query(query_config)

    def _query_secret(self):
        """查询每日密码"""
        query_config = {
            'param_getter': lambda: {
                'source': self.secret_source_var.get().strip()
            },
            'validate_func': lambda params: self._validate_not_empty(params['source'], "密码来源"),
            'param_builder': lambda p: {
                'iChartId': '316969',
                'iSubChartId': '316969',
                'sIdeToken': 'NoOapI',
                'method': 'dfm/center.day.secret',
                'source': p['source'],
                'param': '{}'
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_secret_result(r),
            'success_status': '每日密码查询完成'
        }
        
        self._perform_query(query_config)

    def _validate_date_format(self, date_string):
        """验证日期格式是否为YYYYMMDD格式的8位数字
        
        参数:
            date_string: 要验证的日期字符串
            
        返回:
            bool: 格式正确返回True，否则显示错误提示并返回False
        """
        if not date_string or len(date_string) != 8 or not date_string.isdigit():
            messagebox.showerror("错误", "统计日期格式不正确，应为YYYYMMDD格式的8位数字")
            return True  # 返回True表示验证失败
        return False  # 返回False表示验证通过
    
    def _validate_not_empty(self, value, field_name):
        """验证字段不为空
        
        参数:
            value: 要验证的值
            field_name: 字段名称，用于错误提示
            
        返回:
            bool: 为空返回True，否则返回False
        """
        if not bool(value):
            messagebox.showerror("错误", f"请选择{field_name}")
            return True  # 返回True表示验证失败
        return False  # 返回False表示验证通过
    
    def _query_friend_report(self):
        """查询周报队友数据"""
        # 配置查询参数
        query_config = {
            'param_getter': lambda: {
                'stat_date': self.friend_date_var.get().strip(),
                's_area': self.friend_area_var.get().strip(),
                'mode': self.friend_mode_var.get()
            },
            'validate_func': lambda p: self._validate_date_format(p['stat_date']),
            'param_builder': lambda p: {
                'iChartId': '316968',
                'iSubChartId': '316968',
                'sIdeToken': 'KfXJwH',
                'source': '5',
                'sArea': p['s_area'],
                'method': f"dfm/weekly.{p['mode']}.friend.record",
                'statDate': p['stat_date'],
                'param': json.dumps({
                    'source': '5',
                    'method': f"dfm/weekly.{p['mode']}.friend.record",
                    'statDate': p['stat_date']
                })
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_friend_result(r, p['mode']),
            'success_status': '周报队友查询完成'
        }
        
        self._perform_query(query_config)

    def _query_fire_weekly_report(self):
        """查询烽火周报数据"""
        query_config = {
            'param_getter': lambda: {
                'stat_date': self.fire_weekly_date_var.get().strip(),
                's_area': self.fire_weekly_area_var.get().strip()
            },
            'validate_func': lambda params: self._validate_date_format(params['stat_date']),
            'param_builder': lambda p: {
                'iChartId': '316968',
                'iSubChartId': '316968',
                'sIdeToken': 'KfXJwH',
                'source': '5',
                'sArea': p['s_area'],
                'method': "dfm/weekly.sol.record",
                'statDate': p['stat_date'],
                'param': json.dumps({
                    'source': '5',
                    'method': "dfm/weekly.sol.record",
                    'statDate': p['stat_date']
                })
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_fire_weekly_result(r),
            'success_status': '烽火周报查询完成'
        }
        
        self._perform_query(query_config)

    def _query_currency(self):
        """查询货币资产"""
        query_config = {
            'param_getter': lambda: {
                'item': self.currency_type_var.get().strip()
            },
            'validate_func': lambda params: self._validate_not_empty(params['item'], "货币类型"),
            'param_builder': lambda p: {
                'iChartId': '319386',
                'iSubChartId': '319386',
                'sIdeToken': 'zMemOt',
                'item': p['item'],
                'type': '3'
            },
            'host': 'comm.ams.game.qq.com',
            'display_func': lambda r, p: self.display_currency_result(r, p['item']),
            'success_status': '货币资产查询完成'
        }
        
        self._perform_query(query_config)

    # ==================== 结果显示 ====================

    def show_table(self, headers, data):
        """通用表格显示方法"""
        # 清空表格
        self.tree.delete(*self.tree.get_children())
        
        # 设置列
        self.tree['columns'] = list(headers.keys())
        
        # 配置列标题和宽度
        for col, title in headers.items():
            self.tree.heading(col, text=title)
            self.tree.column(col, width=150, anchor='center')
            # 允许列自动调整大小
            self.tree.column(col, stretch=True, minwidth=100)
        
        # 添加数据行，实现斑马纹效果
        for i, row in enumerate(data):
            values = [row.get(col, '') for col in headers.keys()]
            # 斑马纹效果：偶数行使用浅灰色背景
            tags = ('evenrow',) if i % 2 == 1 else ()
            self.tree.insert('', tk.END, values=values, tags=tags)
        
        # 配置斑马纹样式
        self.tree.tag_configure('evenrow', background='#f0f0f0')
        
        # 添加鼠标悬停效果
        self.tree.bind('<Enter>', lambda e, t=self.tree: t.bind('<Motion>', self._on_mouse_move))
        self.tree.bind('<Leave>', lambda e, t=self.tree: t.unbind('<Motion>'))
        
        # 切换显示模式：隐藏文本区域，显示表格
        self.result_text.grid_remove()
        self.table_frame.grid()
    
    def display_special_duty_result(self, result):
        """使用表格显示特勤处状态结果"""
        try:
            self.clear_results()
            # 保存当前查询结果
            self.current_query_result = result
            
            data = json.loads(result)
            jData = data.get("jData", {})
            place_data = jData.get("data", {}).get("data", {}).get("placeData", [])

            if not place_data:
                self.result_text.insert(tk.END, "没有特勤处状态数据\n")
                return
            
            # 准备表格数据
            table_data = []
            for place in place_data:
                name = place.get('Name', '未知')
                status = place.get('Status', '未知')
                level = place.get('Level', '未知')
                left_time_seconds = place.get('leftTime', 0)
                
                if left_time_seconds > 0:
                    hours = left_time_seconds // 3600
                    minutes = (left_time_seconds % 3600) // 60
                    seconds = left_time_seconds % 60
                    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    formatted_time = "已完成"
                
                table_data.append({
                    'name': name,
                    'status': status,
                    'level': level,
                    'remain_time': formatted_time
                })
            
            # 定义表头
            headers = {
                'name': '名称',
                'status': '状态',
                'level': '等级',
                'remain_time': '剩余时间'
            }
            
            # 使用表格显示
            self.show_table(headers, table_data)
            
            # 根据当前视图模式设置显示
            if hasattr(self, 'current_view_mode'):
                if self.current_view_mode == 'table':
                    # 表格模式，自动调整列宽
                    self._autofit_tree_columns()
                else:
                    # 文本模式，格式化文本显示
                    self._format_text_display()
        except Exception as e:
            error_msg = f"解析结果时发生错误: {str(e)}"
            self.result_text.insert(tk.END, error_msg)
            self.set_status(error_msg)
            messagebox.showerror("错误", error_msg)

    def display_daily_result(self, result, resource_type):
        self.clear_results()
        resource_name = "烽火地带" if resource_type == "sol" else "全面战场"
        self.result_text.insert(tk.END, f"=== {resource_name}昨日日报 ===\n\n")

        try:
            success, actual_data = self._parse_api_response(result)
            if not success:
                self.result_text.insert(tk.END, f"查询失败: {actual_data}\n")
                return
            
            if not actual_data:
                self.result_text.insert(tk.END, "无有效数据返回\n")
                return

            if resource_type == "sol":
                report_data = actual_data.get('solDetail', {})
                if not report_data:
                    self.result_text.insert(tk.END, "无烽火地带日报数据\n")
                    return

                self.result_text.insert(tk.END, f"报告日期: {report_data.get('recentGainDate', '未知')}\n")
                self.result_text.insert(tk.END, f"昨日收益: {report_data.get('recentGain', 0):,} 金币\n\n")

                user_collection = report_data.get('userCollectionTop', {})
                top_items = user_collection.get('list', []) if isinstance(user_collection, dict) else []

                if top_items:
                    self.result_text.insert(tk.END, "=== 收益Top3物品 ===\n\n")
                    for i, item in enumerate(top_items, 1):
                        item_id = item.get('objectID', '未知')
                        item_name = self.get_item_name(item_id)
                        self.result_text.insert(tk.END, f"{i}. 物品: {item_name} (ID: {item_id})\n")
                        self.result_text.insert(tk.END, f"   带出数量: {item.get('count', 0)}\n")
                        self.result_text.insert(tk.END, f"   物品价值: {float(item.get('price', 0)):,.1f} 金币\n\n")
                else:
                    self.result_text.insert(tk.END, "无收益Top3物品数据\n\n")

                current_time = actual_data.get('currentTime', '未知')
                self.result_text.insert(tk.END, f"报告生成时间: {current_time}\n")
            else:
                mp_data = actual_data.get('mpDetail', {})
                if mp_data:
                    self.result_text.insert(tk.END, "=== 全面战场数据 ===\n\n")
                    self.result_text.insert(tk.END, f"总得分: {mp_data.get('totalScore', 0):,}\n")
                    self.result_text.insert(tk.END, f"总击杀: {mp_data.get('totalKill', 0):,}\n")
                    self.result_text.insert(tk.END, f"总死亡: {mp_data.get('totalDeath', 0):,}\n")
                    self.result_text.insert(tk.END, f"胜场: {mp_data.get('winNum', 0):,}\n")
                    self.result_text.insert(tk.END, f"总场次: {mp_data.get('totalNum', 0):,}\n")
                else:
                    self.result_text.insert(tk.END, "无全面战场数据\n")

        except json.JSONDecodeError:
            self.result_text.insert(tk.END, "JSON解析错误，原始响应:\n\n")
            self.result_text.insert(tk.END, result)
        except Exception as e:
            self.result_text.insert(tk.END, f"处理数据时发生错误: {str(e)}\n")

    def display_weekly_result(self, result, mode):
        self.clear_results()
        mode_name = "烽火地带" if mode == "sol" else "全面战场"
        self.result_text.insert(tk.END, f"=== {mode_name}战场周报 ===\n\n")

        try:
            data = json.loads(result)

            if data.get('ret') != 0 or data.get('iRet') != 0:
                self.result_text.insert(tk.END, f"请求失败: {data.get('sMsg', '未知错误')}\n")
                return

            jdata = data.get('jData', {}).get('data', {})

            if jdata.get('code') != 0:
                self.result_text.insert(tk.END, f"数据获取失败: {jdata.get('message', '未知错误')}\n")
                return

            weekly_data = jdata.get('data', {})

            if isinstance(weekly_data, list) and len(weekly_data) == 0:
                self.result_text.insert(tk.END, "本周无战场周报数据\n")
                return

            fields = {
                'Consume_Bullet_Num': '总消耗弹药数',
                'Hit_Bullet_Num': '总命中子弹数',
                'Kill_Num': '总击杀数',
                'Kill_type1_Num': '载具击杀数量',
                'Rank_Match_Score': '排位分',
                'Rescue_Campmate_Count': '救援阵营队友数',
                'Rescue_Teammate_Count': '救援小队队友数',
                'SBattle_Support_CostScore': '局内支援呼叫消耗分数',
                'SBattle_Support_UseNum': '局内支援呼叫次数',
                'Teammate_Reborn_Num': '队友重生次数',
                'Used_Time': '使用次数',
                'by_Rescue_num': '被救援次数',
                'continuous_Kill_Num': '最高连续击杀',
                'total_Occupy': '占点数',
                'total_gametime': '总游戏时长(秒)',
                'total_num': '对局场次',
                'total_score': '总得分',
                'win_num': '胜场',
                'DeployArmedForceType_KillNum': '本命干员完成击杀',
                'DeployArmedForceType_gametime': '本命干员游戏时长(秒)',
                'DeployArmedForceType_inum': '本命干员完成对局',
                'max_inum_DeployArmedForceType': '本命干员ID',
                'max_inum_mapid': '地图信息'
            }

            for field, description in fields.items():
                value = weekly_data.get(field, '无数据')
                if value != '无数据' and isinstance(value, (int, float, str)) and str(value).replace('.', '', 1).isdigit():
                    try:
                        if '.' in str(value):
                            value = f"{float(value):,.1f}"
                        else:
                            value = f"{int(value):,}"
                    except:
                        pass
                self.result_text.insert(tk.END, f"{description}: {value}\n")

        except json.JSONDecodeError:
            self.result_text.insert(tk.END, "原始响应:\n\n")
            self.result_text.insert(tk.END, result)

    def display_friend_result(self, result, mode):
        self.clear_results()
        # 确保使用文本视图显示
        if hasattr(self, '_switch_view_mode'):
            self._switch_view_mode('text')
        mode_name = "烽火地带" if mode == "sol" else "全面战场"
        self.result_text.insert(tk.END, f"=== {mode_name}周报队友数据 ===\n\n")

        try:
            data = json.loads(result)

            if data.get('ret') != 0 or data.get('iRet') != 0:
                self.result_text.insert(tk.END, f"请求失败: {data.get('sMsg', '未知错误')}\n")
                return

            jdata = data.get('jData', {}).get('data', {})

            if jdata.get('code') != 0:
                self.result_text.insert(tk.END, f"数据获取失败: {jdata.get('message', '未知错误')}\n")
                return

            friends_data = jdata.get('data', {}).get('friends_sol_record', [])

            if not friends_data:
                self.result_text.insert(tk.END, "无队友数据\n")
                return

            self.result_text.insert(tk.END, f"共找到 {len(friends_data)} 位队友\n\n")

            for i, friend in enumerate(friends_data, 1):
                self.result_text.insert(tk.END, f"=== 队友 {i} ===\n")
                self.result_text.insert(tk.END, f"OpenID: {friend.get('friend_openid', '未知')}\n")

                friend_fields = {
                    'Friend_total_sol_num': '总场次',
                    'Friend_is_Escape1_num': '撤离成功',
                    'Friend_is_Escape2_num': '撤离失败',
                    'Friend_Sum_Gained_Price': '总带出价值',
                    'Friend_Max_Gained_Price': '最高带出价值',
                    'Friend_consume_Price': '总战损',
                    'Friend_total_sol_KillPlayer': '击杀玩家数',
                    'Friend_total_sol_DeathCount': '死亡次数',
                    'Friend_total_sol_AssistCnt': '救援次数'
                }

                for field, desc in friend_fields.items():
                    value = friend.get(field, 0)
                    if isinstance(value, (int, float)):
                        value = f"{value:,}"
                    self.result_text.insert(tk.END, f"{desc}: {value}\n")

                self.result_text.insert(tk.END, "\n")

        except json.JSONDecodeError:
            self.result_text.insert(tk.END, "原始响应:\n\n")
            self.result_text.insert(tk.END, result)

    def display_fire_weekly_result(self, result):
        self.clear_results()
        # 确保使用文本视图显示
        if hasattr(self, '_switch_view_mode'):
            self._switch_view_mode('text')
        self.result_text.insert(tk.END, "=== 烽火周报数据 ===\n\n")

        try:
            data = json.loads(result)

            if data.get('ret') != 0 or data.get('iRet') != 0:
                self.result_text.insert(tk.END, f"请求失败: {data.get('sMsg', '未知错误')}\n")
                return

            jdata = data.get('jData', {}).get('data', {})

            if jdata.get('code') != 0:
                self.result_text.insert(tk.END, f"数据获取失败: {jdata.get('message', '未知错误')}\n")
                return

            fire_weekly_data = jdata.get('data', {})

            if not fire_weekly_data:
                self.result_text.insert(tk.END, "无烽火周报数据\n")
                return

            fields = {
                'Gained_Price': '本周总带出哈夫币',
                'consume_Price': '本周总带入',
                'rise_Price': '本周总利润',
                'total_sol_num': '本周对局数',
                'total_exacuation_num': '本周撤离成功数',
                'total_Kill_Player': '本周击败干员数',
                'total_Kill_AI': '本周击杀AI数',
                'total_Kill_Boss': '本周击杀BOSS数',
                'total_Death_Count': '本周死亡数',
                'GainedPrice_overmillion_num': '本周百万撤离场次',
                'total_Online_Time': '本周在线时长(秒)',
                'Rank_Score': '排位分数',
                'Mandel_brick_num': '本周曼德尔砖破译数',
            }

            for field, description in fields.items():
                value = fire_weekly_data.get(field, '无数据')
                if value != '无数据' and isinstance(value, (int, float, str)) and str(value).replace('.', '', 1).isdigit():
                    try:
                        if '.' in str(value):
                            value = f"{float(value):,.1f}"
                        else:
                            value = f"{int(value):,}"
                    except:
                        pass
                self.result_text.insert(tk.END, f"{description}: {value}\n")

            operator_data = fire_weekly_data.get('total_ArmedForceId_num', '')
            if operator_data:
                self.result_text.insert(tk.END, f"\n=== 干员使用情况 ===\n")
                try:
                    if isinstance(operator_data, str) and '#' in operator_data:
                        operator_dict = {}
                        for op_str in operator_data.split('#'):
                            if op_str.strip():
                                try:
                                    op_item = parse_dict_like_string(op_str.strip())
                                    op_id = str(op_item.get('ArmedForceId', ''))
                                    op_count = int(op_item.get('inum', 0))
                                    if op_id:
                                        operator_dict[op_id] = operator_dict.get(op_id, 0) + op_count
                                except:
                                    continue

                        if operator_dict:
                            total_uses = sum(operator_dict.values())
                            for op_id, op_count in sorted(operator_dict.items(), key=lambda x: int(x[1]), reverse=True):
                                op_name = self.operator_map.get(op_id, f"未知干员({op_id})")
                                percentage = (int(op_count) / total_uses * 100) if total_uses > 0 else 0
                                self.result_text.insert(tk.END, f"  {op_name}: {op_count}次 ({percentage:.1f}%)\n")
                        else:
                            self.result_text.insert(tk.END, f"  无有效干员数据\n")
                    else:
                        self.result_text.insert(tk.END, f"  数据格式异常: {operator_data}\n")
                except Exception as e:
                    self.result_text.insert(tk.END, f"  解析失败: {str(e)}\n")

            highprice_list_str = fire_weekly_data.get('CarryOut_highprice_list', '')
            if highprice_list_str:
                self.result_text.insert(tk.END, f"\n=== 高价值物品列表 ===\n")
                try:
                    if isinstance(highprice_list_str, str) and '#' in highprice_list_str:
                        items = []
                        for item_str in highprice_list_str.split('#'):
                            if item_str.strip():
                                try:
                                    item_dict = parse_dict_like_string(item_str.strip())
                                    items.append(item_dict)
                                except:
                                    continue

                        if items:
                            total_items = len(items)
                            self.result_text.insert(tk.END, f"  共 {total_items} 件物品\n\n")
                            sorted_items = sorted(items, key=lambda x: float(x.get('iPrice', 0)), reverse=True)

                            for i, item in enumerate(sorted_items, 1):
                                item_id = item.get('itemid', '未知')
                                item_name = self.get_item_name(item_id)
                                item_type = item.get('auctontype', '未知类型')
                                item_subtype = item.get('auctonsubtype', '')
                                quality = item.get('quality', 0)
                                price = float(item.get('iPrice', 0))
                                count = int(item.get('inum', 1))

                                self.result_text.insert(tk.END, f"  {i}. {item_name} (ID: {item_id})\n")
                                self.result_text.insert(tk.END, f"     类型: {item_type} - {item_subtype}\n")
                                self.result_text.insert(tk.END,
                                                        f"     品质: {quality}级 | 数量: {count} | 总价值: {price:,.0f}哈夫币\n\n")
                        else:
                            self.result_text.insert(tk.END, f"  无有效物品数据\n")
                    else:
                        self.result_text.insert(tk.END, f"  - {str(highprice_list_str)}\n")
                except Exception as e:
                    self.result_text.insert(tk.END, f"  解析失败: {str(e)}\n")

        except json.JSONDecodeError:
            self.result_text.insert(tk.END, "原始响应:\n\n")
            self.result_text.insert(tk.END, result)
        except Exception as e:
            self.result_text.insert(tk.END, f"处理数据时发生错误: {str(e)}\n")

    def display_currency_result(self, result, item_type):
        """使用表格显示货币资产数据"""
        self.clear_results()
        currency_name = {
            '17020000010': '哈夫币',
            '17888808889': '三角券',
            '17888808888': '三角币'
        }.get(item_type, '未知货币')

        try:
            data = json.loads(result)

            if data.get('ret') != 0 or data.get('iRet') != 0:
                self.result_text.insert(tk.END, f"请求失败: {data.get('sMsg', '未知错误')}\n")
                return

            jdata = data.get('jData', {})

            if jdata.get('iRet') != '0':
                self.result_text.insert(tk.END, f"数据获取失败: {jdata.get('sMsg', '未知错误')}\n")
                return

            currency_data = jdata.get('data', [{}])[0]
            total_money = currency_data.get('totalMoney', '0')
            
            # 准备表格数据
            table_data = [{
                'currency_type': currency_name,
                'amount': f"{int(total_money):,}",
                'description': '当前可用数量'
            }]
            
            # 添加详细信息（如果有）
            if 'details' in currency_data:
                for detail in currency_data['details']:
                    table_data.append({
                        'currency_type': f"{currency_name}明细",
                        'amount': str(detail.get('amount', 0)),
                        'description': detail.get('source', '未知来源')
                    })
            
            # 定义表头
            headers = {
                'currency_type': '货币类型',
                'amount': '数量',
                'description': '说明'
            }
            
            # 使用表格显示
            self.show_table(headers, table_data)

        except json.JSONDecodeError:
            self.result_text.insert(tk.END, "原始响应:\n\n")
            self.result_text.insert(tk.END, result)

    def display_secret_result(self, result, *args):
        try:
            self.clear_results()
            data = json.loads(result)
            jdata = data.get('jData', {})
            secret_data = jdata.get('data', {})

            if secret_data.get('code') == 0:
                secret_list = secret_data.get('data', {}).get('list', [])

                result_text = "每日密码查询结果：\n"
                result_text += "=" * 50 + "\n"

                for secret_info in secret_list:
                    map_id = secret_info.get('mapID', '')
                    map_name = secret_info.get('mapName', '')
                    password = secret_info.get('secret', '')

                    result_text += f"地图ID: {map_id}\n"
                    result_text += f"地图名称: {map_name}\n"
                    result_text += f"密码: {password}\n"
                    result_text += "-" * 30 + "\n"

                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, result_text)
            else:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, f"查询失败: {secret_data.get('msg', '未知错误')}")

        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"解析结果时发生错误: {str(e)}")

    def clear_results(self):
        """清除结果并重置视图，使用批量操作优化性能"""
        # 批量删除表格数据
        if hasattr(self, 'tree'):
            children = self.tree.get_children()
            if children:
                self.tree.delete(*children)
            
            # 清空列配置
            for col in self.tree['columns']:
                self.tree.heading(col, text='')
            self.tree['columns'] = ()
        
        # 清空文本内容
        if hasattr(self, 'result_text'):
            self.result_text.delete(1.0, tk.END)
        
        # 保留当前视图模式
        if hasattr(self, 'result_text') and hasattr(self, 'table_frame'):
            if self.current_view_mode == 'table' and hasattr(self, 'table_frame'):
                self.result_text.grid_remove()
                self.table_frame.grid()
            else:
                self.table_frame.grid_remove()
                self.result_text.grid()
        
        # 重置当前查询结果
        self.current_query_result = None
    
    def _on_tab_changed(self, event=None):
        """处理标签页切换事件"""
        if hasattr(self, 'notebook'):
            try:
                current_tab = self.notebook.select()
                self.current_tab_index = self.notebook.index(current_tab)
            except:
                self.current_tab_index = 0
    
    def _on_closing(self):
        """窗口关闭确认函数"""
        if messagebox.askyesno("确认退出", "确定要退出烽火地带数据查询工具吗？"):
            self.root.destroy()
    
    def _autofit_tree_columns(self):
        """自动调整表格列宽以适应内容，同时处理多种表格对象"""
        # 配置悬停样式
        if hasattr(self, 'tree'):
            self.tree.tag_configure('hover', background='#e0e0ff')
        if hasattr(self, 'result_tree'):
            self.result_tree.tag_configure('hover', background='#e0e0ff')
        
        # 处理self.tree表格
        if hasattr(self, 'tree'):
            self._autofit_specific_tree(self.tree)
        
        # 处理self.result_tree表格
        if hasattr(self, 'result_tree'):
            self._autofit_specific_tree(self.result_tree)
    
    def _autofit_specific_tree(self, tree_widget):
        """自动调整特定Treeview组件的列宽
        
        参数:
            tree_widget: 要调整的Treeview组件
        """
        # 获取配置的最大列宽（可从配置中读取或使用默认值）
        max_col_width = self.config.get('max_column_width', 500)
        
        # 为每一列调整宽度
        for col in tree_widget['columns']:
            # 首先设置一个合理的初始宽度
            tree_widget.column(col, width=120)
            
            try:
                # 尝试使用bbox方法获取实际渲染宽度（更准确）
                # 先尝试获取列标题宽度
                header_width = 0
                try:
                    # 注意：bbox可能在某些环境中不可靠
                    header_width = tree_widget.bbox('@0,0', col)[2] if tree_widget.bbox('@0,0', col) else 0
                except:
                    # 如果获取失败，使用文字长度估算
                    header_text = tree_widget.heading(col).get('text', col)
                    header_width = len(header_text) * 10
                
                # 获取该列所有项的最大宽度
                max_width = max(header_width, len(col) * 10)  # 至少显示完整的列名
                
                # 遍历所有行计算最大宽度
                for item in tree_widget.get_children():
                    try:
                        # 尝试使用bbox获取实际宽度
                        cell_width = 0
                        try:
                            cell_bbox = tree_widget.bbox(item, col)
                            cell_width = cell_bbox[2] if cell_bbox else 0
                        except:
                            # 如果bbox不可用，使用字符串长度估算
                            index = tree_widget['columns'].index(col)
                            value = str(tree_widget.item(item, 'values')[index]) if index < len(tree_widget.item(item, 'values')) else ''
                            cell_width = len(value) * 9
                        
                        if cell_width > max_width:
                            max_width = cell_width
                    except Exception as e:
                        # 忽略单个单元格的错误，继续处理其他单元格
                        self.logger.debug(f"计算单元格宽度失败: {str(e)}")
                
                # 设置列宽为最大宽度加一些边距
                final_width = min(max_width + 20, max_col_width)  # 限制最大宽度
                tree_widget.column(col, width=final_width, anchor='center')
                
                # 配置列标题居中显示
                tree_widget.heading(col, anchor='center')
                
            except Exception as e:
                # 如果整列调整失败，使用默认宽度并记录错误
                tree_widget.column(col, width=150, anchor='center')
                self.logger.warning(f"调整列'{col}'宽度失败: {str(e)}")
        
        # 确保Treeview自动扩展填充可用空间
        tree_widget.column('#0', width=0, stretch=tk.NO)  # 隐藏默认的#0列
    
    def _switch_view_mode(self, mode=None):
        """切换结果显示模式"""
        # 如果未指定模式，则使用切换按钮的状态
        if mode is None:
            mode = self.view_mode_var.get() if hasattr(self, 'view_mode_var') else self.current_view_mode
        
        self.current_view_mode = mode
        
        # 切换视图显示
        if hasattr(self, 'result_text') and hasattr(self, 'table_frame'):
            # 切换到表格视图时自动适应列宽
            if mode == 'table' and hasattr(self, 'result_tree'):
                self._autofit_tree_columns()
            if mode == 'table':
                self.result_text.grid_remove()
                self.table_frame.grid()
                # 自动调整列宽以适应内容
                if hasattr(self, 'tree'):
                    # 先设置一个初始宽度
                    for col in self.tree['columns']:
                        self.tree.column(col, width=120, anchor='center')
                    # 然后让表格尝试自动调整
                    self._autofit_tree_columns()
            else:
                self.table_frame.grid_remove()
                self.result_text.grid()
                # 更新文本显示格式
                if hasattr(self, 'current_query_result') and self.current_query_result:
                    self._format_text_display()
                    

            
    def _format_text_display(self):
        """格式化文本显示，使输出更易读"""
        if not hasattr(self, 'result_text') or not self.current_query_result:
            return
            
        # 清空现有文本
        self.result_text.delete(1.0, tk.END)
        
        try:
            # 尝试将结果解析为JSON
            import json
            parsed = json.loads(self.current_query_result)
            # 格式化JSON以提高可读性
            formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
            self.result_text.insert(tk.END, formatted)
        except:
            # 如果解析失败，直接显示原始文本
            self.result_text.insert(tk.END, self.current_query_result)
        
        # 如果有当前查询结果，尝试在当前视图中显示
        if hasattr(self, 'current_query_result') and self.current_query_result:
            # 这里可以添加逻辑，将当前结果根据视图模式重新显示
            pass
    
    def refresh_data(self):
        """优化的刷新数据方法"""
        # 保存当前视图模式
        previous_mode = self.current_view_mode if hasattr(self, 'current_view_mode') else 'text'
        
        self.set_status("正在刷新数据...")
        self.clear_results()
        
        try:
            # 清除缓存
            if hasattr(self, 'result_cache'):
                self.result_cache = {}
            if hasattr(self, 'cache_timestamps'):
                self.cache_timestamps = {}
            
            # 优先使用保存的查询状态
            if hasattr(self, 'current_query_function') and self.current_query_function:
                self.current_query_function(*self.current_query_args)
            else:
                # 回退到基于标签页的刷新
                if hasattr(self, '_refresh_by_current_tab'):
                    self._refresh_by_current_tab()
                else:
                    messagebox.showinfo("提示", "请先执行一次查询操作")
            
        except Exception as e:
            error_msg = f"刷新数据失败: {str(e)}"
            self.set_status(error_msg)
            self.log_error(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def _refresh_by_current_tab(self):
        """根据当前标签页刷新数据"""
        if hasattr(self, 'notebook'):
            current_tab = self.notebook.select()
            tab_id = self.notebook.index(current_tab)
            
            # 根据标签页索引重新执行相应的查询
            if tab_id == 0:  # 认证设置 - 无需查询
                self.set_status("认证设置页面无需刷新数据")
            elif tab_id == 1:  # 昨日日报
                self.query_daily_report()
            elif tab_id == 2:  # 战场周报
                self.query_weekly_report()
            elif tab_id == 3:  # 周报队友
                self.query_friend_report()
            elif tab_id == 4:  # 烽火周报
                self.query_fire_weekly_report()
            elif tab_id == 5:  # 货币查询
                self.query_currency()
            elif tab_id == 6:  # 每日密码
                self.query_secret()
            elif tab_id == 7:  # 特勤处状态
                self.query_special_duty()

    def export_data(self):
        """导出当前显示的数据，支持多种格式，优化用户体验"""
        # 获取当前显示的内容
        content = self.result_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showinfo("提示", "没有数据可以导出")
            return

        try:
            # 根据配置确定默认导出格式
            default_ext = "." + self.config.get('export_format', 'txt')
            
            # 定义支持的文件类型
            filetypes = [
                ("文本文件 (TXT)", "*.txt"),
                ("CSV表格文件", "*.csv"),
                ("所有文件", "*.*")
            ]
            
            # 显示文件保存对话框，添加初始文件名建议
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            initial_filename = f"查询结果_{timestamp}{default_ext}"
            
            filename = filedialog.asksaveasfilename(
                defaultextension=default_ext,
                filetypes=filetypes,
                title="导出数据",
                initialfile=initial_filename
            )
            
            if filename:
                # 显示进度条
                self.set_status("正在导出数据...")
                self.update_progress(30)
                
                # 确定文件扩展名
                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                
                # 根据不同格式导出数据
                if ext == '.csv':
                    # 尝试将表格数据转换为CSV格式
                    csv_content = self._convert_to_csv(content)
                    with open(filename, "w", encoding="utf-8-sig") as f:  # 使用UTF-8 BOM以便Excel正确识别
                        f.write(csv_content)
                else:
                    # 默认使用TXT格式
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                
                # 更新进度
                self.update_progress(100)
                self.set_status(f"数据导出完成: {os.path.basename(filename)}")
                messagebox.showinfo("成功", f"数据已导出到 {filename}")
        except Exception as e:
            self.update_progress(0)
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            
    def _convert_to_csv(self, content):
        """尝试将表格格式的文本转换为CSV格式"""
        lines = content.strip().split('\n')
        csv_lines = []
        
        for line in lines:
            # 尝试检测常见的表格分隔符（制表符或多个空格）
            import re
            # 将多个空格或制表符替换为逗号
            csv_line = re.sub(r'\s{2,}|\t', ',', line.strip())
            csv_lines.append(csv_line)
        
        return '\n'.join(csv_lines)

    # ==================== 数据处理函数（供导出使用） ====================

    def _process_special_duty_data(self, result):
        """处理特勤处状态数据（格式化版）"""
        try:
            data = json.loads(result)
            jData = data.get("jData", {})
            place_data = jData.get("data", {}).get("data", {}).get("placeData", [])

            facilities = []
            for place in place_data:
                left_time_seconds = place.get('leftTime', 0)
                if left_time_seconds > 0:
                    hours = left_time_seconds // 3600
                    minutes = (left_time_seconds % 3600) // 60
                    seconds = left_time_seconds % 60
                    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    formatted_time = "已完成"

                facilities.append({
                    "名称": place.get('Name', '未知'),
                    "状态": place.get('Status', '未知'),
                    "等级": place.get('Level', '未知'),
                    "剩余时间": formatted_time
                })
            return facilities
        except Exception as e:
            return {"错误": f"解析失败: {str(e)}"}

    def _process_daily_data(self, result, resource_type):
        """处理昨日日报数据（格式化版）"""
        try:
            data = json.loads(result)
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return {"错误": f"请求失败: {data.get('sMsg', '未知错误')}"}

            jdata = data.get('jData', {})
            response_data = jdata.get('data', {})

            if response_data.get('code') != 0:
                return {"错误": f"数据获取失败: {response_data.get('msg', '未知错误')}"}

            actual_data = response_data.get('data', {})

            if resource_type == "sol":
                report_data = actual_data.get('solDetail', {})
                top_items = report_data.get('userCollectionTop', {}).get('list', [])

                processed_items = []
                for i, item in enumerate(top_items, 1):
                    item_id = item.get('objectID', '未知')
                    processed_items.append({
                        "排名": i,
                        "物品ID": item_id,
                        "物品名称": self.get_item_name(item_id),
                        "带出数量": item.get('count', 0),
                        "物品价值": float(item.get('price', 0))
                    })

                return {
                    "报告日期": report_data.get('recentGainDate', '未知'),
                    "昨日收益": f"{report_data.get('recentGain', 0):,} 金币",
                    "收益Top物品": processed_items,
                    "生成时间": actual_data.get('currentTime', '未知')
                }
            else:
                mp_data = actual_data.get('mpDetail', {})
                return {
                    "总得分": f"{mp_data.get('totalScore', 0):,}",
                    "总击杀": f"{mp_data.get('totalKill', 0):,}",
                    "总死亡": f"{mp_data.get('totalDeath', 0):,}",
                    "胜场": f"{mp_data.get('winNum', 0):,}",
                    "总场次": f"{mp_data.get('totalNum', 0):,}"
                }
        except Exception as e:
            return {"错误": f"处理失败: {str(e)}"}

    def _process_weekly_data(self, result, mode):
        """处理战场周报数据（格式化版）"""
        try:
            data = json.loads(result)
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return {"错误": f"请求失败: {data.get('sMsg', '未知错误')}"}

            jdata = data.get('jData', {}).get('data', {})
            if jdata.get('code') != 0:
                return {"错误": f"数据获取失败: {jdata.get('message', '未知错误')}"}

            weekly_data = jdata.get('data', {})

            if isinstance(weekly_data, list) and len(weekly_data) == 0:
                return {"信息": "本周无战场周报数据"}

            fields = {
                'Consume_Bullet_Num': '总消耗弹药数',
                'Hit_Bullet_Num': '总命中子弹数',
                'Kill_Num': '总击杀数',
                'Kill_type1_Num': '载具击杀数量',
                'Rank_Match_Score': '排位分',
                'Rescue_Campmate_Count': '救援阵营队友数',
                'Rescue_Teammate_Count': '救援小队队友数',
                'SBattle_Support_CostScore': '局内支援呼叫消耗分数',
                'SBattle_Support_UseNum': '局内支援呼叫次数',
                'Teammate_Reborn_Num': '队友重生次数',
                'Used_Time': '使用次数',
                'by_Rescue_num': '被救援次数',
                'continuous_Kill_Num': '最高连续击杀',
                'total_Occupy': '占点数',
                'total_gametime': '总游戏时长(秒)',
                'total_num': '对局场次',
                'total_score': '总得分',
                'win_num': '胜场',
                'DeployArmedForceType_KillNum': '本命干员完成击杀',
                'DeployArmedForceType_gametime': '本命干员游戏时长(秒)',
                'DeployArmedForceType_inum': '本命干员完成对局',
                'max_inum_DeployArmedForceType': '本命干员ID',
                'max_inum_mapid': '地图信息'
            }

            processed_data = {}
            for field, description in fields.items():
                value = weekly_data.get(field, '无数据')
                if value != '无数据' and isinstance(value, (int, float, str)) and str(value).replace('.', '', 1).isdigit():
                    try:
                        if '.' in str(value):
                            value = f"{float(value):,.1f}"
                        else:
                            value = f"{int(value):,}"
                    except:
                        pass
                processed_data[description] = value

            return processed_data
        except Exception as e:
            return {"错误": f"处理失败: {str(e)}"}

    def _process_friend_data(self, result, mode):
        """处理队友数据（格式化版）"""
        try:
            data = json.loads(result)
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return {"错误": f"请求失败: {data.get('sMsg', '未知错误')}"}

            jdata = data.get('jData', {}).get('data', {})
            if jdata.get('code') != 0:
                return {"错误": f"数据获取失败: {jdata.get('message', '未知错误')}"}

            friends_data = jdata.get('data', {}).get('friends_sol_record', [])

            if not friends_data:
                return {"信息": "无队友数据"}

            processed_friends = []
            for i, friend in enumerate(friends_data, 1):
                friend_info = {
                    "序号": i,
                    "OpenID": friend.get('friend_openid', '未知'),
                    "总场次": f"{friend.get('Friend_total_sol_num', 0):,}",
                    "撤离成功": f"{friend.get('Friend_is_Escape1_num', 0):,}",
                    "撤离失败": f"{friend.get('Friend_is_Escape2_num', 0):,}",
                    "总带出价值": f"{friend.get('Friend_Sum_Gained_Price', 0):,}",
                    "最高带出价值": f"{friend.get('Friend_Max_Gained_Price', 0):,}",
                    "总战损": f"{friend.get('Friend_consume_Price', 0):,}",
                    "击杀玩家数": f"{friend.get('Friend_total_sol_KillPlayer', 0):,}",
                    "死亡次数": f"{friend.get('Friend_total_sol_DeathCount', 0):,}",
                    "救援次数": f"{friend.get('Friend_total_sol_AssistCnt', 0):,}"
                }
                processed_friends.append(friend_info)

            return {
                "队友数量": len(friends_data),
                "队友详情": processed_friends
            }
        except Exception as e:
            return {"错误": f"处理失败: {str(e)}"}

    def _process_fire_weekly_data(self, result):
        """处理烽火周报数据（格式化版）"""
        try:
            data = json.loads(result)
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return {"错误": f"请求失败: {data.get('sMsg', '未知错误')}"}

            jdata = data.get('jData', {}).get('data', {})
            if jdata.get('code') != 0:
                return {"错误": f"数据获取失败: {jdata.get('message', '未知错误')}"}

            fire_weekly_data = jdata.get('data', {})

            if not fire_weekly_data:
                return {"信息": "无烽火周报数据"}

            # 基础字段
            fields = {
                'Gained_Price': '本周总带出哈夫币',
                'consume_Price': '本周总带入',
                'rise_Price': '本周总利润',
                'total_sol_num': '本周对局数',
                'total_exacuation_num': '本周撤离成功数',
                'total_Kill_Player': '本周击败干员数',
                'total_Kill_AI': '本周击杀AI数',
                'total_Kill_Boss': '本周击杀BOSS数',
                'total_Death_Count': '本周死亡数',
                'GainedPrice_overmillion_num': '本周百万撤离场次',
                'total_Online_Time': '本周在线时长(秒)',
                'Rank_Score': '排位分数',
                'Mandel_brick_num': '本周曼德尔砖破译数',
            }

            processed_data = {}
            for field, description in fields.items():
                value = fire_weekly_data.get(field, '无数据')
                if value != '无数据' and isinstance(value, (int, float, str)) and str(value).replace('.', '', 1).isdigit():
                    try:
                        if '.' in str(value):
                            value = f"{float(value):,.1f}"
                        else:
                            value = f"{int(value):,}"
                    except:
                        pass
                processed_data[description] = value

            # 干员使用情况
            operator_data = fire_weekly_data.get('total_ArmedForceId_num', '')
            operators = []
            if operator_data and isinstance(operator_data, str) and '#' in operator_data:
                operator_dict = {}
                for op_str in operator_data.split('#'):
                    if op_str.strip():
                        try:
                            op_item = parse_dict_like_string(op_str.strip())
                            op_id = str(op_item.get('ArmedForceId', ''))
                            op_count = int(op_item.get('inum', 0))
                            if op_id:
                                operator_dict[op_id] = operator_dict.get(op_id, 0) + op_count
                        except:
                            continue

                if operator_dict:
                    total_uses = sum(operator_dict.values())
                    for op_id, op_count in sorted(operator_dict.items(), key=lambda x: int(x[1]), reverse=True):
                        op_name = self.operator_map.get(op_id, f"未知干员({op_id})")
                        percentage = (int(op_count) / total_uses * 100) if total_uses > 0 else 0
                        operators.append({
                            "干员名称": op_name,
                            "使用次数": op_count,
                            "占比": f"{percentage:.1f}%"
                        })

            processed_data["干员使用情况"] = operators

            # 高价值物品
            highprice_list_str = fire_weekly_data.get('CarryOut_highprice_list', '')
            highprice_items = []
            if highprice_list_str and isinstance(highprice_list_str, str) and '#' in highprice_list_str:
                for item_str in highprice_list_str.split('#'):
                    if item_str.strip():
                        try:
                            item_dict = parse_dict_like_string(item_str.strip())
                            item_id = item_dict.get('itemid', '未知')
                            price = float(item_dict.get('iPrice', 0))
                            highprice_items.append({
                                "物品名称": self.get_item_name(item_id),
                                "物品ID": item_id,
                                "类型": f"{item_dict.get('auctontype', '未知类型')} - {item_dict.get('auctonsubtype', '')}",
                                "品质": f"{item_dict.get('quality', 0)}级",
                                "数量": int(item_dict.get('inum', 1)),
                                "总价值": f"{price:,.0f}哈夫币"
                            })
                        except:
                            continue

            processed_data["高价值物品列表"] = {
                "物品总数": len(highprice_items),
                "物品详情": sorted(highprice_items, key=lambda x: float(x["总价值"].replace(',', '').replace('哈夫币', '')),
                               reverse=True)
            }

            return processed_data
        except Exception as e:
            return {"错误": f"处理失败: {str(e)}"}

    def _process_currency_data(self, result, item_type):
        """处理货币数据（格式化版）"""
        try:
            data = json.loads(result)
            if data.get('ret') != 0 or data.get('iRet') != 0:
                return {"错误": f"请求失败: {data.get('sMsg', '未知错误')}"}

            jdata = data.get('jData', {})
            if jdata.get('iRet') != '0':
                return {"错误": f"数据获取失败: {jdata.get('sMsg', '未知错误')}"}

            currency_data = jdata.get('data', [{}])[0]
            total_money = int(currency_data.get('totalMoney', 0))

            currency_name = {
                '17020000010': '哈夫币',
                '17888808889': '三角券',
                '17888808888': '三角币'
            }.get(item_type, '未知货币')

            return {
                "货币类型": currency_name,
                "数量": f"{total_money:,}"
            }
        except Exception as e:
            return {"错误": f"处理失败: {str(e)}"}

    def _process_secret_data(self, result):
        """处理每日密码数据（格式化版）"""
        try:
            data = json.loads(result)
            jdata = data.get('jData', {})
            secret_data = jdata.get('data', {})

            if secret_data.get('code') == 0:
                secret_list = secret_data.get('data', {}).get('list', [])
                processed_secrets = []
                for secret_info in secret_list:
                    processed_secrets.append({
                        "地图ID": secret_info.get('mapID', ''),
                        "地图名称": secret_info.get('mapName', ''),
                        "密码": secret_info.get('secret', '')
                    })
                return processed_secrets
            else:
                return {"错误": f"查询失败: {secret_data.get('msg', '未知错误')}"}
        except Exception as e:
            return {"错误": f"解析失败: {str(e)}"}

    # ==================== 数据获取方法（原始数据） ====================

    def _get_daily_report_data(self, resource_type, s_area=None):
        """获取昨日日报原始数据"""
        if s_area is None:
            s_area = self.daily_area_var.get().strip() or "36"
        cookie = self.get_cookie()

        params = {
            'iChartId': '316969',
            'iSubChartId': '316969',
            'sIdeToken': 'NoOapI',
            'method': 'dfm/center.recent.detail',
            'source': '2',
            'sArea': s_area,
            'param': json.dumps({'resourceType': resource_type})
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_weekly_report_data(self, mode, stat_date, s_area):
        """获取战场周报原始数据"""
        cookie = self.get_cookie()

        params = {
            'iChartId': '316969',
            'iSubChartId': '316969',
            'sIdeToken': 'NoOapI',
            'method': f'dfm/weekly.{mode}.record',
            'source': '5',
            'sArea': s_area,
            'param': json.dumps({'statDate': stat_date})
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_friend_report_data(self, mode, stat_date, s_area):
        """获取队友数据原始数据"""
        cookie = self.get_cookie()

        method = f"dfm/weekly.{mode}.friend.record"
        param_data = {'source': '5', 'method': method, 'statDate': stat_date}

        params = {
            'iChartId': '316968',
            'iSubChartId': '316968',
            'sIdeToken': 'KfXJwH',
            'source': '5',
            'sArea': s_area,
            'method': method,
            'statDate': stat_date,
            'param': json.dumps(param_data)
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_fire_weekly_report_data(self, stat_date, s_area):
        """获取烽火周报原始数据"""
        cookie = self.get_cookie()

        params = {
            'iChartId': '316968',
            'iSubChartId': '316968',
            'sIdeToken': 'KfXJwH',
            'source': '5',
            'sArea': s_area,
            'method': 'dfm/weekly.sol.record',
            'statDate': stat_date,
            'param': json.dumps({'source': '5', 'method': 'dfm/weekly.sol.record', 'statDate': stat_date})
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_currency_data(self, item_type):
        """获取货币资产原始数据"""
        cookie = self.get_cookie()

        params = {
            'iChartId': '319386',
            'iSubChartId': '319386',
            'sIdeToken': 'zMemOt',
            'item': item_type,
            'type': '3'
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_secret_data(self):
        """获取每日密码原始数据"""
        cookie = self.get_cookie()

        params = {
            'iChartId': '316969',
            'iSubChartId': '316969',
            'sIdeToken': 'NoOapI',
            'method': 'dfm/center.day.secret',
            'source': self.secret_source_var.get().strip(),
            'param': '{}'
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)

    def _get_special_duty_data(self):
        """获取特勤处状态原始数据"""
        cookie = self.get_cookie()

        params = {
            'iChartId': '365589',
            'iSubChartId': '365589',
            'sIdeToken': 'bQaMCQ',
            'source': '2'
        }

        headers = {'Cookie': cookie}
        return self._make_api_request("comm.ams.game.qq.com", params, headers)
    
    def show_config_dialog(self):
        """显示配置选项对话框"""
        # 创建配置对话框
        config_window = tk.Toplevel(self.root)
        config_window.title("配置选项")
        config_window.geometry("500x450")
        config_window.resizable(False, False)
        config_window.transient(self.root)
        config_window.grab_set()
        
        # 设置对话框的主题
        config_window.configure(bg=self.current_theme['bg'])
        
        # 创建笔记本组件来组织配置选项
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 网络设置页
        network_frame = ttk.Frame(notebook)
        notebook.add(network_frame, text="网络设置")
        
        # API超时设置
        ttk.Label(network_frame, text="API超时时间 (秒):", style="TLabel").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        timeout_var = tk.StringVar(value=str(self.config['timeout']))
        ttk.Entry(network_frame, textvariable=timeout_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        
        # 重试次数设置
        ttk.Label(network_frame, text="请求重试次数:", style="TLabel").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        retry_var = tk.StringVar(value=str(self.config['retry_count']))
        ttk.Entry(network_frame, textvariable=retry_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)
        
        # 缓存过期时间
        ttk.Label(network_frame, text="缓存过期时间 (秒):", style="TLabel").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        cache_var = tk.StringVar(value=str(self.config['cache_expiry']))
        ttk.Entry(network_frame, textvariable=cache_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)
        
        # 显示设置页
        display_frame = ttk.Frame(notebook)
        notebook.add(display_frame, text="显示设置")
        
        # 主题选择
        ttk.Label(display_frame, text="应用主题:", style="TLabel").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        theme_var = tk.StringVar(value=self.theme_manager.current_theme)
        theme_frame = ttk.Frame(display_frame)
        theme_frame.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        
        ttk.Radiobutton(theme_frame, text="浅色", variable=theme_var, value="light").pack(side=tk.LEFT)
        ttk.Radiobutton(theme_frame, text="深色", variable=theme_var, value="dark").pack(side=tk.LEFT)
        
        # 数据设置页
        data_frame = ttk.Frame(notebook)
        notebook.add(data_frame, text="数据设置")
        
        # 自动刷新
        auto_refresh_var = tk.BooleanVar(value=self.config['auto_refresh'])
        ttk.Checkbutton(data_frame, text="启用自动刷新", variable=auto_refresh_var, command=lambda: refresh_frame.grid(row=1, column=0) if auto_refresh_var.get() else refresh_frame.grid_remove()).grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # 刷新间隔
        refresh_frame = ttk.Frame(data_frame)
        ttk.Label(refresh_frame, text="刷新间隔 (秒):", style="TLabel").pack(side=tk.LEFT, padx=5)
        refresh_var = tk.StringVar(value=str(self.config['refresh_interval']))
        ttk.Entry(refresh_frame, textvariable=refresh_var, width=10).pack(side=tk.LEFT)
        
        # 根据当前设置显示或隐藏刷新间隔
        if auto_refresh_var.get():
            refresh_frame.grid(row=1, column=0, sticky=tk.W, padx=30, pady=5)
        
        # 详细日志
        log_var = tk.BooleanVar(value=self.config['show_detailed_logs'])
        ttk.Checkbutton(data_frame, text="显示详细日志", variable=log_var).grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        
        # 导出格式
        ttk.Label(data_frame, text="默认导出格式:", style="TLabel").grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
        export_var = tk.StringVar(value=self.config['export_format'])
        export_frame = ttk.Frame(data_frame)
        export_frame.grid(row=3, column=1, sticky=tk.W, padx=10, pady=10)
        
        ttk.Radiobutton(export_frame, text="文本 (TXT)", variable=export_var, value="txt").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(export_frame, text="表格 (CSV)", variable=export_var, value="csv").pack(side=tk.LEFT, padx=5)
        
        # 底部按钮区域
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def apply_settings():
            try:
                # 更新配置
                self.config['timeout'] = float(timeout_var.get())
                self.config['retry_count'] = int(retry_var.get())
                self.config['cache_expiry'] = int(cache_var.get())
                self.config['auto_refresh'] = auto_refresh_var.get()
                self.config['refresh_interval'] = int(refresh_var.get())
                self.config['show_detailed_logs'] = log_var.get()
                self.config['export_format'] = export_var.get()
                
                # 更新主题
                if theme_var.get() != self.theme_manager.current_theme:
                    self.theme_manager.current_theme = theme_var.get()
                    self.current_theme = self.theme_manager.get_theme()
                    self._update_style()
                
                # 保存配置
                self.save_config()
                messagebox.showinfo("成功", "配置已保存")
                config_window.destroy()
                
            except ValueError as e:
                messagebox.showerror("输入错误", f"请检查输入值: {str(e)}")
        
        ttk.Button(button_frame, text="取消", command=config_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="应用", command=apply_settings).pack(side=tk.RIGHT, padx=5)
        
        # 更新样式以应用当前主题
        for frame in [network_frame, display_frame, data_frame]:
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Widget):
                    widget.configure(style="TLabel")

    # 数据可视化相关方法已移除
            messagebox.showerror("错误", error_msg)
    
    def show_help(self):
        help_text = """使用说明：
1. 认证设置：
   - OpenID: 用户唯一标识
   - Token: 访问令牌
   - 账号类型: QQ(qc) 或 微信(wx)

2. 昨日日报：
   - 资源类型: sol(烽火) 或 mp(全面战场)
   - 战区: 默认36

3. 战场周报：
   - 统计日期: 格式YYYYMMDD (如: 20250706)
   - 战区: 默认36
   - 模式: sol(烽火) 或 mp(全面战场)

4. 周报队友：
   - 统计日期: 格式YYYYMMDD
   - 战区: 默认36
   - 模式: sol(烽火) 或 mp(全面战场)

5. 烽火周报：
   - 统计日期: 格式YYYYMMDD
   - 战区: 默认36

6. 货币查询：
   - 货币类型: 17020000010(哈夫币)、17888808889(三角券)、17888808888(三角币)

7. 每日密码：
   - 来源: 默认为2

8. 特勤处查询：
   - 显示特勤处各 facility 的等级和剩余时间

9. 一键导出所有数据：
   - 可一次性导出所有模块的数据
   - 文件格式: JSON格式，包含所有查询结果
   - 文件命名: 自动添加时间戳

10. 选择性导出：
    - 点击"一键导出所有数据"按钮后，可以选择要导出的模块
    - 支持多选，只导出选中的模块
    - 提供全选/全不选功能

11. 物品名称显示：
    - 在"昨日日报"和"烽火周报"中，物品ID会自动替换为物品名称
    - 需要确保 return.txt 文件与程序在同一目录下

12. 数据刷新功能：
    - 手动刷新：点击"刷新数据"按钮可刷新当前显示的数据
    - 自动刷新：在配置中可启用自动刷新功能，设置刷新间隔

13. 数据可视化：
    - 查询数据后，点击"数据可视化"按钮
    - 选择图表类型（柱状图、折线图、饼图）
    - 选择要显示的X轴和Y轴数据
    - 点击"生成图表"查看可视化结果
    - 可通过"保存图表"按钮将图表保存为图片文件

默认值已预设，可直接使用。查询结果会自动格式化显示。"""

        messagebox.showinfo("使用帮助", help_text)


    def _setup_logging(self):
        """优化的日志系统设置"""
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_filename = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 创建自定义日志格式
        class CustomFormatter(logging.Formatter):
            def format(self, record):
                # 添加线程信息
                record.thread_name = threading.current_thread().name
                return super().format(record)
        
        # 配置日志格式
        formatter = CustomFormatter(
            fmt='%(asctime)s - [%(thread_name)s] - %(name)s - %(levelname)s - %(module)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 获取日志记录器
        self.logger = logging.getLogger('FHZDDataQueryTool')
        
        # 根据配置设置日志级别
        log_level = logging.DEBUG if self.config.get('show_detailed_logs', False) else logging.INFO
        self.logger.setLevel(log_level)
        
        # 清除已有的处理器
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到日志记录器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 记录程序启动日志
        self.logger.info("程序启动，日志系统初始化完成")
        self.logger.debug(f"当前配置: {self.config}")
        
        # 记录系统信息
        try:
            import platform
            self.logger.info(f"系统信息: {platform.system()} {platform.release()} - Python {platform.python_version()}")
        except:
            pass
    
    def log_info(self, message):
        """记录信息日志"""
        if hasattr(self, 'logger'):
            self.logger.info(message)
    
    def log_debug(self, message):
        """记录调试日志"""
        if hasattr(self, 'logger'):
            self.logger.debug(message)
    
    def log_error(self, message):
        """记录错误日志"""
        if hasattr(self, 'logger'):
            self.logger.error(message)
            # 如果有异常信息，记录异常堆栈
            if traceback.format_exc() != 'NoneType: None\n':
                self.logger.error(traceback.format_exc())
    
    def setup_auto_refresh(self):
        """设置自动刷新功能"""
        # 取消现有的定时器（如果有）
        if hasattr(self, 'auto_refresh_timer') and self.auto_refresh_timer:
            self.root.after_cancel(self.auto_refresh_timer)
            self.auto_refresh_timer = None
        
        # 根据配置决定是否启用自动刷新
        if self.config.get('auto_refresh', False):
            interval = self.config.get('refresh_interval', 60) * 1000  # 转换为毫秒
            self.auto_refresh_timer = self.root.after(interval, self._auto_refresh_callback)
            self.log_info(f"已启用自动刷新，刷新间隔：{interval/1000}秒")
        else:
            self.log_info("自动刷新已禁用")
    
    def _auto_refresh_callback(self):
        """自动刷新的回调函数"""
        try:
            # 只有在有数据显示时才执行自动刷新
            if hasattr(self, 'tree') and len(self.tree.get_children()) > 0 or hasattr(self, 'result_text') and self.result_text.get(1.0, tk.END).strip():
                self.refresh_data()
        except Exception as e:
            error_msg = f"自动刷新失败: {str(e)}"
            self.log_error(error_msg)
        finally:
            # 无论成功失败，都重新设置定时器
            if self.config.get('auto_refresh', False):
                interval = self.config.get('refresh_interval', 60) * 1000
                self.auto_refresh_timer = self.root.after(interval, self._auto_refresh_callback)
            
    def _on_mouse_move(self, event):
        """处理鼠标悬停效果"""
        # 检查组件类型，确保只对Text组件应用标签操作
        if hasattr(event.widget, 'tag_remove') and hasattr(event.widget, 'tag_add'):
            # 获取鼠标位置对应的项
            item = event.widget.identify_row(event.y) if hasattr(event.widget, 'identify_row') else None
            if item:
                # 高亮当前行
                event.widget.tag_remove('hover', '*')
                event.widget.tag_add('hover', item)
            else:
                # 移除所有高亮
                event.widget.tag_remove('hover', '*')
            


if __name__ == "__main__":
    root = tk.Tk()
    app = FHZDDataQueryTool(root)
    root.mainloop()
