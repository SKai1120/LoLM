# Hướng dẫn cài đặt

## Yêu cầu hệ thống

- Windows 10/11 64-bit
- GPU: AMD RX 7900 XTX 24 GB (hoặc NVIDIA/CPU)
- RAM: ≥ 16 GB
- Disk: ≥ 50 GB trống (models thường 4–40 GB mỗi cái)
- Python 3.10+

---

## Bước 1: Cài Ollama

1. Tải Ollama tại: https://ollama.com/download/windows
2. Chạy installer, Ollama sẽ tự động nhận diện GPU AMD (HIP/ROCm)
3. Sau khi cài, mở terminal kiểm tra:

```powershell
ollama --version
```

**Kiểm tra GPU được nhận diện:**
```powershell
ollama run llama3.2:3b
# Nếu GPU hoạt động, tốc độ generate sẽ > 30 tokens/sec
```

---

## Bước 2: Cài Python dependencies

```powershell
cd H:\Project\LoLM
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Bước 3: Pull model đầu tiên

| Model | VRAM cần | Tốc độ (7900XTX) | Ghi chú |
|-------|----------|------------------|---------|
| llama3.2:3b | ~3 GB | ~120 t/s | Test nhanh |
| gemma3:12b | ~8 GB | ~60 t/s | Chất lượng tốt |
| llama3.3:70b-q4 | ~40 GB | ~20 t/s | Cần RAM+VRAM |
| qwen2.5:32b | ~20 GB | ~30 t/s | Khuyến nghị cho 24GB |

```powershell
# Bắt đầu với model nhỏ để test
ollama pull llama3.2:3b

# Sau đó thử model lớn hơn
ollama pull qwen2.5:32b
```

---

## Bước 4: Kiểm tra server API

Ollama tự expose REST API tại `http://localhost:11434`

```powershell
# Kiểm tra server đang chạy
curl http://localhost:11434/api/tags
```

---

## Ghi chú AMD GPU

- Ollama Windows dùng ROCm HIP để hỗ trợ AMD
- Nếu GPU không được nhận: kiểm tra AMD Software Adrenalin phiên bản mới nhất
- Environment variable hữu ích:
  ```powershell
  $env:OLLAMA_GPU_OVERHEAD = "0"  # tận dụng toàn bộ VRAM
  ```
