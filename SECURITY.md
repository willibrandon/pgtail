# Security

Report a vulnerability privately through GitHub Security Advisories for the `willibrandon/pgtail` repository: open the
Security tab and choose "Report a vulnerability". Please do not open a public issue for one. Fixes go into the latest
release.

pgtail reads PostgreSQL log files and configuration with your permissions, and runs what you ask it to: a `!` command,
a `pipe` command, or a notification. Those doing what you typed is working as intended. A report is welcome when pgtail
does something you did not ask for, such as running part of a log line as a command, writing outside its own
configuration and the files you name, or letting log content change what the terminal does.

pgtail does not collect telemetry. It uses the network for one thing: once a day it asks GitHub for the latest release
to tell you about an update. `set updates.check false` turns that off.
