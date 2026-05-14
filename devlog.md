# LoLM — Development Log

> Nhật ký phát triển dự án Local Language Model  
> Bắt đầu: 2026-05-14  
> Tác giả: K  

---

## Tổng quan dự án

**Mục tiêu:** Xây dựng hệ thống chạy Large Language Model hoàn toàn local, không phụ thuộc cloud.

**Stack chính:**
- Backend: Ollama (AMD ROCm / Vulkan)
- Interface: Python
- GPU: AMD Radeon RX 7900 XTX 24 GB VRAM
- OS: Windows 11

**Kiến trúc dự kiến:**
```
[Model Files (.gguf)] → [Ollama Server] → [Python Client] → [Ứng dụng]
```

---

## Các giai đoạn (Roadmap)

| Giai đoạn | Nội dung | Trạng thái |
|-----------|----------|------------|
| Phase 1 | Cài đặt môi trường (Ollama + Python) | 🔄 Đang làm |
| Phase 2 | Chạy model đầu tiên & benchmark | ⏳ Chờ |
| Phase 3 | Xây Python wrapper / client | ⏳ Chờ |
| Phase 4 | Tính năng nâng cao (streaming, multi-turn) | ⏳ Chờ |
| Phase 5 | Ứng dụng thực tế (RAG / Chatbot) | ⏳ Chờ |

---

## Nhật ký phát triển

### [2026-05-14] Phase 1 — Khởi tạo dự án

**Quyết định kiến trúc:**
- Dùng **Ollama** làm model serving layer vì hỗ trợ Windows + AMD ROCm tốt nhất hiện tại
- AMD 7900XTX 24GB VRAM → có thể chạy được model 70B (Q4_K_M) hoặc 34B (Q8)
- Python là ngôn ngữ chính để tương tác và build application

**Cấu trúc thư mục tạo:**
```
H:\Project\LoLM\
├── src/          # Source code Python
├── docs/         # Tài liệu kỹ thuật
├── scripts/      # Script setup & tiện ích
├── notebooks/    # Jupyter experiments
├── models/       # Model configs & metadata
├── devlog.md     # File này
└── README.md     # Tổng quan dự án
```

**TODO Phase 1:**
- [x] Cài Ollama cho Windows
- [x] Xác nhận AMD GPU được nhận diện — **202 tokens/sec** với llama3.2:3b
- [x] Pull model đầu tiên: `llama3.2:3b` (2.0 GB) tại `D:\Ollamamodel`
- [x] Chạy `scripts/check_gpu.py` thành công — Ollama server OK, GPU OK
- [x] Cài Python dependencies (Python 3.12.10 + venv tại `.venv`)

**Cấu hình đã thiết lập:**
- Models lưu tại `D:\Ollamamodel` (SSD riêng) thay vì mặc định `C:\Users\K\.ollama\models`
- Cách set (thêm vào System Environment Variables):
  ```
  Tên biến : OLLAMA_MODELS
  Giá trị  : D:\Ollamamodel
  ```

---

### [2026-05-14] Q&A — Khái niệm cơ bản Phase 1

**Q: `.venv` là gì, tại sao cần tạo nó?**
A: Môi trường Python riêng cho dự án. Thư viện cài vào `.venv` không ảnh hưởng Python hệ thống và không xung đột với dự án khác. Kích hoạt bằng `.\.venv\Scripts\Activate.ps1`.

**Q: Các thư viện trong `requirements.txt` dùng để làm gì?**
A:
- `ollama` — SDK Python để gọi Ollama server, thay cho gõ lệnh tay
- `httpx` — gửi HTTP request, dùng nội bộ bởi `ollama` SDK
- `rich` — in text màu sắc, bảng đẹp ra terminal
- `typer` — tạo CLI app (giao diện dòng lệnh) cho dự án
- `python-dotenv` — đọc file `.env` chứa cấu hình riêng tư

**Q: Tại sao dùng `pip` trong `.venv` thay vì `pip` hệ thống?**
A: Để cài đúng vào phòng riêng của dự án. Dùng `.\.venv\Scripts\pip` thay vì `pip` toàn cục.

---

### [2026-05-14] Kiểm tra kết nối GitHub

Kiểm tra remote và git identity:
```powershell
cd H:\Project\LoLM
git remote -v
git config --global user.name
git config --global user.email
```

Kiểm tra SSH đến GitHub:
```powershell
ssh -T git@github.com
```

**Kết quả:** Remote chưa được liên kết, `gh` CLI chưa cài. GitHub được kết nối qua Claude Code settings (OAuth) — đây là kết nối riêng, không tự động tạo remote cho repo.

Liên kết local repo với GitHub remote:
```powershell
cd H:\Project\LoLM
git remote add origin https://github.com/SKai1120/LoLM.git
git push -u origin master
```

**Kết quả:** Remote đã kết nối thành công → https://github.com/SKai1120/LoLM

---

<!-- Thêm entries mới vào đây theo format: -->
<!-- ### [YYYY-MM-DD] Tiêu đề -->
