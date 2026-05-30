# Remote Access — Tailscale Setup

Hướng dẫn truy cập LoLM từ xa (điện thoại, laptop khác) qua Tailscale VPN mesh.

## Tailscale là gì?

Tailscale tạo một mạng VPN riêng tư giữa tất cả thiết bị của bạn. Không cần mở port,
không cần IP tĩnh, không expose IP thật ra internet. Miễn phí cho cá nhân (tối đa 3 thiết bị).

## Setup (5 phút)

### 1. Cài Tailscale

| Thiết bị | Link |
|----------|------|
| Windows 11 (máy chạy LoLM) | https://tailscale.com/download/windows |
| Android / iOS | Tìm "Tailscale" trên Play Store / App Store |

### 2. Đăng nhập cùng account

Đăng nhập bằng cùng một Google / GitHub / Microsoft account trên tất cả thiết bị.
Hai thiết bị sẽ tự nhận nhau trong vòng 30 giây.

### 3. Lấy Tailscale IP của máy Windows

```powershell
# Trong PowerShell hoặc Command Prompt
tailscale ip -4
# Ví dụ kết quả: 100.64.x.x
```

## Cách dùng

### Truy cập TUI từ điện thoại (qua SSH)

**Yêu cầu:** Bật OpenSSH Server trên Windows 11

```
Settings → System → Optional Features → Add a feature → OpenSSH Server
```

Sau đó SSH từ app Termius / JuiceSSH / ConnectBot trên điện thoại:
```bash
ssh username@100.64.x.x
cd C:\path\to\LoLM
.venv\Scripts\python -m src.tui
```

### Telegram Bot (không cần Tailscale)

Telegram Bot dùng **long polling** — máy local tự kết nối ra Telegram, không cần inbound connection.
Chỉ cần chạy:
```bash
python scripts/start_bot.py
```
Rồi nhắn lệnh `/ask`, `/status`, v.v. từ Telegram trên điện thoại bất kỳ đâu.

## Security Notes

- Tailscale traffic được mã hóa end-to-end (WireGuard)
- Chỉ thiết bị trong cùng Tailscale account mới kết nối được
- Không cần mở port trên router/firewall
- Máy local KHÔNG expose ra internet — chỉ accessible trong Tailscale network
