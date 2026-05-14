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
- [ ] Cài Ollama cho Windows
- [ ] Xác nhận AMD GPU được nhận diện (ROCm / HIP)
- [ ] Pull model đầu tiên (khuyến nghị: gemma3:12b hoặc llama3.2:3b để test)
- [ ] Chạy `ollama run` lần đầu thành công
- [ ] Cài Python dependencies

---

<!-- Thêm entries mới vào đây theo format: -->
<!-- ### [YYYY-MM-DD] Tiêu đề -->
