if status is-interactive
    set -U fish_greeting
    starship init fish | source

    fish_add_path $HOME/.local/bin
    fish_add_path $HOME/.cargo/bin

    zoxide init fish | source
    alias cd="z"
    alias ls="eza --icons"
    alias ll="eza -l --icons"
    alias cat="bat --paging=never"

    # At this point, specify the Zellij config dir, so we can launch it manually if we want to
    export ZELLIJ_CONFIG_DIR=$HOME/.config/zellij

    # Check if our Terminal emulator is Ghostty
    if [ "$TERM" = xterm-ghostty ]
        # Launch zellij
        eval (zellij setup --generate-auto-start fish | string collect)
    end

    if status is-interactive
        mise activate fish | source
    else
        mise activate fish --shims | source
    end
end
