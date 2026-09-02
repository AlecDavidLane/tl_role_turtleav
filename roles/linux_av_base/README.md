# linux_av_base

Shared Ubuntu 24.04 configuration for the Turtle AV presentation and backup
playback computers. The role deliberately contains only the common operating
system baseline; Chromium and VLC behaviour belong in their machine roles.

## What it configures

- Validates Ubuntu 24.04 or later and systemd.
- Installs common deployment and diagnostic packages.
- Enables SSH.
- Creates a locked-password `avoperator` local account.
- Creates Transition Layer application, state, log and media directories.
- Configures GDM automatic login using Xorg.
- Disables screen locking, blanking, notifications and system sleep.
- Prevents unattended package activity during a live show.
- Validates the operator account and SSH service.

## Example

```yaml
- name: Configure presentation and backup computers
  hosts: av_computers
  become: true
  roles:
    - role: linux_av_base
      vars:
        linux_av_base_hostname: "{{ inventory_hostname }}"
        linux_av_base_timezone: Europe/London
```

Set `linux_av_base_enable_autologin: false` when applying the role to an Ubuntu
Server installation without GDM. Set the automatic-update or sleep variables to
`false` only when those functions are managed by another site policy.

