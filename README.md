# Transition Layer - Turtle AV CHAZY role

An idempotent Ansible proof-of-concept for configuring a Turtle AV CHAZY Control Pro through its restricted SSH command interface.

The first implementation manages one safe, visible controller setting: the RS-232 baud rate. It queries the controller before making a change, changes only a non-compliant value, queries it again, and fails unless the requested value is verified.

## Requirements

- macOS with Ansible installed
- Python 3
- Network access to the CHAZY Control Pro
- CHAZY SSH enabled

Create a project virtual environment and install the dependencies. This avoids
the `externally-managed-environment` restriction used by current Homebrew Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m pip install ansible
```

Keep the virtual environment active while running the playbook.

## Run

The supplied defaults target `192.168.6.160` and set the RS-232 baud rate to `38400`:

```bash
ansible-playbook -i inventory.yml site.yml
```

Ansible prompts for the CHAZY admin password without displaying or storing it.

Override the controller address or desired baud rate when required:

```bash
ansible-playbook -i inventory.yml site.yml \
  -e chazy_host=192.168.6.160 \
  -e chazy_rs232_baud=38400
```

Supported baud rates are `115200`, `57600`, `38400`, `19200`, and `9600`.

## Expected first run

```text
before_baud: 57600
after_baud: 38400
changed: true
verified: true
```

Running the same playbook again should return:

```text
before_baud: 38400
after_baud: 38400
changed: false
verified: true
```

## Restore the original value

```bash
ansible-playbook -i inventory.yml site.yml -e chazy_rs232_baud=57600
```

## Security

- No passwords are committed to this repository.
- `vault.yml` is ignored if Ansible Vault variables are added later.
- Host-key verification is handled by Paramiko for this initial local proof-of-concept. Production deployments should pin and verify the controller host key.
