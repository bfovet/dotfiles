#!/bin/bash

install_on_arch() {
  sudo pacman -Syu --noconfirm ansible
  sudo mkdir /etc/ansible/
  sudo touch /etc/ansible/hosts
  sudo chmod 777 /etc/ansible/hosts
  sudo echo "localhost ansible_connection=local" >>/etc/ansible/hosts
}

OS="$(uname -s)"
case "${OS}" in
Linux*)
  if [ -f /etc/arch-release ]; then
    install_on_arch
  fi
  ;;
*)
  echo "Unsupported operating system: ${OS}"
  exit 1
  ;;
esac

ansible-playbook ~/.bootstrap/setup.yml --ask-become-pass

echo "Ansible installation complete"
