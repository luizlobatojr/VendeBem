#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
launcher="$project_dir/executar_ubuntu.sh"
icon="$project_dir/assets/vendebem.svg"

if [ ! -x "$launcher" ]; then
    printf '%s\n' "Erro: não foi encontrado o iniciador executável: $launcher" >&2
    exit 1
fi

if [ ! -f "$icon" ]; then
    printf '%s\n' "Erro: não foi encontrado o ícone: $icon" >&2
    exit 1
fi

if command -v xdg-user-dir >/dev/null 2>&1; then
    desktop_dir=$(xdg-user-dir DESKTOP 2>/dev/null || true)
else
    desktop_dir=""
fi
if [ -z "$desktop_dir" ]; then
    desktop_dir="$HOME/Desktop"
fi

mkdir -p "$desktop_dir"
shortcut="$desktop_dir/VendeBem.desktop"

escape_desktop_arg() {
    printf '"'
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/`/\\`/g; s/\$/\\$/g'
    printf '"'
}

{
    printf '%s\n' '[Desktop Entry]'
    printf '%s\n' 'Version=1.0' 'Type=Application' 'Name=VendeBem'
    printf 'Comment=%s\n' 'Gerenciador de vendas e stock'
    printf 'Exec=%s\n' "$(escape_desktop_arg "$launcher")"
    printf 'Icon=%s\n' "$icon"
    printf '%s\n' 'Terminal=false' 'Categories=Office;Finance;'
} > "$shortcut"

chmod +x "$shortcut"
printf 'Atalho criado em: %s\n' "$shortcut"
