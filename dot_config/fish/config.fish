if status is-interactive
   set -U fish_greeting
   starship init fish | source

   fish_add_path $HOME/.local/bin
   fish_add_path $HOME/.cargo/bin

   zoxide init fish | source
   alias cd="z"
   alias ls="eza --icons"
   alias ll="eza -l --icons"
   alias cat="batcat --paging=never"
end
