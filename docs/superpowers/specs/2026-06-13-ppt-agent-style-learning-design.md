# PPT Agent — Style Learning 设计

## 概述

子项目 5：从示例 .pptx 文件中提取排版风格（配色、字体、布局模式、间距比例），持久化为 StyleProfile，在生成新 PPT 时应用该风格。

## 范围

### 包含
- StyleExtractor：从 .pptx 提取风格特征
- StyleProfile：结构化的风格描述（pydantic model）
- 风格持久化：存储到 `~/.ppt-agent/styles/` 目录
- 集成到 generator：Shape Renderer 根据风格配色/字体/间距渲染
- CLI：`ppt-agent style extract 