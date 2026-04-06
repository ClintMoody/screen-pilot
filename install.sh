#!/usr/bin/env bash
set -euo pipefail

# screen-pilot installer bootstrap
# Downloads dependencies, then launches the interactive TUI installer.
# Usage: curl -sSL https://raw.githubusercontent.com/clintm/screen-pilot/main/install.sh | bash

VERSION="${SP_VERSION:-latest}"
REPO="https://github.com/clintm/screen-pilot.git"
INSTALL_DIR="${HOME}/.local/share/screen-pilot"
NO_OMNIPARSER=0
NO_TUI=0
UNINSTALL=0

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# --- Parse args ---
for arg in "$@"; do
    case "$arg" in
        --no-omniparser) NO_OMNIPARSER=1 ;;
        --yes|--no-tui)  NO_TUI=1 ;;
        --uninstall)     UNINSTALL=1 ;;
        --version=*)     VERSION="${arg#*=}" ;;
        --help|-h)
            echo "screen-pilot installer"
            echo ""
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-omniparser  Skip OmniParser (no GPU deps, ~4GB smaller)"
            echo "  --yes, --no-tui  Non-interactive install with defaults"
            echo "  --uninstall      Remove screen-pilot"
            echo "  --version=TAG    Install specific version (default: latest)"
            echo "  --help           Show this help"
            exit 0
            ;;
    esac
done

# --- Detect system ---
detect_distro() {
    if command -v pacman &>/dev/null; then
        echo "arch"
    elif command -v apt &>/dev/null; then
        echo "debian"
    else
        echo "unknown"
    fi
}

detect_session() {
    echo "${XDG_SESSION_TYPE:-unknown}"
}

detect_gpu() {
    if command -v nvidia-smi &>/dev/null; then
        echo "nvidia"
    elif [ -d /sys/class/drm/card0/device ] && grep -qi amd /sys/class/drm/card0/device/uevent 2>/dev/null; then
        echo "amd"
    else
        echo "cpu"
    fi
}

DISTRO=$(detect_distro)
SESSION=$(detect_session)
GPU=$(detect_gpu)

echo ""
echo -e "${BOLD}screen-pilot installer${NC}"
echo "========================"
echo -e "  OS:      ${GREEN}${DISTRO}${NC}"
echo -e "  Session: ${GREEN}${SESSION}${NC}"
echo -e "  GPU:     ${GREEN}${GPU}${NC}"
echo -e "  Shell:   ${GREEN}${SHELL##*/}${NC}"
echo ""

if [ "$DISTRO" = "unknown" ]; then
    err "Unsupported distro. screen-pilot requires Arch/CachyOS or Debian/Ubuntu."
    exit 1
fi

# --- Uninstall ---
if [ "$UNINSTALL" = "1" ]; then
    warn "Uninstalling screen-pilot..."
    systemctl --user stop screen-pilot 2>/dev/null || true
    systemctl --user disable screen-pilot 2>/dev/null || true
    rm -f "${HOME}/.config/systemd/user/screen-pilot.service"
    systemctl --user daemon-reload 2>/dev/null || true

    if command -v conda &>/dev/null; then
        conda env remove -n screen-pilot -y 2>/dev/null || true
    fi

    rm -rf "${HOME}/.config/screen-pilot"
    rm -rf "${INSTALL_DIR}"
    ok "screen-pilot removed. OmniParser weights and system packages were left in place."
    exit 0
fi

# --- Confirm ---
if [ "$NO_TUI" = "0" ]; then
    echo -e "${YELLOW}This will install system packages and configure services.${NC}"
    read -rp "Continue? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# --- System packages ---
info "Installing system packages..."
if [ "$DISTRO" = "arch" ]; then
    sudo pacman -Syu --noconfirm --needed \
        ydotool python-evdev grim python-pip git wget base-devel
elif [ "$DISTRO" = "debian" ]; then
    sudo apt update
    sudo apt install -y \
        ydotool python3-evdev grim python3-pip python3-venv git wget
fi
ok "System packages installed"

# --- uinput ---
if ! groups | grep -q input; then
    info "Adding $USER to input group..."
    sudo usermod -aG input "$USER"
    warn "You'll need to log out and back in for input group to take effect"
fi

if [ ! -f /etc/udev/rules.d/99-uinput.rules ]; then
    info "Creating uinput udev rule..."
    echo 'KERNEL=="uinput", MODE="0660", GROUP="input"' | sudo tee /etc/udev/rules.d/99-uinput.rules
    sudo modprobe uinput
    echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
    sudo udevadm control --reload-rules
    sudo udevadm trigger --name-match=uinput
fi
ok "uinput configured"

# --- ydotoold ---
if ! systemctl --user is-active ydotool &>/dev/null; then
    info "Enabling ydotool service..."
    systemctl --user enable --now ydotool 2>/dev/null || {
        warn "systemd ydotool service not available, starting manually"
        ydotoold --socket-path /run/user/$(id -u)/.ydotool_socket &
    }
fi
ok "ydotoold running"

# --- Miniconda ---
if ! command -v conda &>/dev/null; then
    info "Installing Miniconda..."
    wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    EXPECTED_HASH=$(curl -sL https://repo.anaconda.com/miniconda/ | grep -oP "(?<=Miniconda3-latest-Linux-x86_64.sh</a></td><td>[^<]*</td><td>)[a-f0-9]{64}" | head -1)
    ACTUAL_HASH=$(sha256sum /tmp/miniconda.sh | cut -d' ' -f1)
    if [ -n "$EXPECTED_HASH" ] && [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
        err "Miniconda SHA256 mismatch! Aborting."
        exit 1
    fi
    bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
    export PATH="$HOME/miniconda3/bin:$PATH"
    conda init "$(basename "$SHELL")" 2>/dev/null || true
    ok "Miniconda installed"
else
    ok "Conda already available"
fi

export PATH="$HOME/miniconda3/bin:$PATH"

# --- Conda env ---
if ! conda env list | grep -q screen-pilot; then
    info "Creating screen-pilot conda environment..."
    conda create -n screen-pilot python=3.12 -y
fi
ok "Conda environment ready"

# --- Clone/update repo ---
if [ -d "$INSTALL_DIR" ]; then
    info "Updating screen-pilot..."
    cd "$INSTALL_DIR" && git pull
else
    info "Cloning screen-pilot..."
    git clone "$REPO" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

if [ "$VERSION" != "latest" ]; then
    git checkout "$VERSION"
fi

# --- Install Python package ---
info "Installing screen-pilot..."
conda run -n screen-pilot pip install -e ".[dev]"

if [ "$NO_OMNIPARSER" = "0" ]; then
    info "Installing vision dependencies (OmniParser + torch)..."
    if [ "$GPU" = "nvidia" ]; then
        CUDA_VER=$(nvidia-smi | grep -oP "CUDA Version: \K[0-9.]+" | cut -d. -f1-2)
        # Map CUDA version to closest available torch wheel
        case "$CUDA_VER" in
            13.*|12.8|12.9) CUDA_WHEEL="cu128" ;;
            12.4|12.5|12.6|12.7) CUDA_WHEEL="cu124" ;;
            *) CUDA_WHEEL="cu121" ;;
        esac
        conda run -n screen-pilot pip install torch torchvision --index-url "https://download.pytorch.org/whl/${CUDA_WHEEL}"
    else
        conda run -n screen-pilot pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    fi
    conda run -n screen-pilot pip install "ultralytics>=8.4.0"

    # Download OmniParser weights
    WEIGHTS_DIR="${HOME}/.local/share/screen-pilot/weights"
    if [ ! -d "$WEIGHTS_DIR/icon_detect" ]; then
        info "Downloading OmniParser weights (~2GB)..."
        conda run -n screen-pilot python -c "
from huggingface_hub import snapshot_download
snapshot_download('microsoft/OmniParser-v2.0', local_dir='${WEIGHTS_DIR}')
"
        if [ -d "$WEIGHTS_DIR/icon_caption" ] && [ ! -d "$WEIGHTS_DIR/icon_caption_florence" ]; then
            mv "$WEIGHTS_DIR/icon_caption" "$WEIGHTS_DIR/icon_caption_florence"
        fi
        ok "OmniParser weights downloaded"
    else
        ok "OmniParser weights already present"
    fi
fi

ok "Python packages installed"

# --- Systemd service ---
info "Installing systemd service..."
mkdir -p "${HOME}/.config/systemd/user"
cp "$INSTALL_DIR/screen-pilot.service" "${HOME}/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable screen-pilot
ok "Service installed (run 'screen-pilot up' to start)"

# --- Default config ---
CONFIG_DIR="${HOME}/.config/screen-pilot"
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
    mkdir -p "$CONFIG_DIR"
    cp "$INSTALL_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
    ok "Default config created at $CONFIG_DIR/config.toml"
fi

# --- Summary ---
echo ""
echo -e "${GREEN}${BOLD}Installation complete!${NC}"
echo ""
echo "  Start:    screen-pilot up"
echo "  Status:   screen-pilot status"
echo "  Config:   screen-pilot config"
echo ""
echo "  Claude Code:  claude mcp add screen-pilot --transport sse http://localhost:7222/mcp"
echo "  Codex:        codex mcp add screen-pilot --transport sse http://localhost:7222/mcp"
echo ""

if ! groups | grep -q input; then
    echo -e "${YELLOW}NOTE: Log out and back in for input group to take effect.${NC}"
fi
