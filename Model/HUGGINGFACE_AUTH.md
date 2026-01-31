# Hugging Face auth – if login fails

If `login()` or the Read token doesn’t work, try these in order.

---

## 1. Use the token explicitly (avoids paste issues)

Pasting in the terminal can add spaces/newlines and break the token. Use Python with the token in quotes:

```bash
cd Model
python3.11 -c "from huggingface_hub import login; login(token='PASTE_YOUR_TOKEN_HERE')"
```

Replace `PASTE_YOUR_TOKEN_HERE` with your actual token (starts with `hf_`). No spaces before or after the token inside the quotes.

---

## 2. Use the environment variable

Set the token in your shell so every command uses it:

```bash
export HF_TOKEN="hf_your_full_token_here"
```

Then run your script in the **same terminal**:

```bash
python3.11 test_sam3.py
```

To make it permanent (optional), add the `export` line to `~/.zshrc` and run `source ~/.zshrc`.

---

## 3. Check the token

- **Copy again** from https://huggingface.co/settings/tokens (Create new token if needed).
- **Type:** Read.
- **No extra characters:** after pasting, ensure there’s no space or newline at the start or end.

---

## 4. Confirm model access

Auth can succeed but the **model** can still return 401/403 if:

- You’re not approved for the gated model yet.
- You’re using a different Hugging Face account than the one that requested access.

Check:

1. Open https://huggingface.co/facebook/sam3 while **logged in**.
2. You should see the model page (no “Request access” or “Access denied”).
3. Use the **same account** when running `login()` or `HF_TOKEN`.

---

## 5. Verify auth from Python

Run:

```bash
cd Model
python3.11 -c "
from huggingface_hub import login, whoami
login(token='YOUR_TOKEN_HERE')  # or skip if you set HF_TOKEN
print(whoami())
"
```

If you see your username, auth is working. If you get 401, the token is wrong or revoked.

---

## Quick checklist

| Step | Action |
|------|--------|
| 1 | Token from https://huggingface.co/settings/tokens, type **Read** |
| 2 | `export HF_TOKEN="hf_..."` in the same terminal you use for Kavi |
| 3 | Same HF account as the one with access to `facebook/sam3` |
| 4 | Run `python3.11 test_sam3.py` |
