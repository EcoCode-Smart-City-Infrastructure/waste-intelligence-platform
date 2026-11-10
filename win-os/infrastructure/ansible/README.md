# WIN OS Ansible provisioning

Roles: `win_validate` (OS/version gate, confirmed-host guard, time sync, base
packages, unattended security upgrades), `win_docker` (Docker Engine +
Compose plugin, log rotation), `win_deploy` (target directory + guided,
credential-free deployment steps).

```bash
ansible-galaxy collection list   # ansible-core >= 2.16 is enough
ansible-playbook -i inventory.ini win-os/infrastructure/ansible/site.yml --check --diff
ansible-playbook -i inventory.ini win-os/infrastructure/ansible/site.yml
```

Safety: the playbook refuses unidentified hosts (`win_target_confirm`),
never changes SSH or firewall by default, and stores no credentials.
Validate syntax with `ansible-playbook --syntax-check`.
