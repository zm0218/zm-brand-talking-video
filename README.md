# zm的品牌口播视频剪辑

把真人口播、双人访谈和活动素材，整理成有内容逻辑的品牌视频。

这是一套供 Codex 等支持 `SKILL.md` 的助手使用的剪辑工作流，附带可在本机运行的 Python / FFmpeg 工具。支持多段素材合为一条完整视频，也支持按需求拆分；不预设60秒上限。

**Skill 标识：`zm-brand-talking-video` · 许可证：[MIT](LICENSE)**

## 可以做什么

- 盘点原素材，使用已安装的 macOS 中文模型本地转写。
- 结合语义选择片段，删去重录、拍摄讨论、口误和重复，保留完整观点。
- 制作9:16竖屏或16:9横屏；支持1080p及按需4K、30fps。
- 加短句字幕、关键词强调、轻量标题和黑底缩窗。
- 插入图片／视频B-roll，同时保留采访原声。
- 接入使用者自备的封面、片尾及获准音乐。
- 导出H.264/AAC MP4、JSON时间轴、ASS字幕、来源映射与技术记录。

脚本负责可靠执行；理解素材、选择剪点、核准业务事实和完整看听仍需助手及使用者完成。不是一键复原剪映工程，也不提供人物换脸、声音克隆或虚构采访。

## 安装与使用

将本仓库完整目录放到助手的技能目录，并保持目录名为 `zm-brand-talking-video`。本地 Codex 默认技能目录为 `~/.codex/skills/`；已配置 `CODEX_HOME` 时使用其中的 `skills/`。已有同名技能时先备份和核对，不直接覆盖。

```bash
git clone https://github.com/zm0218/zm-brand-talking-video.git
```

然后在新对话中提供源文件，并调用：

```text
$zm-brand-talking-video

请把这几段素材剪成一条视频，给品牌合作伙伴看，
用于内部交流，保留完整信息。画幅和时长请结合素材建议。
```

助手会先利用已有资料，只补问受众、用途、画幅、时长和关键事实中缺失的部分。

## 运行依赖

- Python 3.11+，渲染脚本只用标准库。
- 完整版FFmpeg及ffprobe，包含libx264、AAC、libass（`subtitles`）、`overlay`、`pad`、`loudnorm`。
- 支持中文的本机字体，例如Noto Sans CJK SC；可在JSON中设置 `font_family` 和 `font_file`。
- 本地中文转写可选：支持SpeechTranscriber的macOS、Swift编译器以及**已安装**的简体中文模型。转写脚本不下载模型、不上传音频。其他系统可使用已有逐词字幕或自行获准的ASR。

FFmpeg默认从PATH查找，也可显式设置 `ZM_VIDEO_FFMPEG` 和 `ZM_VIDEO_FFPROBE`。仓库不包含FFmpeg二进制、语音模型和字体，也不会自动安装依赖。

## 命令行入口

以下命令在仓库目录运行。先复制 [配置示例](assets/edit-job.json) 到本次工作目录，替换素材路径、剪点、字幕时码与已确认brief；示例的 `confirmed` 默认为 `false`，不得为了通过检查而擅自设为 `true`。

```bash
python3 scripts/video.py inspect /path/to/source.mp4 --out /path/to/work/inventory.json
python3 scripts/transcribe.py /path/to/source.mp4 --out /path/to/work/transcription
python3 scripts/video.py render /path/to/work/edit-job.json --check
python3 scripts/video.py render /path/to/work/edit-job.json --out /path/to/work/preview-v01 --preview 12
python3 scripts/video.py render /path/to/work/edit-job.json --out /path/to/work/full-v01
```

完整配置见 [时间轴与渲染](references/rendering.md)，不同剪法见 [风格指南](references/style-guide.md)，自备首尾素材见 [首尾说明](references/bookends.md)。

## 素材与隐私

仓库只包含原创工作流文档、脚本和无业务数据的配置示例。**不包含真人采访、参考成片、人物头像、商业封面、品牌Logo、音乐、字体、转写记录或客户资料。** 这些素材需由使用者自行取得对应授权。

运行生成的时间轴、转写和QA可能包含素材路径及内容，应存放在独立工作目录，不能直接当成可公开资料。代码采用MIT许可证，不同时授予任何品牌、肖像、音乐或第三方素材的使用权；详见 [素材边界](ASSETS.md)。

## 验证与限制

可运行以下合成素材自检，不需下载原视频，也不会上传文件：

```bash
python3 scripts/smoke_test.py --out /path/to/new-smoke-output
```

自检覆盖横竖屏导出、字幕、视频B-roll保留原声、首尾拼接、时长与重复字幕／越界拒绝等行为；结果是技术验证，不是实际人物的完整看听验收。macOS转写、Windows／Linux兼容性和长片听感需要在具体环境另行验证。

制作结果应明确区分“生成完成”“技术检查完成”“完整看听通过”和“已发布”。未完成连续看听时，交付名称及记录应写“有声审片版”。
