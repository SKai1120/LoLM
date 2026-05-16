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
| Phase 1 | Cài đặt môi trường (Ollama + Python) | ✅ Xong |
| Phase 2 | Chạy model đầu tiên & benchmark | ✅ Xong |
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

Commit và push devlog + .gitignore:
```powershell
cd H:\Project\LoLM
git add devlog.md .gitignore
git commit -m "Update devlog: GitHub setup + add .gitignore"
git push
```

---

### [2026-05-14] Q&A — Tái tạo môi trường trên máy khác

**Q: Làm sao tạo lại `.venv` trên máy khác?**
A: Clone repo về rồi chạy 3 lệnh:
```powershell
git clone https://github.com/SKai1120/LoLM.git
cd LoLM
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```
`.venv` không lên git (có trong `.gitignore`). `requirements.txt` chứa danh sách thư viện — máy mới tự cài lại từ đó.

---

### [2026-05-15] Phase 2 — Benchmark kết quả

Chạy benchmark so sánh 2 model:
```powershell
cd H:\Project\LoLM
.\.venv\Scripts\python scripts\benchmark.py
```

**Kết quả:**
| Model | Tốc độ tb | Ghi chú |
|-------|-----------|---------|
| qwen2.5:14b | **65.6 t/s** | Ổn định, tiếng Việt khá |
| deepseek-r1:32b | 6.5 t/s | Chậm do kiến trúc reasoning (sinh thinking tokens), test 1 timeout 120s |

**Phân tích:**
- `deepseek-r1` chậm vì là reasoning model — tự "nháp" trước khi trả lời, sinh nhiều tokens hơn
- Cả 2 model bị lỗi trộn tiếng Trung khi không có system prompt → sẽ fix ở Phase 3
- 19GB deepseek có thể bị tràn một phần sang RAM (VRAM overhead)

**Quyết định:**
- Model chính: `qwen2.5:14b` — nhanh gấp 10x, đủ chất lượng
- `deepseek-r1:32b` — giữ lại cho bài toán cần suy luận sâu

---

### [2026-05-15] Phase 3 — Tóm tắt cuối ngày

**Đã hoàn thành:**
- Smart router `src/router.py` — tự chọn qwen/deepseek theo loại câu hỏi
- `num_ctx` tối ưu per model — tránh context overflow, không lãng phí VRAM
- `ChatSession` — multi-turn chat với 3 lớp bảo vệ:
  - num_ctx đúng theo model
  - Sliding window (max 20 turns)
  - Summary memory (tóm tắt phần cũ trước khi bỏ)
- Session persistent: `save()` / `load()` JSON — nhớ qua nhiều ngày
- `src/chat.py` — interactive CLI với lệnh `/help /model /history /save /reset /exit`

**Bỏ ngỏ — tiếp tục lần sau:**
- [ ] Test `src/chat.py` interactive CLI
- [ ] Phase 4: Spinner khi chờ token đầu tiên
- [ ] Phase 4: Live panel — text render trong khung cố định
- [ ] Phase 4: Strip `<think>` tag của deepseek-r1
- [ ] Phase 5: RAG / Chatbot

---

<!-- Thêm entries mới vào đây theo format: -->
<!-- ### [YYYY-MM-DD] Tiêu đề -->
