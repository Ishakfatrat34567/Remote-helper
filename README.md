# Consent-Based Remote Assistance (Safe Demo)

This project is a **consent-first remote assistance coordinator** with a local desktop UI.

It does **not** provide hidden access, persistence, or automatic control of another computer.
Instead, it helps two people coordinate a support session where the recipient must explicitly approve each request.

## What it does

- Generates a one-time session code on the recipient side.
- Lets a helper send a request using recipient IP + code.
- Prompts recipient to approve or deny.
- After approval, opens (or instructs to open) a trusted remote-support tool.

## Run

```bash
python3 app.py
```

## Important safety notes

Use this only for legitimate support with explicit consent from the device owner.
