#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}======================================"
echo "   P2P Messenger VPN - Установщик"
echo -e "======================================${NC}"

detect_shell() {
    CURRENT_SHELL=$(basename "$SHELL")
    case "$CURRENT_SHELL" in
        bash|zsh|fish) echo "$CURRENT_SHELL" ;;
        *) echo "" ;;
    esac
}

SHELL_NAME=$(detect_shell)
if [ -z "$SHELL_NAME" ]; then
    echo "Не удалось определить оболочку. Выберите из списка:"
    echo "1) bash"
    echo "2) zsh"
    echo "3) fish"
    read -p "Номер (1-3): " shell_choice
    case $shell_choice in
        1) SHELL_NAME="bash" ;;
        2) SHELL_NAME="zsh" ;;
        3) SHELL_NAME="fish" ;;
        *) echo -e "${RED}Неверный выбор, выходим.${NC}"; exit 1 ;;
    esac
fi
echo -e "Оболочка: ${GREEN}$SHELL_NAME${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python3 не найден.${NC}"
    read -p "Установить python3 и pip? (y/n): " install_py
    if [ "$install_py" = "y" ]; then
        if command -v apt-get &>/dev/null; then
            apt-get update && apt-get install -y python3 python3-venv python3-pip
        elif command -v yum &>/dev/null; then
            yum install -y python3 python3-pip
        elif command -v pacman &>/dev/null; then
            pacman -Sy --noconfirm python python-pip
        else
            echo "Неизвестный пакетный менеджер. Установите python3 вручную."; exit 1
        fi
    else
        echo "Без python3 программа не заработает. Выход."; exit 1
    fi
fi

INSTALL_DIR="/opt/p2p_messenger_vpn"
VENV_DIR="/opt/p2pvpn_env"
echo "Создаю виртуальное окружение..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install pycryptodome
deactivate

echo "Копирую файлы проекта..."
mkdir -p "$INSTALL_DIR"
cp -r "$(dirname "$0")"/* "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/run.sh"

echo "Настраиваю алиас p2pmsngr..."
ALIAS_CMD="alias p2pmsngr='sudo $INSTALL_DIR/run.sh'"
case "$SHELL_NAME" in
    bash)
        if ! grep -q "alias p2pmsngr=" "$HOME/.bashrc" 2>/dev/null; then
            echo "$ALIAS_CMD" >> "$HOME/.bashrc"
        fi
        ;;
    zsh)
        if ! grep -q "alias p2pmsngr=" "$HOME/.zshrc" 2>/dev/null; then
            echo "$ALIAS_CMD" >> "$HOME/.zshrc"
        fi
        ;;
    fish)
        mkdir -p "$HOME/.config/fish"
        if ! grep -q "alias p2pmsngr=" "$HOME/.config/fish/config.fish" 2>/dev/null; then
            echo "alias p2pmsngr='sudo $INSTALL_DIR/run.sh'" >> "$HOME/.config/fish/config.fish"
        fi
        ;;
esac

ln -sf "$INSTALL_DIR/run.sh" /usr/local/bin/p2pmsngr 2>/dev/null || echo "Симлинк в /usr/local/bin не создан (возможно, нет прав)"

echo -e "${GREEN}Установка завершена!${NC}"
echo "Теперь можно запустить: sudo p2pmsngr"
echo "Или после перезапуска оболочки: p2pmsngr"
