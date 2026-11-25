# 接口契约 v1

助手的脚本接口使用当前用户 SID 隔离的本机命名管道，名称为 \\.\pipe\VoiceCard-<SID>-control。一次写入一条 UTF-8 JSON，单请求不超过 60000 字节。返回 {"ok":true,"result":...} 或 {"ok":false,"error":"错误原因"}。同进程内的字幕订阅由桌面助手管理。命令行示例为 VoiceCard.exe record.start --codec ima。用户可继续直接用键盘编辑。

|操作|请求字段|成功 result|
|---|---|---|
|device.bind|无，先 USB 双键解锁|bound，同时校时并订阅|
|device.status|无，连接由配置选定|device_id、state、session_id、first_free_sample、free_bytes、utc、clock_trusted、battery_percent、last_error；当前无电量计，电量为 null|
|device.set_time|utc，Unix 秒，省略为电脑当前 UTC|set|
|record.start|codec 为 ima 或 pcm16，可选 request_id|字符串“会话号 状态 UTC”|
|record.stop|session_id，省略则查询活动会话，可选 request_id|同上|
|audio.subscribe|订阅当前链路上的新听写块|ima 16000 505|
|sessions.list|可选 session_id、since、until、page，从 0 开始|每页最多 50 条封存段元数据，时间范围取左闭右开相交段|
|sessions.export|可选同一组过滤条件，必填 dest|校验完成的导出目录；接续使用相同选择和目的地，导出单位为整段|
|adapter.bind|app 为 workbuddy、codex、claude_code|该助手进程内的 target_id|
|adapter.insert|target_id、utterance_id、text|inserted、already_inserted 或 draft_saved；相同编号不同文本返回 ID_CONFLICT|

USB CDC 115200、DTR 置位，实际数据速率由 USB 决定。BLE 主服务 UUID 为 4cb30000-7873-46d7-884a-b66c77636431，末组相同、首组尾数字 1 的特征接收控制写入，2 的特征通过通知复用返回和音频。必须重组通知至换行后再解析。首次 USB 物理绑定存一个随机 128 位十六进制令牌，主板存 NVS，Windows 用当前用户 DPAPI 保存。BLE 控制和 CCC 需要加密，订阅及控制还要校验令牌。USB 实体确认并绑定成功后清除旧的设备端配对，并开放 120 秒的 BLE 首次配对窗口；成功配对即关闭窗口。之后使用已有 bond 重连，应用命令仍验证同一令牌。

```text
V1 <request_id> <token> <op> [args...] LF
R <request_id> OK <value> LF
R <request_id> ERR <code> LF
B <session_id> <utterance_hex> <first_sample> LF
A <session_id> <utterance_hex> <first_sample> <crc32_hex> <base64_256B_IMA> LF
E <session_id> <utterance_hex> <end_sample_exclusive> LF
```

固件还支持 talk 和 block。talk 传 会话号-听写号 或 latest，返回该听写的标识、起始采样、结束采样（开区间）及是否已封闭。block 传上述标识与绝对采样位置，返回 CRC32 和 Base64 IMA 块。位置从听写起点按 505 递增。最近 16 次听写在本次开机内可定位，超出返回 RANGE_UNAVAILABLE。助手会在恢复已开始的听写时补块，恢复定稿交给用户查看。

设备基本操作为 pair、status、time、start、stop、sub、ls、get。USB 的 ls 按目录和条目序号枚举；get 按相对路径和字节偏移读最多 720 B，返回 CRC32 和 Base64。设备对最近 16 个启停请求缓存应答，限定同一次启动周期。块序由 first_sample/505 推得，同一流内用采样位置检测缺块。音频配置、目标软件和认证令牌均由助手管理。

|条件 / 代码|设备或助手行为与操作|
|---|---|
|DEVICE_UNAVAILABLE|检查 Sense、卡座、供电或 RTC。绿灯熄灭红灯亮时停机，重新插卡、上电，让固件先恢复日志。|
|NO_SPACE / WRITE_FAILED|仅回收超期段。停录断电后导出可读文件，检查卡及其供电，必要时换卡。|
|CORRUPT / EXPORT_FAILED|保存原始卡与已复制字节，软件提示问题路径。校验失败副本进入 .corrupt；断链重连后用同一组条件重试。|
|AUTH_REQUIRED / LINK_LOST / USB_REQUIRED|检查传输配置、端口及绑定。掉线后助手尝试重连，设备继续写卡；缺块定稿留草稿。USB 负责封存文件传输。|
|SESSION_MISMATCH / ID_CONFLICT / INVALID|查询当前会话，给不同操作分配不同请求号，核对字段和编码。|
|TARGET_LOST / INPUT_DENIED|重新绑定前台可编辑控件或专用控制台。插入失败时保存草稿供手动恢复。|
|麦克风权限|此实现从设备传输音频，不打开 Windows 麦克风。遇系统拒绝访问时检查串口占用、蓝牙开关、配对与目标窗口的运行权限。|

[WorkBuddy](https://www.codebuddy.cn/work/) · [Codex Windows](https://developers.openai.com/codex/windows/) · [Claude Code](https://code.claude.com/docs/en/interactive-mode) · [离线模型资料](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/index.html)
