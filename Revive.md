# Revive.md

This file is empty of names on purpose.

Use this in a **new** chat to bring an already-saved agent back. Not a first-save.

Copy this kit, run `Start_config.bat` or `python prepare_agent.py`. The script asks the name, then a password window titled AgentSelfSave (paste works), writes `.secrets/secrets_{Name}.txt`, copies house rules into `.cursor/rules/`, writes `{Name}.mdc` with this revive prompt, and overwrites this file with the revive paste. Port 3306 will not work. Use phpMyAdmin.

Do not paste the on-screen first-save again. He must load what is already there. He must not wipe experience. After later tasks he closes the locker and archives chats without being told save.
