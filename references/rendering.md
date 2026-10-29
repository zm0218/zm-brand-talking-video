# 时间轴与渲染

## 依赖与路径

`video.py` 使用Python标准库和完整FFmpeg/libass。优先读取 `ZM_VIDEO_FFMPEG`，否则使用PATH；ffprobe可通过 `ZM_VIDEO_FFPROBE` 指定，也可位于FFmpeg同目录或PATH。脚本实际运行二进制并检查字幕、叠加、留边和响度滤镜，不自动安装或升级。

JSON中的素材路径相对JSON文件所在目录解析，也可用绝对路径。包含个人路径的运行结果应留在本次私有工作目录。

`transcribe.py` 在支持SpeechTranscriber的macOS上调用已有简体中文模型；Swift编译缓存和音频写入指定输出目录。没有模型时报告错误，不自动下载；沙箱不可见需与实际未安装区分。输出JSONL含句段和 `words[]` 的实际起止秒数。转写结果须校对。

## JSON字段

| 字段 | 含义 |
|---|---|
| `brief.confirmed` | 本次核心目标和关键事实已确认，不能为绕过检查擅自改为true |
| `resolution` | `[1080,1920]`、`[1920,1080]`、`[2160,3840]`、`[3840,2160]` |
| `fps` | 30 |
| `theme` | warm / blue / meme / natural |
| `font_family` / `font_file` | 本机可用字体名／可选字体路径；字体文件仅复制到本次渲染目录 |
| `clips[]` | 数组顺序即成片顺序，每项绑定source与in/out |
| `captions[]` / `titles[]` | 成片时码start/end，text可用 `[[重点]]`；显式换行最多两行 |
| `bgm` | 可选 `{path, gain_db}`，gain_db为-36至-12，默认-20；须确认使用权 |

clip字段：

- `source`、`in`、`out`：原声及默认画面的来源，秒数，out不含。片段时长对齐30fps。
- `layout`：`full` 或 `inset`，后者约84%矩形缩窗。
- `fit`：`cover` 默认等比裁切填满，或 `contain` 等比留边保留全部构图。contain时zoom须为1。
- `zoom`：1–1.3；`focus_x/y`：0–1，默认0.5，用于cover裁切位置。
- `source_has_captions`：原视频有烧录字幕时设true，阻止重叠的新字幕。
- `visual`：可选B-roll文件。`visual_type:image` 默认图片；设为 `video` 时可用视频。
- `visual_in`：视频B-roll的起点，默认0。B-roll必须长于所覆盖片段，不自动循环补足。
- `visual_has_captions`：替换画面有烧录字幕时设true。visual只替换画面，音频仍取source。

字幕和标题：

- 使用成片秒数，不直接填源片时码。同轨不允许重叠。
- 字幕每行最多14字符、标题每行最多10字符，最长两行；长英文名按语义单独安排。
- `x/y` 是画布比例锚点，`size` 是1080p对应方向的基础字号。4K由ASS画布等比缩放。
- 竖屏ASS画布为1080×1920，横屏为1920×1080。不要直接把竖屏字号和坐标拉伸到横屏。

## 时间映射

源片段 `[in,out)` 放在成片offset，源词t映射为 `offset + t - in`。按逐词时间戳和语义分句，剪点对齐完整词或换气点；不能用字数比例伪造精确时码。

语音识别的品牌、姓名、同音词和起音可能出错。保留原始转写与修订映射；字幕时间映射正确不等于已经逐字听审。剪掉一个片段时，同时更新后续字幕和标题时码。

## 输出与检查

渲染会拒绝覆盖非空目录、未确认brief、源时长越界、同轨重叠字幕及二次烧录字幕。

- `review.mp4`：H.264 / AAC192kbps / 48kHz / 30fps / yuv420p / BT.709 / faststart。
- `job.snapshot.json`：原配置；`source-map.json`：解析后的源路径、实际片段时长和成片时间。
- `captions.ass`：字幕与标题；`qa.json`：输出规格与“待完整看听”状态。
- `check-*.jpg`：起中尾静帧，仍需检查主要切点。
- `segment-*.mkv`、`base.mkv`：中间工程，不当作最终交付。

片段先用PCM保存音频，最终导出做响度规范化；它不自动去除所有噪声，也不保证不同人物主观音量一致。源收音有问题时应先定位，再单独处理和听审。

对实际MP4重测响度，可将下列 `ffmpeg` 替换为本机已配置的完整路径：

```bash
ffmpeg -hide_banner -i review.mp4 -vn -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -
```

技术目标约-16LUFS、TP≤-1.5dBTP，记录编码偏差。完整解码、ASR成功与截图检查不能代替连续看听。
