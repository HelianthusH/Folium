# VoiceCard 独立录音与 Windows 语音输入器

Folium 项目许可：原创软件采用 [MIT](LICENSE.md)，原创硬件设计采用 CERN-OHL-S v2，原创文档采用 CC BY 4.0。固件、Windows 便携助手与离线模型的第三方许可和来源见 [随包声明](THIRD_PARTY_NOTICES.md)。发布包中附有对应的许可全文。

先看 [逐针接线、BOM 与外壳装配](hardware/ASSEMBLY.md)。第一次试机只需 Sense 主板、3.3 V 卡座、FAT32 卡、两个常开按键和 USB 电源。完整电池版的物料预算为 **¥211**。工作区含可刷固件、Windows 便携助手和制板文件。实机测试请用 [验收记录表](docs/ACCEPTANCE.md)。

## 一、总体设计

|模块|输入、职责与输出|
|---|---|
|XIAO Sense 与固件|板载 PDM 麦克风以标称 16 kHz、单声道、16 位采集。驱动提供缓冲，应用按块编码。录音键切换启停，绿色表示采集、红色表示故障。|
|microSD 与 RTC|独立写 WAV、逐段清单及带 CRC 的双份状态记录。离线时间来源为 PCF8563，录音长度来源为采样计数。|
|USB / BLE|录音期间按住听写键，固件将同一批新录音块传给已订阅的助手。单独使用听写键时也会保存短会话。|
|Windows 11 助手|本地中英流式识别、字幕、草稿记录和输入目标绑定。WorkBuddy、Codex 使用前台窗口与输入控件，Claude Code 使用助手启动的专用控制台。用户可混合键入、听写和修改，最后自行发送。|
|供电|USB-C 或 Qi 接收片供 BQ24074，电池接 BAT，电源路径输出经 5 V 升压供主板。两种充电入口共用一个面板插座。|

状态依次为 IDLE、STARTING、RECORDING、STOPPING、STOPPED。启动检查卡和容量并初始化麦克风，停止时排空可读缓冲、定稿当前 WAV、写清单。遇错进入 ERROR。正常断电前停录并等绿灯熄灭。意外断电后依双副本日志验证末段、修正文件长度，再依据录音意图续录。断电期间没有采样，以 gap_after 登记未知间隔。

## 二、接口契约

详情与调用示例见 [接口协议](docs/PROTOCOL.md)。电脑脚本通过当前用户的 Windows 命名管道调用助手，助手再通过 USB CDC 或已加密的 BLE GATT 链路访问设备。首次绑定用 USB 和实体双键确认。无需智能体 API 密钥。

## 三、实现产物

|入口|用途|
|---|---|
|[voicecard.uf2](release/voicecard.uf2) · [固件源码](firmware/src/main.c)|Zephyr 4.2.0，板型 xiao_ble/nrf52840/sense|
|[Windows 助手](release/VoiceCard/VoiceCard.exe) · [桌面源码](desktop/app.py)|解压后保留同目录的 _internal、models 和 config。双击运行，关闭主窗口后可从托盘再次打开。|
|[配置](config/voicecard.json) · [启动脚本](scripts/run.ps1)|首次启动复制到 %LOCALAPPDATA%\VoiceCard\voicecard.json。改 USB 端口、连接方式或可执行文件白名单后，从托盘退出并重启。|
|[载板 PCB](hardware/carrier/carrier.kicad_pcb) · [Gerber＋钻孔](hardware/carrier/carrier-gerber.zip)|2×7 插座转接板，外围模块按装配表接线|
|[模块级接线原理图](hardware/schematic/assembly.sch)|KiCad 可编辑原理图，打开时保留同目录符号库。面板 VBUS_IN 与本地 V5_LOCAL 分网。|
|[底壳](hardware/enclosure/base.stl) · [盖板](hardware/enclosure/lid.stl) · [可编辑外壳](hardware/enclosure/case.scad)|按所购模块微调开孔、固定位置与高度|
|[归档逻辑](desktop/archive.py) · [测试](tests/test_voicecard.py)|按卡或 USB 查询、恢复导出、SHA-256 核验|

### 保存、空间与导出

默认 IMA ADPCM WAV，每块 256 B 存 505 个采样点，静音照常记录。码流约 29.2 MB/小时，48 小时约 1.40 GB。PCM16 逐采样保存，48 小时约 5.53 GB。以上是十进制容量，另有头部、清单和 FAT 开销。录音约每 5 分钟在完整块边界切段，录音时只保留有限的缓冲。16 GB 卡留足两天容量。

会话目录为 REC/YYYY/MM/DD/十六位会话号/，日期取会话开始 UTC，跨午夜仍属于同一会话。RTC 失效时使用 REC/UNSYNCED/。0001.wav 对应 0001.json，字段含设备号、固件版本、会话号、段号、UTC、时钟可信度、编码、采样位置、样本数、字节数、SHA-256、结束原因及缺口。设备按目录与清单检索，助手重建 SQLite 时间索引。

每次开新段检查空间。低于 512 MiB 时依段末 UTC 从最老的段清理，只清理已封存且超过 48 小时的段，未校时的段保留。空间仍不足时进入 NO_SPACE。导出先写 .partial 目录，再核对长度和整段 SHA-256；通过后发布 export-… 目录及 SHA256.json。导出中断后用相同参数重试，校验失败的副本保留 .corrupt 扩展名。卡上最近 48 小时的保护依赖可信 RTC，校时前先确认电脑时间。

## 四、实施计划与首次使用

1. **独立试录。** 按装配表焊接 SPI 卡座、按键，插入单分区 FAT32 卡。用数据线接 XIAO，快速双击 RESET 进入 UF2 引导盘，把 release/voicecard.uf2 复制到引导盘，等主板重启。接独立 USB 电源，按录音键开始，过 10 秒再按一次。确认绿灯熄灭后断电、取卡播放 WAV。首次无 RTC 时间时到 UNSYNCED 目录查找。若无引导盘，先核对数据线、Sense 型号及原厂 UF2 引导程序。
2. **接便携供电。** 先限流测电源路径，再接电池和 Qi，测单独录音及录音加 BLE 两档电池端平均电流。预算为 44 小时独立录音加 4 小时听写，总耗电上限 2400 mAh。记录电芯与模块温升后再合壳。
3. **启用听写。** Windows 解压完整目录，运行 release/VoiceCard/VoiceCard.exe。插 USB，必要时指定 COM 口。同时按两键后松开，30 秒内点“USB 绑定”。回到助手查状态并确认时钟。点“绑定 workbuddy”或“绑定 codex”后在 4 秒内点击相应软件的草稿输入框。Claude Code 先运行 scripts/claude.ps1，再选择 claude_code 并切到专用控制台。按住听写键说话，松开后检查草稿。若输入框不支持辅助功能，用“打开草稿记录”复制定稿。
4. **无线使用和归档。** USB 绑定成功后有 120 秒首次蓝牙配对窗口。此期间在 Windows 蓝牙设置中配对 VoiceCard，然后把用户配置 transport 改为 ble 并重启助手。已配对电脑以后可直接重连。超时请重新双键确认并执行 USB 绑定，必要时先在 Windows 移除旧的配对。多台设备时指定 ble_address。批量导出切回 USB，或停录、断电后用读卡器。定版前完成 48 小时整机测试和三款应用的 USB、BLE 六组测试。

在项目根目录的 PowerShell 执行。脚本中的 E: 替换为卡的盘符。

```powershell
.\scripts\status.ps1
.\scripts\start.ps1 -Codec ima
.\scripts\stop.ps1
.\scripts\list.ps1 --card E:\
.\scripts\export.ps1 -Card E:\ -Dest D:\VoiceExports
.\scripts\verify.ps1 -Dest D:\VoiceExports\export-具体批次号
```

源码模式需要 Python 3.10 x64。运行 scripts/install.ps1 安装锁定版本的依赖及模型，然后执行 scripts/run.ps1。固件构建需要 ARM 嵌入式工具链、Git、CMake、Ninja、west 和 Zephyr 指定模块。Windows 下构建源和 Zephyr 工作树使用纯英文物理路径以兼容工具链。模型首次下载时校验上游归档的 SHA-256，便携版已带模型。

## 五、验证验收

主机测试已覆盖读卡检索、坏段检测、断点续传、草稿去重、命名管道和离线模型。续航、USB/Qi 充电、麦克风声音、掉电损失、蓝牙吞吐以及三款智能体版本兼容性须在装配后填写。[验收步骤与已知边界](docs/ACCEPTANCE.md)
