#!/usr/bin/env bash
set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

echo -e "${BOLD}PPT Agent — 安装${RESET}"
echo ""

# Python 检查
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        v=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$v" | cut -d. -f1)
        if [[ "$major" -ge 3 && "$v" != "3.0" && "$v" != "3.1" && "$v" != "3.10" ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

# 特殊处理 macOS Homebrew python3.11 (命名可能为 python3.11)
if [[ -z "$PYTHON" ]]; then
    for major in 11 12 13 14; do
        if command -v "python3.${major}" &>/dev/null; then
            PYTHON="python3.${major}"
            break
        fi
    done
fi

if [[ -z "$PYTHON" ]]; then
    echo -e "${YELLOW}未找到 Python 3.11+。请先安装 Python。${RESET}"
    echo "macOS: brew install python@3.14"
    echo "Ubuntu: apt install python3.12 python3.12-venv"
    exit 1
fi

echo -e "使用 Python: ${GREEN}$PYTHON${RESET} ($($PYTHON --version))"

# 项目目录 (脚本所在目录)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# 创建 venv
if [[ ! -d "$VENV_DIR" ]]; then
    echo "创建虚拟环境..."
    $PYTHON -m venv "$VENV_DIR"
fi

# 安装
echo "安装 ppt..."
"$VENV_DIR/bin/pip" install --quiet -e "$SCRIPT_DIR"

# 创建配置目录
CONFIG_DIR="$HOME/.ppt-agent"
if [[ ! -d "$CONFIG_DIR" ]]; then
    mkdir -p "$CONFIG_DIR"
fi

# 如果不存在配置文件，从示例复制
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
    cp "$SCRIPT_DIR/config.yaml.example" "$CONFIG_DIR/config.yaml"
    echo -e "已创建配置: ${GREEN}$CONFIG_DIR/config.yaml${RESET}"
    echo -e "${YELLOW}请编辑此文件，填写你的 LLM API Key。${RESET}"
fi

# 建立软链接到 PATH
BIN_DEST=""
for dest in /usr/local/bin "$HOME/.local/bin" "$HOME/bin"; do
    if [[ -d "$dest" && -w "$dest" ]]; then
        BIN_DEST="$dest/ppt"
        break
    fi
done

if [[ -n "$BIN_DEST" ]]; then
    ln -sf "$VENV_DIR/bin/ppt" "$BIN_DEST"
    echo -e "命令已链接: ${GREEN}$BIN_DEST${RESET}"
else
    VENV_BIN="$VENV_DIR/bin/ppt"
    echo -e "请将以下路径加入 PATH，或手动创建软链接:"
    echo -e "  ${BOLD}$VENV_BIN${RESET}"
    echo ""
    # 尝试通过 PATH 检查
    if [[ ":$PATH:" == *":$VENV_DIR/bin:"* ]]; then
        echo -e "${GREEN}ppt 已在 PATH 中。${RESET}"
    fi
fi

echo ""
echo -e "${GREEN}安装完成！${RESET}"
echo "运行: ppt --help"
echo "生成: ppt new \"你的主题\" --template /path/to/template.pptx"
