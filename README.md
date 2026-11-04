# Ứng dụng luyện dịch TOPIK II – Câu 54

## Chức năng
- Luyện dịch Hàn → Việt và Việt → Hàn.
- AI đánh giá ngữ nghĩa, ngữ cảnh, từng cụm từ và tiêu chí riêng cho từng chiều dịch.
- Chấp nhận cách dịch đồng nghĩa hợp lý, không chỉ so sánh với đáp án mẫu.
- Nghe phát âm câu tiếng Hàn, câu trả lời tiếng Hàn và từ vựng bằng OpenAI Text-to-Speech.
- Giữ ngân hàng 20 câu mỗi chiều, từ vựng và ngữ pháp trong mã gốc.
- Có chế độ tự nhập câu để luyện thêm.

## Cài đặt
Yêu cầu Python 3.10 trở lên.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Cấu hình API Key

Cách 1: Nhập OpenAI API Key ở thanh bên trong ứng dụng. Key chỉ tồn tại trong phiên chạy hiện tại.

Cách 2: Đặt biến môi trường `OPENAI_API_KEY`.

Cách 3: Tạo `.streamlit/secrets.toml`:
```toml
OPENAI_API_KEY = "sk-..."
```

Không chia sẻ API Key hoặc đưa file secrets lên GitHub.

Tuỳ chọn:
- `OPENAI_TEXT_MODEL`: mặc định `gpt-4o-mini`
- `OPENAI_TTS_MODEL`: mặc định `tts-1`
- `OPENAI_TTS_VOICE`: mặc định `alloy`
- `APP_PASSWORD`: đặt mật khẩu ứng dụng. Nếu không đặt, ứng dụng không bật màn hình đăng nhập.

## Chạy ứng dụng
```bash
streamlit run app.py
```

## Chi phí và giới hạn
Chấm dịch và tạo âm thanh đều gọi OpenAI API, có thể phát sinh phí theo mức giá và hạn mức tài khoản hiện hành. Âm thanh được cache trong phiên/cache Streamlit để tránh tạo lại không cần thiết. Mô hình AI có thể đánh giá chưa hoàn hảo; phần trăm là ước lượng học tập, không phải xác suất hay điểm TOPIK chính thức.
