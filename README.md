# Ứng dụng luyện dịch TOPIK II – bản miễn phí

## Điểm quan trọng
- Không tích hợp OpenAI API, không cần API Key và không gọi dịch vụ AI trả phí.
- Giữ ngân hàng 20 câu Hàn → Việt, 20 câu Việt → Hàn, từ vựng và ngữ pháp trong mã nguồn ban đầu.
- Có nút đọc câu/từ tiếng Hàn bằng Web Speech API của trình duyệt/thiết bị. Chọn giọng `ko-KR` nếu thiết bị có giọng này.
- Có chế độ chấm câu tự nhập.
- Tách bộ đếm tiến độ của hai chiều dịch.

## Giới hạn chấm điểm
Bản miễn phí dùng so khớp từ ngữ, tỷ lệ từ chung và một từ điển nhỏ các cách diễn đạt tương đương. Điểm và phần trăm chỉ là **chỉ số tham khảo theo từ ngữ**, không phải đánh giá ngữ nghĩa thật, không thể thay thế giảng viên hoặc AI hiểu ngữ cảnh. Từ đồng nghĩa ngoài từ điển có thể chưa được nhận diện.

## Cài đặt trên máy tính
1. Cài Python 3.10 trở lên.
2. Giải nén thư mục.
3. Mở Terminal/CMD tại thư mục chứa `app.py`.
4. Chạy: `pip install -r requirements.txt`
5. Chạy: `streamlit run app.py`

## Phát âm
Nút 🔊 sử dụng giọng đọc có sẵn trong trình duyệt, không cần API Key. Nên mở bằng Chrome/Edge và kiểm tra thiết bị đã cài giọng tiếng Hàn (Korean/ko-KR). Chất lượng và khả năng phát âm phụ thuộc thiết bị/trình duyệt; đây không phải tệp âm thanh tải sẵn.

## Chi phí
Ứng dụng không sử dụng OpenAI API và không yêu cầu thanh toán API. Nếu triển khai trên nền tảng hosting bên ngoài, nền tảng đó có thể có chính sách/giới hạn riêng.
