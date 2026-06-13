#!/usr/bin/env bash
set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

echo -e "${BOLD}ppt — 安装${RESET}"
echo ""

INSTALL_DIR="$HOME/.ppt-agent"
VENV_DIR="$INSTALL_DIR/.venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python 检查
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        v=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$v" | cut -d. -f1)
        minor=$(echo "$v" | cut -d. -f2)
        if [[ "$major" -eq 3 && "$minor" -ge 11 ]]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo -e "${YELLOW}未找到 Python 3.11+。请先安装 Python。${RESET}"
    echo "macOS: brew install python@3.14"
    echo "Ubuntu: apt install python3.12 python3.12-venv"
    exit 1
fi

echo -e "Python: ${GREEN}$PYTHON${RESET} ($($PYTHON --version))"
echo -e "安装目录: ${CYAN}$INSTALL_DIR${RESET}"
echo ""

# 创建目录结构
mkdir -p "$INSTALL_DIR"/{sessions,knowledge,styles}

# 创建/重建 venv (已有则跳过)
if [[ ! -d "$VENV_DIR" ]]; then
    echo "创建虚拟环境..."
    $PYTHON -m venv "$VENV_DIR"
fi

# 安装
echo "安装 ppt..."
"$VENV_DIR/bin/pip" install --quiet "$SCRIPT_DIR"

# 配置模板
if [[ ! -f "$INSTALL_DIR/config.yaml" ]]; then
    cp "$SCRIPT_DIR/config.yaml.example" "$INSTALL_DIR/config.yaml"
    echo -e "配置模板: ${GREEN}$INSTALL_DIR/config.yaml${RESET}"
    echo -e "${YELLOW}请编辑此文件，填写 LLM API Key。${RESET}"
fi

# 知识库目录
mkdir -p "$INSTALL_DIR/knowledge"/{web,papers,github,graph,chroma,wiki}

# 软链接到 PATH
BIN_DEST=""
for dest in /usr/local/bin "$HOME/.local/bin" "$HOME/bin"; do
    if [[ -d "$dest" && -w "$dest" ]]; then
        BIN_DEST="$dest/ppt"
        break
    fi
done

if [[ -n "$BIN_DEST" ]]; then
    ln -sf "$VENV_DIR/bin/ppt" "$BIN_DEST"
    echo -e "命令链接: ${GREEN}$BIN_DEST${RESET} → $VENV_DIR/bin/ppt"
else
    echo -e "${YELLOW}未找到可写入的 PATH 目录。请手动添加:${RESET}"
    echo "  echo 'export PATH=\"$VENV_DIR/bin:\$PATH\"' >> ~/.zshrc"
fi

echo ""
echo -e "${GREEN}安装完成！${RESET}"
echo ""
echo "所有文件位于: $INSTALL_DIR/"
echo "  $INSTALL_DIR/config.yaml       配置文件"
echo "  $INSTALL_DIR/.venv/             Python 虚拟环境"
echo "  $INSTALL_DIR/sessions/          会话存档"
echo "  $INSTALL_DIR/knowledge/         知识库"
echo "  $INSTALL_DIR/styles/            风格配置"
echo ""
echo "快速开始:"
echo "  1. vim $INSTALL_DIR/config.yaml   # 填写 API Key"
echo "  2. ppt --help"
echo "  3. ppt new \"你的主题\" --template /path/to/template.pptx"
