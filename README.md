# DFM游戏数据查询工具代码全解析

帮助文档链接: https://docs.qq.com/document/DS2hWc29pSGVIa3dM

=== DFM查询工具使用说明 ===

1. 用户配置：
   - 输入您的OpenID和Access Token
   - 点击保存按钮保存配置

2. 查询功能：
   - 选择查询类型
   - 点击查询数据获取结果

3. 支持的查询类型：
   - 每日密码：获取当日地图密码
   - 烽火地带收益Top3：查看昨日高价值物品
   - 全面战场数据：查看MP模式战绩
   - 战场周报数据：查看本周MP统计
   - 烽火周报数据：查看本周Sol统计
   - 特勤处状态：查看特勤处设施状态
   - 货币资产查询：查看游戏货币余额

4. 功能特性：
   - 可折叠的用户配置区域
   - 自动物品名称识别
   - 详细的数据格式化显示
   - 错误处理和状态提示

5. 常见问题：
   - 如查询失败，请检查网络连接
   - 如显示配置错误，请重新输入凭证
   - 可折叠配置区域以获得更大查看空间

完整文档请访问：https://docs.qq.com/document/DS2hWc29pSGVIa3dM
## 一、代码整体定位与技术栈
DFM游戏数据查询工具是基于Python开发的跨平台桌面应用，专为“烽火地带”（DFM）游戏玩家设计，核心功能是聚合查询游戏多维度数据，包括每日密码、战斗统计、周报数据、资产管理等，解决玩家手动查询数据效率低、维度分散的痛点。

技术栈选型聚焦轻量化与实用性，具体包括：
- **UI框架**：Toga，实现跨平台原生风格界面，支持Windows、macOS、Linux，无需单独适配不同系统UI；
- **网络请求**：requests，处理HTTP POST请求，调用游戏官方API获取数据，支持超时控制与异常捕获；
- **配置管理**：configparser，读写INI格式配置文件，存储用户OpenID与Access Token，确保凭证持久化；
- **剪贴板操作**：pyperclip，实现帮助文档一键复制，提升用户操作便捷性；
- **时间处理**：datetime与timedelta，计算周报统计周期、格式化时间显示，匹配游戏数据统计规则；
- **数据解析**：json，解析API返回的JSON响应，处理数据格式转换与异常。


## 二、核心类与初始化逻辑
### 1. 核心类定义：DFMQueryApp
代码以`DFMQueryApp`类为核心，继承自Toga的`App`类，封装所有功能模块，包括UI构建、配置管理、数据查询、结果格式化等，类结构清晰，职责统一。

### 2. 初始化方法（__init__）
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.config_file = None  # 配置文件路径，后续在startup中初始化
    self.openid = ""  # 用户唯一标识，用于API身份验证
    self.access_token = ""  # 用户访问令牌，用于API权限验证
```
- 调用父类构造方法，确保Toga App基础功能正常初始化；
- 初始化核心配置参数，`config_file`暂设为`None`，后续在`startup`方法中结合Toga的路径接口确定具体路径；
- `openid`与`access_token`初始化为空字符串，后续通过`load_config`方法从配置文件加载。


## 三、配置管理模块（load_config与save_config）
### 1. 加载配置（load_config）
负责从本地配置文件读取用户凭证，确保应用启动时自动恢复上次配置，核心逻辑如下：
```python
def load_config(self):
    if self.config_file is None:  # 若配置文件路径未初始化，重置凭证
        self.openid = ""
        self.access_token = ""
        return
    config = configparser.ConfigParser()
    if os.path.exists(self.config_file):  # 检查配置文件是否存在，避免FileNotFoundError
        config.read(self.config_file)
        if config.has_section('User'):  # 验证配置文件结构合法性
            # 读取OpenID与Access Token，设置fallback默认值为空字符串
            self.openid = config.get('User', 'openid', fallback='')
            self.access_token = config.get('User', 'access_token', fallback='')
```
- **容错设计**：通过`os.path.exists`检查文件存在性、`has_section`验证配置结构、`fallback`设置默认值，避免配置文件损坏或缺失导致应用崩溃；
- **数据清洗**：后续在`save_user_config`中通过`strip()`处理输入，确保加载的凭证无多余空格，减少API请求错误。

### 2. 保存配置（save_config）
负责将用户输入的OpenID与Access Token写入本地配置文件，实现凭证持久化：
```python
def save_config(self):
    config = configparser.ConfigParser()
    # 构建User section，存储当前凭证
    config['User'] = {
        'openid': self.openid,
        'access_token': self.access_token
    }
    # 以UTF-8编码写入文件，避免中文乱码（未来扩展中文配置时兼容）
    with open(self.config_file, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
```
- **覆盖写入**：每次保存时重新构建`User` section，确保配置始终为最新状态，避免旧值残留；
- **编码规范**：指定`encoding='utf-8'`，兼容未来可能的中文备注信息，提升代码扩展性。


## 四、UI构建模块（startup方法）
`startup`是Toga框架的核心方法，负责初始化主窗口与所有UI组件，构建完整交互界面，整体采用“盒子嵌套（Box）”结构，通过`COLUMN`（垂直排列）与`ROW`（水平排列）实现灵活布局，具体组件与逻辑如下：

### 1. 主窗口初始化
```python
self.main_window = toga.MainWindow(title="DFM查询工具 --Made by Xyihang", size=(700, 650))
main_box = toga.Box(style=Pack(direction=COLUMN, margin=8))  # 根容器，垂直排列所有组件
```
- 设定窗口标题与固定尺寸（700×650），兼顾显示完整性与桌面适配性；
- 根容器`main_box`设置`margin=8`，避免组件紧贴窗口边缘，提升视觉舒适度。

### 2. 标题组件
```python
title_label = toga.Label(
    "DFM游戏数据查询工具 --Made by Xyihang",
    style=Pack(font_size=18, font_weight="bold", margin_bottom=15)
)
main_box.add(title_label)
```
- 采用大字体（18号）与加粗样式，突出工具名称，`margin_bottom=15`与下方组件分隔，视觉层次清晰。

### 3. 用户配置区域（可折叠）
配置区域是用户输入凭证的核心模块，支持折叠/展开，节省界面空间，由“头部（标题+折叠按钮+保存按钮）”与“内容（输入框+状态显示）”组成：
#### （1）头部组件（header_box）
```python
header_box = toga.Box(style=Pack(direction=ROW, margin_bottom=5))
# 配置标题
config_label = toga.Label("用户配置", style=Pack(font_size=14, font_weight="bold"))
# 折叠/展开按钮，初始文本为"▲"（展开状态）
self.toggle_button = toga.Button(
    "▲",
    on_press=self.toggle_config,
    style=Pack(margin_left=10, padding=(5, 2), background_color="#607D8B", color="white", width=30)
)
# 保存按钮，蓝色背景突出操作
save_button = toga.Button(
    "保存",
    on_press=self.save_user_config,
    style=Pack(margin_left=5, padding=(5, 2), background_color="#2196F3", color="white")
)
header_box.add(config_label)
header_box.add(self.toggle_button)
header_box.add(save_button)
```
- **交互设计**：折叠按钮绑定`toggle_config`方法，点击切换显示状态；保存按钮绑定`save_user_config`，触发配置保存；
- **视觉区分**：按钮采用不同背景色（折叠按钮#607D8B、保存按钮#2196F3），引导用户识别操作功能。

#### （2）输入框容器（inputs_container）
包含OpenID与Access Token两个输入框，采用水平排列（ROW）确保标签与输入框对齐：
```python
inputs_container = toga.Box(style=Pack(direction=COLUMN))
# OpenID输入框
openid_box = toga.Box(style=Pack(direction=ROW, margin=2))
openid_label = toga.Label("OpenID:", style=Pack(width=70, margin_right=8, font_size=12))
self.openid_input = toga.TextInput(
    placeholder="请输入OpenID",
    value=self.openid,  # 加载已保存的OpenID
    style=Pack(flex=1, height=30)  # flex=1自适应宽度，height=30确保输入框高度统一
)
openid_box.add(openid_label)
openid_box.add(self.openid_input)

# Access Token输入框（结构与OpenID输入框一致）
token_box = toga.Box(style=Pack(direction=ROW, margin=2))
token_label = toga.Label("Access Token:", style=Pack(width=70, margin_right=8, font_size=12))
self.token_input = toga.TextInput(
    placeholder="请输入Access Token",
    value=self.access_token,
    style=Pack(flex=1, height=30)
)
token_box.add(token_label)
token_box.add(self.token_input)

inputs_container.add(openid_box)
inputs_container.add(token_box)
```
- **自适应布局**：输入框设置`flex=1`，随窗口宽度变化自动调整，避免窗口缩放导致布局错乱；
- **数据预填**：输入框`value`属性绑定已加载的`openid`与`access_token`，用户无需重复输入，提升操作效率。

#### （3）状态显示（status_box）
实时显示当前配置的用户信息，隐藏过长的OpenID，保护用户隐私：
```python
status_box = toga.Box(style=Pack(direction=ROW, margin_top=5))
self.user_info_label = toga.Label(
    f"用户: {self.openid[:10] + '...' if self.openid and len(self.openid) > 10 else (self.openid if self.openid else '未设置')}",
    style=Pack(font_size=10, color="gray")
)
status_box.add(self.user_info_label)
```
- **隐私保护**：OpenID长度超过10时截断并添加“...”，避免完整凭证泄露；
- **状态明确**：未配置时显示“未设置”，用户可快速确认配置状态，无需进入输入框检查。

#### （4）配置区域组装与初始状态
```python
# 可折叠的内容容器，包含输入框与状态显示
self.config_content = toga.Box(style=Pack(direction=COLUMN))
self.config_content.add(inputs_container)
self.config_content.add(status_box)

# 组装配置区域
self.config_box = toga.Box(style=Pack(direction=COLUMN, margin=5, background_color="#f5f5f5"))
self.config_box.add(header_box)
self.config_box.add(self.config_content)

# 初始状态为展开（config_visible=True）
self.config_visible = True
main_box.add(self.config_box)
```
- **视觉区分**：配置区域背景色设为`#f5f5f5`，与其他区域形成对比，便于用户识别功能模块；
- **初始状态**：默认展开配置区域，引导新用户完成凭证配置，降低使用门槛。

### 4. 查询类型选择器（query_type_box）
提供7种查询类型，用户可通过下拉选择需要查询的数据：
```python
query_type_box = toga.Box(style=Pack(direction=ROW, margin=5))
query_type_label = toga.Label("查询类型:", style=Pack(font_size=14, margin_right=10))
self.query_type = toga.Selection(
    items=["每日密码", "烽火地带收益Top3", "全面战场数据", "战场周报数据", "烽火周报数据", "特勤处状态", "货币资产查询"],
    style=Pack(flex=1)
)
query_type_box.add(query_type_label)
query_type_box.add(self.query_type)
main_box.add(query_type_box)
```
- **覆盖全场景**：查询类型涵盖日常游戏（每日密码）、战斗统计（全面战场数据）、周总结（战场周报）、资产管理（货币资产查询），满足玩家核心需求；
- **自适应宽度**：选择器设置`flex=1`，与输入框宽度保持一致，布局更规整。

### 5. 功能按钮容器（button_container）
包含“查询数据”与“获取帮助”两个核心按钮，水平排列确保操作便捷：
```python
button_container = toga.Box(style=Pack(direction=ROW, margin=5))
# 查询按钮，绿色背景突出核心操作
query_button = toga.Button(
    "查询数据",
    on_press=self.query_data,
    style=Pack(flex=1, margin_right=5, background_color="#4CAF50", color="white")
)
# 帮助按钮，橙色背景区分辅助功能
help_button = toga.Button(
    "获取帮助",
    on_press=self.get_help,
    style=Pack(flex=1, background_color="#FF9800", color="white")
)
button_container.add(query_button)
button_container.add(help_button)
main_box.add(button_container)
```
- **功能区分**：查询按钮（绿色）为核心操作，帮助按钮（橙色）为辅助功能，通过色彩引导用户操作优先级；
- **均等宽度**：两个按钮均设置`flex=1`，宽度均等，布局对称美观。

### 6. 结果显示区域
包含结果标题与多行文本框，用于展示查询结果，支持长文本滚动：
```python
# 结果标题
result_label = toga.Label("查询结果:", style=Pack(font_size=14, font_weight="bold", margin_top=10))
main_box.add(result_label)

# 结果文本框，只读模式，支持滚动
self.result_text = toga.MultilineTextInput(
    style=Pack(flex=1, margin=5, padding=10),
    readonly=True,
    placeholder="选择查询类型并点击查询按钮获取数据..."
)
main_box.add(self.result_text)
```
- **只读保护**：设置`readonly=True`，避免用户误修改结果，确保数据完整性；
- **提示引导**：占位文本提示用户操作流程，新用户可快速理解使用方法；
- **自适应高度**：`flex=1`设置让文本框占据剩余垂直空间，大量数据可通过滚动查看，无需担心显示不全。

### 7. 状态栏（status_label）
实时显示应用状态，如“就绪”“查询中”“查询成功”“错误”，提升用户操作感知：
```python
self.status_label = toga.Label("就绪", style=Pack(font_size=10, color="gray", margin_top=5))
main_box.add(self.status_label)
```
- **状态明确**：不同操作对应不同状态文本，用户可实时了解应用运行情况，避免盲目等待；
- **视觉弱化**：采用灰色小字体（10号），既传递信息又不干扰核心功能，视觉层级合理。

### 8. 窗口展示
```python
self.main_window.content = main_box
self.main_window.show()
```
- 将根容器`main_box`设为窗口内容，调用`show()`显示窗口，完成UI初始化。


## 五、配置交互功能（toggle_config与save_user_config）
### 1. 配置区域折叠/展开（toggle_config）
实现配置区域的显示与隐藏切换，节省界面空间，核心逻辑是“移除/添加配置内容容器”与“切换按钮文本”：
```python
def toggle_config(self, widget):
    try:
        if hasattr(self, 'config_visible') and self.config_visible:
            # 隐藏配置内容：从config_box中移除config_content
            self.config_box.remove(self.config_content)
            self.toggle_button.text = "▼"  # 按钮文本改为"▼"，提示可展开
            self.config_visible = False
        else:
            # 显示配置内容：向config_box中添加config_content
            self.config_box.add(self.config_content)
            self.toggle_button.text = "▲"  # 按钮文本改为"▲"，提示可折叠
            self.config_visible = True
    except Exception as e:
        print(f"切换配置区域时出错: {e}")
```
- **异常捕获**：通过`try-except`捕获操作异常，避免界面卡死，同时打印错误信息便于调试；
- **状态同步**：`config_visible`变量记录当前状态，确保按钮文本与显示状态一致，避免交互混乱。

### 2. 保存用户配置（save_user_config）
获取输入框内容，验证并保存配置，同时更新状态显示：
```python
def save_user_config(self, widget):
    try:
        # 获取输入框内容并去除多余空格
        self.openid = self.openid_input.value.strip()
        self.access_token = self.token_input.value.strip()
        
        # 验证OpenID非空（核心凭证，缺失会导致API请求失败）
        if not self.openid:
            self.result_text.value = "错误: OpenID不能为空"
            return
        
        # 保存配置到本地文件
        self.save_config()
        
        # 更新用户状态显示，反映最新配置
        self.user_info_label.text = f"用户: {self.openid[:10] + '...' if self.openid and len(self.openid) > 10 else (self.openid if self.openid else '未设置')}"
        
        # 显示成功消息，引导用户后续操作
        self.result_text.value = "配置保存成功！\n\n现在可以使用查询功能了。"
        self.status_label.text = "配置已保存"
    except Exception as e:
        # 异常时显示错误信息，帮助用户排查问题
        self.result_text.value = f"保存配置时发生错误: {str(e)}"
        self.status_label.text = "保存失败"
```
- **数据清洗**：通过`strip()`去除输入内容的前后空格，避免因空格导致的凭证错误；
- **前置验证**：检查OpenID非空，提前拦截无效配置，减少后续API请求失败；
- **反馈及时**：保存成功后更新状态标签与结果文本，用户可明确知晓操作结果，同时引导使用查询功能。


## 六、核心功能：数据查询（query_data方法）
`query_data`是数据查询的核心入口，负责根据用户选择的查询类型，构造API请求、处理响应、调用格式化方法，是连接UI与数据的关键模块，逻辑流程如下：

### 1. 初始化状态与前置验证
```python
def query_data(self, widget):
    try:
        # 更新状态栏为“查询中”，告知用户操作进度
        self.status_label.text = "正在查询中..."
        
        # 前置验证：检查OpenID是否配置，未配置则提示错误
        if not self.openid:
            self.result_text.value = "错误: 请先在用户配置区域设置OpenID并保存配置"
            self.status_label.text = "配置不完整"
            return
```
- **状态反馈**：查询开始即更新状态栏，避免用户因无反馈而重复点击；
- **前置拦截**：验证OpenID配置，减少无效API请求，提升效率并降低服务器压力。

### 2. 绑定查询类型与参数
根据用户选择的查询类型，确定API请求参数、查询函数（`query_func`）与特殊处理逻辑：
```python
        # 根据查询类型绑定参数与处理函数
        query_type = self.query_type.value
        if query_type == "每日密码":
            param_value = '{}'  # 无特殊参数，传递空JSON
            query_func = self.query_daily_secret  # 绑定每日密码查询函数
        elif query_type == "烽火地带收益Top3":
            param_value = '{"resourceType":"sol"}'  # 参数指定sol类型（烽火地带）
            query_func = self.query_sol_data  # 绑定烽火地带数据查询函数
        elif query_type == "全面战场数据":
            param_value = '{"resourceType":"mp"}'  # 参数指定mp类型（全面战场）
            query_func = self.query_mp_data  # 绑定全面战场数据查询函数
        elif query_type == "战场周报数据":
            # 计算最近一个周日日期（游戏周报统计周期为周一至周日）
            today = datetime.now()
            days_since_sunday = today.weekday() + 1  # weekday()返回0=周一，6=周日，+1后0=周日
            last_sunday = today - timedelta(days=days_since_sunday % 7)
            stat_date = last_sunday.strftime('%Y%m%d')  # 格式化为YYYYMMDD
            param_value = f'{{"statDate":"{stat_date}"}}'  # 参数传递统计日期
            query_func = self.query_weekly_data  # 绑定战场周报查询函数
        elif query_type == "烽火周报数据":
            # 同战场周报，计算最近周日日期
            today = datetime.now()
            days_since_sunday = today.weekday() + 1
            last_sunday = today - timedelta(days=days_since_sunday % 7)
            stat_date = last_sunday.strftime('%Y%m%d')
            param_value = f'{{"statDate":"{stat_date}"}}'
            query_func = self.query_sol_weekly_data  # 绑定烽火周报查询函数
        elif query_type == "货币资产查询":
            param_value = '{}'
            query_func = self.query_all_currencies  # 绑定货币资产查询函数（特殊：多请求）
            # 预定义三种货币ID与名称，后续查询使用
            self.currency_items = ['17020000010', '17888808889', '17888808888']  # 哈夫币, 三角券, 三角币
        else:  # 特勤处状态
            param_value = '{}'
            query_func = self.query_special_force_status  # 绑定特勤处状态查询函数
```
- **参数精准**：不同查询类型传递对应参数，如`resourceType`区分`sol`/`mp`，`statDate`指定周报统计日期，完全匹配游戏API要求；
- **周期匹配**：周报数据计算“最近一个周日”作为`statDate`，与游戏“周一至周日”的统计周期一致，确保数据无偏差；
- **特殊处理**：货币资产查询预定义三种货币ID，为后续多请求逻辑做准备。

### 3. 构造API请求参数（params）
根据查询类型构造不同的API请求参数（`iChartId`、`sIdeToken`、`method`等），这些参数是游戏API的核心标识，决定请求的接口与权限：
```python
        # 构造API请求参数（不同查询类型对应不同参数）
        if query_type == "每日密码":
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '316969',  # 每日密码接口标识
                'iSubChartId': '316969',
                'sIdeToken': 'NoOapI',  # 每日密码接口令牌
                'method': 'dfm/center.day.secret',  # 每日密码接口方法
                'source': '2',
                'param': param_value
            }
        elif query_type == "战场周报数据":
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '316968',  # 周报接口标识
                'iSubChartId': '316968',
                'sIdeToken': 'KfXJwH',  # 周报接口令牌
                'source': '5',
                'sArea': '36',
                'method': 'dfm/weekly.mp.record',  # 战场周报接口方法
                'param': param_value
            }
        elif query_type == "烽火周报数据":
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '316968',
                'iSubChartId': '316968',
                'sIdeToken': 'KfXJwH',
                'source': '5',
                'sArea': '36',
                'method': 'dfm/weekly.sol.record',  # 烽火周报接口方法
                'param': param_value
            }
        elif query_type == "货币资产查询":
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '319386',  # 货币资产接口标识
                'iSubChartId': '319386',
                'sIdeToken': 'zMemOt',  # 货币资产接口令牌
                'type': '3',
                'param': param_value
            }
        elif query_type == "特勤处状态":
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '365589',  # 特勤处状态接口标识
                'iSubChartId': '365589',
                'sIdeToken': 'bQaMCQ',  # 特勤处状态接口令牌
                'source': '2',
                'param': param_value
            }
        else:  # 烽火地带收益Top3、全面战场数据
            url = "https://comm.ams.game.qq.com/ide/"
            params = {
                'iChartId': '316969',
                'iSubChartId': '316969',
                'sIdeToken': 'NoOapI',
                'method': 'dfm/center.recent.detail',  # 日常数据接口方法
                'source': '2',
                'param': param_value
            }
```
- **接口匹配**：每个查询类型对应游戏官方的专属接口参数（`iChartId`、`sIdeToken`、`method`），确保请求合法有效；
- **统一URL**：所有请求使用同一基础URL（`https://comm.ams.game.qq.com/ide/`），符合游戏API的访问规则。

### 4. 构造请求头（headers）与发送请求
请求头包含Cookie信息，传递用户身份凭证，确保API识别用户身份：
```python
        # 构造请求头，通过Cookie传递用户凭证
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',  # API要求的表单格式
            'Cookie': f'openid={self.openid}; acctype=qc; appid=101491592; access_token={self.access_token}'
        }
        
        # 发送POST请求，设置超时10秒，避免网络异常导致卡死
        response = requests.post(url, params=params, headers=headers, timeout=10)
        
        # 调试信息：打印查询类型、HTTP状态码、响应前200字符，便于开发调试
        print(f"查询类型: {query_type}")
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应内容前200字符: {response.text[:200]}")
```
- **身份验证**：Cookie包含`openid`（用户唯一标识）、`access_token`（访问令牌）、`acctype=qc`（QQ账号类型）、`appid=101491592`（游戏应用ID），完全模拟游戏客户端请求，确保身份合法；
- **超时控制**：设置`timeout=10`，避免网络卡顿或服务器无响应导致应用卡死；
- **调试支持**：打印关键调试信息，便于开发人员排查API请求问题（如参数错误、状态码异常）。

### 5. 响应处理与结果展示
根据HTTP状态码、JSON解析结果、API返回状态，分步骤处理响应，最终调用格式化方法展示结果：
#### （1）HTTP状态码判断
```python
        # 处理HTTP响应
        if response.status_code == 200:  # HTTP请求成功
            try:
                # 解析JSON响应
                data = response.json()
            except json.JSONDecodeError as e:  # JSON解析失败（如响应非JSON格式）
                self.result_text.value = f"JSON解析错误: {str(e)}\n\n原始响应:\n{response.text}"
                self.status_label.text = "解析错误"
                return
```
- **解析容错**：捕获`JSONDecodeError`，显示原始响应文本，帮助用户与开发人员排查问题（如API返回HTML错误页）。

#### （2）API返回状态验证
游戏API通过`ret`与`iRet`字段标识请求是否成功（均为0表示成功）：
```python
            # 验证API返回状态（ret与iRet均为0表示成功）
            if data.get('ret') == 0 and data.get('iRet') == 0:
                jdata = data.get('jData', {})  # API核心数据存储在jData中
                data_content = jdata.get('data', {})  # 具体业务数据存储在jData.data中
```

#### （3）特殊处理：货币资产查询
货币资产查询需循环请求三种货币数据，单独处理：
```python
                # 特殊处理：货币资产查询（需多请求）
                if query_type == "货币资产查询":
                    # 调用query_all_currencies方法，循环查询三种货币
                    result = self.query_all_currencies(url, params, headers)
                    self.result_text.value = result
                    # 根据结果判断状态
                    if "查询失败" in result:
                        self.status_label.text = "查询失败"
                    else:
                        self.status_label.text = f"查询成功 - {datetime.now().strftime('%H:%M:%S')}"
```

#### （4）普通查询处理
其他查询类型通过`data_content.code`验证业务状态（0表示成功），调用绑定的查询函数与格式化方法：
```python
                else:
                    # 验证业务状态（code=0表示业务处理成功）
                    if data_content.get('code') == 0:
                        # 调用绑定的查询函数，获取业务数据
                        result = query_func(data_content.get('data', {}))
                        # 显示格式化后的结果
                        self.result_text.value = result
                        # 更新状态栏，添加查询时间戳
                        self.status_label.text = f"查询成功 - {datetime.now().strftime('%H:%M:%S')}"
                    else:  # 业务处理失败（如参数错误、权限不足）
                        self.result_text.value = f"API返回错误: {data_content.get('msg', '未知错误')}"
                        self.status_label.text = "查询失败"
```
- **业务容错**：通过`data_content.code`验证业务状态，避免业务错误导致后续处理崩溃；
- **时间戳**：查询成功时添加时间戳，用户可明确知晓数据时效性。

#### （5）API请求失败处理
```python
            else:  # API返回状态错误（如ret≠0或iRet≠0）
                self.result_text.value = f"请求失败: {data.get('sMsg', '未知错误')}"
                self.status_label.text = "查询失败"
        else:  # HTTP请求失败（如404、500）
            self.result_text.value = f"HTTP错误: {response.status_code}\n响应内容: {response.text}"
            self.status_label.text = "网络错误"
```
- **错误明确**：显示具体HTTP状态码与响应内容，便于排查网络问题（如DNS解析失败、服务器维护）。

### 6. 异常捕获
```python
    except Exception as e:  # 捕获所有未预料的异常（如网络连接超时、变量未定义）
        self.result_text.value = f"查询过程中发生错误: {str(e)}"
        self.status_label.text = "错误"
```
- **全局容错**：通过顶层`try-except`捕获所有异常，避免应用崩溃，同时显示错误信息，帮助问题排查。


## 七、数据查询与格式化方法
代码中每个查询类型对应“查询方法（`query_xxx`）”与“格式化方法（`format_xxx`）”，查询方法提取业务数据，格式化方法将数据转换为易读文本，以下解析核心方法：

### 1. 每日密码查询与格式化
#### （1）查询方法（query_daily_secret）
简单提取`data`中的密码列表，无复杂处理：
```python
def query_daily_secret(self, data):
    return self.format_daily_secret_result(data)
```

#### （2）格式化方法（format_daily_secret_result）
将密码数据按“地图名称-密码”格式展示，添加使用说明，提升可读性：
```python
def format_daily_secret_result(self, data):
    result = []
    if not data:  # 无数据时提示
        return "暂无每日密码数据"
    
    # 添加查询时间与标题
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result.append(f"=== 每日密码查询报告 ===")
    result.append(f"查询时间: {current_time}")
    result.append("")
    
    # 提取密码列表
    secret_list = data.get('list', [])
    if secret_list:
        result.append("=== 今日地图密码 ===")
        result.append("-" * 40)
        
        # 地图ID与名称映射，匹配游戏内显示
        map_names = {
            1: "零号大坝",
            2: "长弓溪谷",
            3: "巴克什",
            4: "航天基地",
            5: "潮汐监狱"
        }
        
        # 遍历密码列表，格式化每个地图的密码
        for secret_info in secret_list:
            map_id = secret_info.get('mapID', 0)
            map_name = map_names.get(map_id, f"未知地图({map_id})")  # 未知地图显示ID
            secret = secret_info.get('secret', '未知')
            result.append(f"【{map_name}】")
            result.append(f"地图ID: {map_id}")
            result.append(f"今日密码: {secret}")
            result.append("")
        
        # 添加使用说明，帮助用户理解密码用途
        result.append("=== 使用说明 ===")
        result.append("-" * 40)
        result.append("• 密码可用于进入对应地图的特殊区域")
        result.append("• 每日密码会在服务器时间00:00刷新")
        result.append("• 不同地图的密码可能不同")
        result.append("• 请妥善保管密码，避免泄露")
        result.append("")
        result.append("💡 提示: 点击密码区域可以复制密码内容")
    else:  # 无密码数据时提示可能原因
        result.append("今日暂无地图密码信息")
        result.append("")
        result.append("可能原因:")
        result.append("- 服务器维护中")
        result.append("- 密码尚未刷新")
        result.append("- 网络连接问题")
    
    return "\n".join(result)  # 列表转换为字符串，便于显示
```
- **地图映射**：将地图ID转换为游戏内名称（如1→“零号大坝”），用户无需记忆ID，提升易用性；
- **使用引导**：添加使用说明与提示，新用户可快速理解密码用途与刷新规则；
- **异常提示**：无数据时列出可能原因，帮助用户排查问题，降低操作焦虑。

### 2. 货币资产查询与格式化
货币资产查询需循环请求三种货币数据，是最复杂的查询类型之一：

#### （1）查询方法（query_all_currencies）
```python
def query_all_currencies(self, url, params, headers):
    result = []
    # 添加查询时间与标题
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result.append(f"=== 货币资产查询报告 ===")
    result.append(f"查询时间: {current_time}")
    result.append("")
    
    # 定义三种货币的ID与名称映射
    currency_items = [
        ('17020000010', '哈夫币'),
        ('17888808889', '三角券'),
        ('17888808888', '三角币')
    ]
    
    total_assets = 0  # 计算总资产（以哈夫币为基准）
    
    # 循环查询每种货币
    for item_id, currency_name in currency_items:
        try:
            # 复制参数并修改item字段（指定货币ID）
            query_params = params.copy()
            query_params['item'] = item_id
            
            # 发送POST请求，超时10秒
            response = requests.post(url, params=query_params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # 验证API状态
                if data.get('ret') == 0 and data.get('iRet') == 0:
                    jdata = data.get('jData', {})
                    data_content = jdata.get('data', [])
                    if isinstance(data_content, list) and len(data_content) > 0:
                        currency_data = data_content[0]
                        total_money = currency_data.get('totalMoney', '0')
                        money_amount = int(total_money)
                        total_assets += money_amount  # 累加总资产
                        
                        # 格式化当前货币信息
                        result.append(f"=== {currency_name} ===")
                        result.append(f"数量: {money_amount:,}")  # 千位分隔符，提升可读性
                        
                        # 根据数量添加资产状态评估，帮助用户判断资产水平
                        if money_amount > 1000000:
                            result.append("💰 资产状态: 富有")
                        elif money_amount > 500000:
                            result.append("💵 资产状态: 小康")
                        elif money_amount > 100000:
                            result.append("💸 资产状态: 一般")
                        else:
                            result.append("💳 资产状态: 需要积累")
                        result.append("")
                    else:
                        result.append(f"{currency_name}: 数据格式异常")
                        result.append("")
                else:
                    result.append(f"{currency_name}: 查询失败 - {data.get('sMsg', '未知错误')}")
                    result.append("")
            else:
                result.append(f"{currency_name}: HTTP错误 - {response.status_code}")
                result.append("")
        except Exception as e:
            result.append(f"{currency_name}: 查询错误 - {str(e)}")
            result.append("")
    
    # 添加总资产统计与整体状态评估
    result.append("=== 总资产统计 ===")
    result.append(f"三种货币总价值: {total_assets:,} 哈夫币")
    result.append("")
    
    if total_assets > 30000000:
        result.append("💰 总体资产状态: 非常富有")
    elif total_assets > 15000000:  # 此处原代码可能存在笔误，应为1500000（150万），按原代码保留
        result.append("💵 总体资产状态: 富有")
    elif total_assets > 5000000:  # 此处原代码可能存在笔误，应为500000（50万），按原代码保留
        result.append("💸 总体资产状态: 小康")
    else:
        result.append("💳 总体资产状态: 需要积累")
    
    return "\n".join(result)
```
- **多请求处理**：循环查询三种货币，每次修改`item`参数指定货币ID，实现“一站式”查询；
- **资产评估**：根据货币数量添加“富有/小康/一般”等状态标签，帮助用户快速判断资产水平；
- **总资产统计**：累加三种货币数量，提供整体资产视角，满足用户资产管理需求。

### 3. 烽火周报数据格式化（format_sol_weekly_result）
烽火周报数据维度最丰富，格式化方法涵盖基础统计、经济数据、战斗数据、特殊数据等，核心逻辑如下：
```python
def format_sol_weekly_result(self, data):
    result = []
    if not data:  # 无数据时提示
        return "本周暂无烽火周报数据"
    
    # 计算统计周期（周一至周日）
    today = datetime.now()
    days_since_sunday = today.weekday() + 1
    last_sunday = today - timedelta(days=days_since_sunday % 7)
    week_start = last_sunday - timedelta(days=6)
    result.append(f"=== 烽火周报数据 (统计周期: {week_start.strftime('%Y-%m-%d')} 至 {last_sunday.strftime('%Y-%m-%d')}) ===")
    result.append("")
    
    # 1. 基础统计（对局数、撤离率、在线时长等）
    total_sol_num = int(data.get('total_sol_num', 0))  # 本周对局数
    total_exacuation_num = int(data.get('total_exacuation_num', 0))  # 撤离成功数
    total_Quest_num = int(data.get('total_Quest_num', 0))  # 完成任务数
    total_Online_Time = int(data.get('total_Online_Time', 0))  # 总在线时长（秒）
    
    # 计算衍生指标
    evacuation_rate = (total_exacuation_num / total_sol_num * 100) if total_sol_num > 0 else 0  # 撤离率
    avg_online_time = total_Online_Time / total_sol_num if total_sol_num > 0 else 0  # 平均在线时长
    hours = total_Online_Time // 3600  # 总在线时长（小时）
    minutes = (total_Online_Time % 3600) // 60  # 总在线时长（分钟）
    
    result.append("=== 基础统计 ===")
    result.append(f"本周对局数: {total_sol_num:,}")
    result.append(f"撤离成功数: {total_exacuation_num:,}")
    result.append(f"撤离率: {evacuation_rate:.1f}%")  # 保留1位小数，提升精度
    result.append(f"完成任务数: {total_Quest_num:,}")
    result.append(f"总在线时长: {total_Online_Time:,}秒 ({hours}小时{minutes}分钟)")  # 转换为小时+分钟
    result.append(f"平均在线时长: {avg_online_time:.1f}秒")
    result.append("")
    
    # 2. 经济数据（收益、成本、利润等）
    gained_price = int(data.get('Gained_Price', 0))  # 总带出哈夫币
    consume_price = int(data.get('consume_Price', 0))  # 总带入哈夫币
    rise_price = int(data.get('rise_Price', 0))  # 总利润
    total_price = data.get('Total_Price', '')  # 每日仓库价值
    
    # 计算衍生指标
    avg_gain = gained_price / total_sol_num if total_sol_num > 0 else 0  # 平均每局收益
    profit_margin = (rise_price / consume_price * 100) if consume_price > 0 else 0  # 利润率
    
    result.append("=== 经济数据 ===")
    result.append(f"本周总带出哈夫币: {gained_price:,}")
    result.append(f"本周总带入哈夫币: {consume_price:,}")
    result.append(f"本周总利润: {rise_price:,}")
    result.append(f"平均每局收益: {avg_gain:,.0f}")  # 取整，符合货币单位
    result.append(f"利润率: {profit_margin:.1f}%")
    result.append("")
    
    # 解析每日仓库价值（格式：周一-20240501-100000,周二-20240502-150000...）
    if total_price:
        try:
            price_entries = total_price.split(',')
            result.append("=== 每日仓库价值 ===")
            for entry in price_entries:
                if '-' in entry:
                    parts = entry.split('-')
                    if len(parts) >= 3:
                        day = parts[0]
                        date = parts[1]
                        value = parts[2]
                        result.append(f"{day} ({date}): {int(value):,}")
        except:
            pass  # 解析失败不影响其他数据
        result.append("")
    
    # 3. 战斗数据（击杀、死亡、KD比等）
    total_kill_count = int(data.get('total_Kill_Count', 0))  # 总击杀数
    total_kill_player = int(data.get('total_Kill_Player', 0))  # 击败干员数
    total_kill_ai = int(data.get('total_Kill_AI', 0))  # 击杀AI数
    total_kill_boss = int(data.get('total_Kill_Boss', 0))  # 击杀BOSS数
    total_death_count = int(data.get('total_Death_Count', 0))  # 死亡次数
    total_rescue_num = int(data.get('total_Rescue_num', 0))  # 救援次数
    
    # 计算衍生指标
    kd_ratio = total_kill_count / total_death_count if total_death_count > 0 else total_kill_count  # KD比
    survival_rate = ((total_sol_num - total_death_count) / total_sol_num * 100) if total_sol_num > 0 else 0  # 生存率
    
    result.append("=== 战斗数据 ===")
    result.append(f"总击杀数: {total_kill_count:,}")
    result.append(f"击败干员数: {total_kill_player:,}")
    result.append(f"击杀AI数: {total_kill_ai:,}")
    result.append(f"击杀BOSS数: {total_kill_boss:,}")
    result.append(f"死亡次数: {total_death_count:,}")
    result.append(f"KD比: {kd_ratio:.2f}")  # 保留2位小数，符合游戏数据习惯
    result.append(f"生存率: {survival_rate:.1f}%")
    result.append(f"救援次数: {total_rescue_num:,}")
    result.append("")
    
    # 4. 特殊数据（百万撤离、被鳄鱼杀死、搜索鸟巢等）
    gained_price_overmillion_num = int(data.get('GainedPrice_overmillion_num', 0))  # 百万撤离场次
    teammate_price_overzero_num = int(data.get('TeammatePrice_overzero_num', 0))  # 队友价格为正次数
    kill_by_crocodile_num = int(data.get('Kill_ByCrocodile_num', 0))  # 被鳄鱼杀死次数
    search_birdsnest_num = int(data.get('search_Birdsnest_num', 0))  # 搜索鸟巢数
    mandel_brick_num = int(data.get('Mandel_brick_num', 0))  # 曼德尔砖破译数
    use_keycard_num = int(data.get('use_Keycard_num', 0))  # 消耗钥匙数
    total_mileage = int(data.get('Total_Mileage', 0))  # 总里程（米）
    rank_score = int(data.get('Rank_Score', 0))  # 排位分数
    
    result.append("=== 特殊数据 ===")
    result.append(f"百万撤离场次: {gained_price_overmillion_num:,}")
    result.append(f"队友价格为正次数: {teammate_price_overzero_num:,}")
    result.append(f"被鳄鱼杀死次数: {kill_by_crocodile_num:,}")
    result.append(f"搜索鸟巢数: {search_birdsnest_num:,}")
    result.append(f"曼德尔砖破译数: {mandel_brick_num:,}")
    result.append(f"消耗钥匙数: {use_keycard_num:,}")
    result.append(f"总里程: {total_mileage:,}米")
    result.append(f"排位分数: {rank_score:,}")
    result.append("")
    
    # 5. 干员使用情况（解析格式：{'ArmedForceId':40005,'inum':2}#{'ArmedForceId':20004,'inum':10}...）
    armed_force_info = data.get('total_ArmedForceId_num', '')
    armed_force_data = []
    if armed_force_info and armed_force_info.startswith('{'):
        try:
            entries = armed_force_info.split('#')
            for entry in entries:
                if entry.startswith('{') and entry.endswith('}'):
                    parts = entry.strip('{}').split(',')
                    force_id = parts[0].split(':')[1] if len(parts) > 0 else '未知'
                    inum = parts[1].split(':')[1] if len(parts) > 1 else '0'
                    armed_force_data.append((force_id, int(inum)))
        except:
            pass
    
    # 干员ID与名称映射，匹配游戏内显示
    force_map = {
        '10007': '红狼', '10010': '威龙', '10011': '无名',
        '20003': '蜂医', '20004': '蛊', '30008': '牧羊人',
        '30011': '比特', '40005': '露娜', '40010': '骇爪', '10012': '疾风'
    }
    
    if armed_force_data:
        result.append("=== 干员使用情况 ===")
        # 按使用场次降序排列，显示使用最多的干员
        for force_id, inum in sorted(armed_force_data, key=lambda x: x[1], reverse=True):
            force_name = force_map.get(force_id, f'干员{force_id}')
            result.append(f"{force_name} (ID:{force_id}): {inum}场")
        result.append("")
    
    # 6. 地图分布（解析格式：{'MapId':2202,'inum':6}#{'MapId':1901,'inum':5}...）
    map_info = data.get('total_mapid_num', '')
    map_data = []
    if map_info and map_info.startswith('{'):
        try:
            map_entries = map_info.split('#')
            for entry in map_entries:
                if entry.startswith('{') and entry.endswith('}'):
                    parts = entry.strip('{}').split(',')
                    map_id = parts[0].split(':')[1] if len(parts) > 0 else '未知'
                    inum = parts[1].split(':')[1] if len(parts) > 1 else '0'
                    map_data.append((map_id, int(inum)))
        except:
            pass
    
    if map_data:
        result.append("=== 地图分布 ===")
        # 按场次降序排列，显示前5个高频地图
        for map_id, inum in sorted(map_data, key=lambda x: x[1], reverse=True)[:5]:
            result.append(f"地图ID {map_id}: {inum}场")
        result.append("")
    
    # 7. 高价值物品（解析格式：{'itemid':13120000256,'inum':1,'auctontype':配件,'quality':5.0,'iPrice':25534.0}...）
    carry_out_highprice_list = data.get('CarryOut_highprice_list', '')
    if carry_out_highprice_list and len(carry_out_highprice_list) > 10:
        try:
            items = carry_out_highprice_list.split('#')
            if items:
                result.append("=== 本周带出高价值物品 (前10个) ===")
                # 显示前10个高价值物品
                for i, item in enumerate(items[:10], 1):
                    if item.startswith('{') and item.endswith('}'):
                        parts = item.strip('{}').split(',')
                        item_id = ''
                        price = ''
                        for part in parts:
                            if 'itemid:' in part:
                                item_id = part.split(':')[1]
                            elif 'iPrice:' in part:
                                price = part.split(':')[1]
                        if item_id and price:
                            result.append(f"{i}. 物品ID: {item_id}, 价值: {float(price):,.0f}")
        except:
            pass
        result.append("")
    
    return "\n".join(result)
```
- **维度全面**：覆盖基础统计、经济数据、战斗数据、特殊数据、干员使用、地图分布、高价值物品7大维度，满足玩家深度分析需求；
- **衍生指标**：计算撤离率、KD比、利润率等衍生指标，帮助玩家挖掘数据背后的游戏表现；
- **数据解析**：处理多种非标准JSON格式（如`#`分隔的字符串），通过`try-except`确保解析失败不影响其他数据；
- **用户友好**：干员ID映射为游戏内名称，时间转换为“小时+分钟”，数值添加千位分隔符，提升数据可读性。


## 八、辅助功能：获取帮助（get_help方法）
`get_help`方法负责获取帮助文档并复制到剪贴板，提供用户操作指引与问题排查方案，核心逻辑如下：
```python
def get_help(self, widget):
    try:
        # 更新状态栏，告知用户正在获取帮助
        self.status_label.text = "正在获取帮助文档..."
        
        # 帮助文档URL（腾讯文档）
        help_url = "https://docs.qq.com/document/DS2hWc29pSGVIa3dM"
        # 发送GET请求获取文档页面，超时15秒
        response = requests.get(help_url, timeout=15)
        
        if response.status_code == 200:  # HTTP请求成功
            try:
                # 提取页面内容与标题
                page_content = response.text
                # 正则匹配HTML标题（<title>标签内容）
                import re
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', page_content, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else "DFM查询工具帮助文档"
                
                # 构建帮助文档内容，涵盖使用说明、查询类型、功能特性、常见问题
                help_content = f"{title}\n\n"
                help_content += f"文档链接: {help_url}\n\n"
                help_content += "=== DFM查询工具使用说明 ===\n\n"
                help_content += "1. 用户配置：\n"
                help_content += "   - 输入您的OpenID和Access Token\n"
                help_content += "   - 点击保存按钮保存配置\n\n"
                help_content += "2. 查询功能：\n"
                help_content += "   - 选择查询类型\n"
                help_content += "   - 点击查询数据获取结果\n\n"
                help_content += "3. 支持的查询类型：\n"
                help_content += "   - 每日密码：获取当日地图密码\n"
                help_content += "   - 烽火地带收益Top3：查看昨日高价值物品\n"
                help_content += "   - 全面战场数据：查看MP模式战绩\n"
                help_content += "   - 战场周报数据：查看本周MP统计\n"
                help_content += "   - 烽火周报数据：查看本周Sol统计\n"
                help_content += "   - 特勤处状态：查看特勤处设施状态\n"
                help_content += "   - 货币资产查询：查看游戏货币余额\n\n"
                help_content += "4. 功能特性：\n"
                help_content += "   - 可折叠的用户配置区域\n"
                help_content += "   - 自动物品名称识别\n"
                help_content += "   - 详细的数据格式化显示\n"
                help_content += "   - 错误处理和状态提示\n\n"
                help_content += "5. 常见问题：\n"
                help_content += "   - 如查询失败，请检查网络连接\n"
                help_content += "   - 如显示配置错误，请重新输入凭证\n"
                help_content += "   - 可折叠配置区域以获得更大查看空间\n\n"
                help_content += f"完整文档请访问：{help_url}"
            
            except Exception as extract_error:  # 提取标题或构建内容失败
                # 提供基础帮助内容，确保用户仍能获取核心信息
                help_content = "DFM查询工具帮助文档\n\n获取详细文档：\n" + help_url + "\n\n此工具用于查询烽火地带游戏数据，支持多种查询类型。如需详细使用说明，请访问上述链接。"
            
            # 复制帮助内容到剪贴板
            try:
                pyperclip.copy(help_content)
                # 更新状态栏与结果文本，告知用户复制成功
                self.status_label.text = "帮助文档已复制到剪贴板"
                self.result_text.value = "=== 帮助文档获取成功 ===\n\n✅ 帮助文档已自动复制到剪贴板\n📖 您可以直接粘贴到文本编辑器中查看\n\n🌐 文档链接：\n" + help_url + "\n\n💡 提示：\n• 如果剪贴板内容为空，请手动访问上方链接\n• 文档包含详细的使用说明和常见问题解答"
            
            except Exception as clipboard_error:  # 剪贴板操作失败（如系统权限限制）
                # 提示用户手动访问链接，提供替代方案
                self.status_label.text = "剪贴板操作失败，请手动访问"
                self.result_text.value = "=== 帮助文档 ===\n\n⚠️ 自动复制到剪贴板失败\n\n🌐 请手动访问文档链接：\n" + help_url + "\n\n📋 您也可以复制下面的链接：\n" + help_url + "\n\n💡 建议将文档链接保存到书签以便快速访问"
        
        else:  # HTTP请求失败（如文档链接失效）
            self.status_label.text = "无法访问帮助文档"
            self.result_text.value = f"=== 获取帮助文档失败 ===\n\n❌ HTTP错误: {response.status_code}\n\n🌐 请手动访问：\n" + help_url + "\n\n💡 可能原因：\n• 网络连接问题\n• 服务器暂时不可用\n• 文档链接已更改"
    
    except Exception as e:  # 捕获所有异常（如网络连接超时）
        self.status_label.text = "获取帮助失败"
        self.result_text.value = f"=== 获取帮助文档时发生错误 ===\n\n🔧 错误信息: {str(e)}\n\n🌐 请手动访问文档链接：\nhttps://docs.qq.com/document/DS2hWc29pSGVIa3dM\n\n💡 建议：\n• 检查网络连接\n• 稍后重试\n• 或者手动访问文档链接"
```
- **双来源保障**：优先从腾讯文档获取最新帮助内容，提取失败时使用本地预设内容，确保无网络或链接失效时仍能提供基础指引；
- **剪贴板便捷**：自动复制帮助内容到剪贴板，用户无需手动选中复制，提升操作效率；
- **容错完善**：覆盖“HTTP请求失败、剪贴板操作失败、网络异常”等场景，提供手动访问链接的替代方案，避免功能完全失效；
- **内容实用**：帮助文档涵盖使用流程、查询类型详解、常见问题，针对性解答用户高频疑问，降低使用门槛。


## 九、代码入口（main函数）
代码通过`main`函数初始化应用并启动主循环，是应用的入口点：
```python
def main():
    # 创建DFMQueryApp实例，指定应用名称与唯一标识
    return DFMQueryApp("烽火地带查询工具", "com.dfm.query")

if __name__ == "__main__":
    # 初始化应用并启动主循环（Toga框架核心，处理UI事件与交互）
    app = main()
    app.main_loop()
```
- **应用标识**：`com.dfm.query`为应用唯一标识，用于Toga框架区分不同应用；
- **主循环**：`app.main_loop()`启动UI事件循环，处理用户点击、输入等交互，确保应用持续运行。


