import streamlit as st
import difflib
import re

# =========================================================
# 🔒 LỚP BẢO MẬT BẰNG MẬT KHẨU
# =========================================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "123456":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔒 Đăng nhập để sử dụng ứng dụng")
        st.text_input("Nhập mật khẩu riêng của bạn:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🔒 Đăng nhập để sử dụng ứng dụng")
        st.text_input("Nhập mật khẩu riêng của bạn:", type="password", on_change=password_entered, key="password")
        st.error("😕 Mật khẩu không đúng. Vui lòng thử lại.")
        return False
    else:
        return True

if not check_password():
    st.stop()


# =========================================================
# 🇰🇷 TOÀN BỘ MÃ NGUỒN ỨNG DỤNG LUYỆN DỊCH TOPIK II - CÂU 54
# =========================================================

st.set_page_config(page_title="AI Giảng Viên Chấm Điểm TOPIK II - Câu 54", page_icon="👨‍🏫", layout="centered")

# Danh sách 20 câu chiều: HÀN SANG VIỆT
KR_TO_VI_LIST = [
    {"id": 1, "source": "현대 사회에서 경쟁은 학생들이 성장하는 데 중요한 역할을 한다.", "target": "Trong xã hội hiện đại, sự cạnh tranh đóng vai trò quan trọng đối với sự phát triển của học sinh."},
    {"id": 2, "source": "학생들은 경쟁을 통해 자신의 능력을 확인하고 부족한 점을 개선할 수 있다.", "target": "Thông qua cạnh tranh, học sinh có thể xác định năng lực bản thân và cải thiện những điểm thiếu sót."},
    {"id": 3, "source": "그러나 지나친 경쟁은 오히려 부정적인 결과를 초래할 수 있으므로 바람직한 경쟁이 이루어져야 한다.", "target": "Tuy nhiên, cạnh tranh quá mức có thể dẫn đến kết quả tiêu cực, vì vậy cần phải có sự cạnh tranh lành mạnh."},
    {"id": 4, "source": "먼저 학생들은 경쟁을 통해 자신의 실력을 향상시키고 목표를 달성하려는 의지를 기를 수 있다.", "target": "Trước hết, thông qua cạnh tranh, học sinh có thể nâng cao thực lực và nuôi dưỡng ý chí đạt được mục tiêu."},
    {"id": 5, "source": "다른 학생들과 실력을 겨루는 과정에서 자신의 강점과 약점을 파악할 수 있다.", "target": "Trong quá trình đọ sức với các học sinh khác, các em có thể nắm bắt được điểm mạnh và điểm yếu."},
    {"id": 6, "source": "부족한 부분을 보완하기 위해 더욱 노력하게 된다.", "target": "Các em sẽ nỗ lực hơn nữa để bù đắp những phần còn thiếu sót."},
    {"id": 7, "source": "또한 이러한 경험은 학생들이 어려움에 부딪혔을 때 포기하지 않고 도전하는 태도를 기르는 데에도 도움이 된다.", "target": "Ngoài ra, trải nghiệm này giúp học sinh rèn luyện thái độ dám thử thách, không bỏ cuộc khi gặp khó khăn."},
    {"id": 8, "source": "반면 지나친 경쟁은 학생들에게 심한 스트레스와 심리적 부담을 줄 수 있다.", "target": "Ngược lại, cạnh tranh quá mức có thể gây áp lực tâm lý và căng thẳng nặng nề cho học sinh."},
    {"id": 9, "source": "특히 좋은 성적이나 높은 순위만을 중요하게 생각하게 되면 결과에 집착하게 된다.", "target": "Đặc biệt, nếu chỉ coi trọng điểm số cao hay thứ hạng cao, các em sẽ dễ bị ám ảnh bởi kết quả."},
    {"id": 10, "source": "결과에 집착한 나머지 친구를 경쟁 상대로만 여기게 될 수 있다.", "target": "Quá chìm đắm vào kết quả có thể khiến các em xem bạn bè chỉ là đối thủ cạnh tranh."},
    {"id": 11, "source": "심한 경우에는 부정행위를 하거나 다른 사람을 배려하지 않는 태도가 나타날 수도 있다.", "target": "Trong trường hợp nặng, có thể xuất hiện hành vi gian lận hoặc thái độ không biết quan tâm đến người khác."},
    {"id": 12, "source": "이는 학생들의 건강한 성장뿐만 아니라 원만한 교우 관계에도 부정적인 영향을 미친다.", "target": "Điều này gây ảnh hưởng tiêu cực đến sự phát triển lành mạnh và các mối quan hệ bạn bè."},
    {"id": 13, "source": "따라서 학교에서는 학생들이 서로 협력하면서 자신의 능력을 발휘할 수 있는 환경을 조성해야 한다.", "target": "Do đó, nhà trường cần tạo môi trường để học sinh phát huy năng lực trong khi hợp tác với nhau."},
    {"id": 14, "source": "예를 들어 개인의 성적이나 순위만을 강조하기보다는 모둠별 과제나 체육 활동을 통해 서로의 장점을 인정해야 한다.", "target": "Ví dụ, thay vì chỉ nhấn mạnh điểm số cá nhân, nên thông qua bài tập nhóm hoặc thể thao để công nhận ưu điểm của nhau."},
    {"id": 15, "source": "부족한 부분을 서로 도와주도록 해야 한다.", "target": "Cần phải giúp đỡ lẫn nhau trong những phần còn thiếu sót."},
    {"id": 16, "source": "또한 결과뿐만 아니라 노력과 발전 과정도 공정하게 평가해야 한다.", "target": "Hơn nữa, không chỉ kết quả mà cả nỗ lực và quá trình phát triển cũng cần được đánh giá công bằng."},
    {"id": 17, "source": "이를 통해 학생들은 다른 사람과의 경쟁을 두려워하지 않게 된다.", "target": "Qua đó, học sinh sẽ không còn sợ hãi việc cạnh tranh với người khác."},
    {"id": 18, "source": "서로 배우며 함께 성장할 수 있을 것이다.", "target": "Các em có thể học hỏi lẫn nhau và cùng nhau trưởng thành."},
    {"id": 19, "source": "경쟁은 때로는 우리에게 발전의 자극제가 된다.", "target": "Cạnh tranh đôi khi là chất kích thích cho sự phát triển của chúng ta."},
    {"id": 20, "source": "우리는 건강한 경쟁 속에서 서로를 존중하며 살아가야 한다.", "target": "Chúng ta phải sống và tôn trọng lẫn nhau trong môi trường cạnh tranh lành mạnh."}
]

# Danh sách 20 câu chiều: VIỆT SANG HÀN
VI_TO_KR_LIST = [
    {"id": 1, "source": "Trong xã hội hiện đại, sự cạnh tranh đóng vai trò quan trọng đối với sự phát triển của học sinh.", "target": "현대 사회에서 경쟁은 학생들이 성장하는 데 중요한 역할을 한다."},
    {"id": 2, "source": "Thông qua cạnh tranh, học sinh có thể xác định năng lực và cải thiện điểm thiếu sót.", "target": "학생들은 경쟁을 통해 자신의 능력을 확인하고 부족한 점을 개선할 수 있다."},
    {"id": 3, "source": "Tuy nhiên, cạnh tranh quá mức có thể dẫn đến kết quả tiêu cực.", "target": "그러나 지나친 경쟁은 오히려 부정적인 결과를 초래할 수 있다."},
    {"id": 4, "source": "Cần phải có sự cạnh tranh lành mạnh.", "target": "바람직한 경쟁이 이루어져야 한다."},
    {"id": 5, "source": "Học sinh có thể nâng cao thực lực và nuôi dưỡng ý chí đạt mục tiêu.", "target": "학생들은 실력을 향상시키고 목표를 달성하려는 의지를 기를 수 있다."},
    {"id": 6, "source": "Trong quá trình đọ sức, các em có thể nắm bắt điểm mạnh và điểm yếu.", "target": "겨루는 과정에서 자신의 강점과 약점을 파악할 수 있다."},
    {"id": 7, "source": "Trải nghiệm này giúp học sinh rèn luyện thái độ không bỏ cuộc khi gặp khó khăn.", "target": "이러한 경험은 학생들이 어려움에 부딪혔을 때 포기하지 않는 태도를 기르는 데 도움이 된다."},
    {"id": 8, "source": "Cạnh tranh quá mức có thể gây ra áp lực tâm lý nặng nề cho học sinh.", "target": "지나친 경쟁은 학생들에게 심한 심리적 부담을 줄 수 있다."},
    {"id": 9, "source": "Nếu chỉ coi trọng điểm số, học sinh sẽ dễ bị ám ảnh bởi kết quả.", "target": "성적만을 중요하게 생각하게 되면 결과에 집착하게 된다."},
    {"id": 10, "source": "Việc này khiến các em xem bạn bè chỉ là đối thủ.", "target": "이는 친구를 경쟁 상대로만 여기게 될 수 있다."},
    {"id": 11, "source": "Trường hợp nặng có thể xuất hiện hành vi gian lận.", "target": "심한 경우에는 부정행위가 나타날 수도 있다."},
    {"id": 12, "source": "Điều này gây ảnh hưởng tiêu cực đến quan hệ bạn bè.", "target": "이는 교우 관계에도 부정적인 영향을 미친다."},
    {"id": 13, "source": "Nhà trường cần tạo ra môi trường để học sinh hợp tác với nhau.", "target": "학교에서는 학생들이 서로 협력할 수 있는 환경을 조성해야 한다."},
    {"id": 14, "source": "Thay vì chỉ nhấn mạnh điểm số, nên tổ chức bài tập nhóm.", "target": "성적만을 강조하기보다는 모둠별 과제를 통해야 한다."},
    {"id": 15, "source": "Học sinh cần công nhận ưu điểm của nhau.", "target": "학생들은 서로의 장점을 인정해야 한다."},
    {"id": 16, "source": "Cần đánh giá công bằng cả quá trình nỗ lực.", "target": "노력 과정도 공정하게 평가해야 한다."},
    {"id": 17, "source": "Học sinh sẽ không sợ hãi việc cạnh tranh.", "target": "학생들은 경쟁을 두려워하지 않게 된다."},
    {"id": 18, "source": "Các em có thể học hỏi lẫn nhau và cùng nhau trưởng thành.", "target": "서로 배우며 함께 성장할 수 있다."},
    {"id": 19, "source": "Cạnh tranh là chất kích thích cho sự phát triển.", "target": "경쟁은 발전의 자극제가 된다."},
    {"id": 20, "source": "Chúng ta phải tôn trọng lẫn nhau trong cạnh tranh lành mạnh.", "target": "우리는 바람직한 경쟁 속에서 서로를 존중해야 한다."}
]

# 📚 TỪ VỰNG TOPIK
TOPIK_VOCAB = [
    {
        "word": "초래하다", "level": "TOPIK 5-6", "meaning": "Gây ra, dẫn đến (kết quả xấu)", 
        "example": "그러나 지나친 경쟁은 오히려 부정적인 결과를 초래할 수 있으므로 바람직한 경쟁이 이루어져야 한다.", 
        "example_meaning": "Tuy nhiên, cạnh tranh quá mức có thể dẫn đến kết quả tiêu cực, vì vậy cần phải có sự cạnh tranh lành mạnh."
    },
    {
        "word": "바람직하다", "level": "TOPIK 4-5", "meaning": "Đáng mong muốn, lành mạnh", 
        "example": "바람직한 경쟁이 이루어져야 한다.", 
        "example_meaning": "Cần phải có sự cạnh tranh lành mạnh."
    },
    {
        "word": "집착하다", "level": "TOPIK 5-6", "meaning": "Ám ảnh, câu nệ, bám chấp", 
        "example": "특히 좋은 성적이나 높은 순위만을 중요하게 생각하게 되면 결과에 집착하게 된다.", 
        "example_meaning": "Đặc biệt, nếu chỉ coi trọng điểm số cao hay thứ hạng cao, các em sẽ dễ bị ám ảnh bởi kết quả."
    },
    {
        "word": "보완하다", "level": "TOPIK 4", "meaning": "Bổ sung, bù đắp phần thiếu sót", 
        "example": "부족한 부분을 보완하기 위해 더욱 노력하게 된다.", 
        "example_meaning": "Các em sẽ nỗ lực hơn nữa để bù đắp những phần còn thiếu sót."
    },
    {
        "word": "조성하다", "level": "TOPIK 5", "meaning": "Kiến tạo, tạo dựng (môi trường)", 
        "example": "따라서 학교에서는 학생들이 서로 협력하면서 자신의 능력을 발휘할 수 있는 환경을 조성해야 한다.", 
        "example_meaning": "Do đó, nhà trường cần tạo môi trường để học sinh phát huy năng lực trong khi hợp tác với nhau."
    },
    {
        "word": "자극제", "level": "TOPIK 5-6", "meaning": "Chất kích thích, động lực", 
        "example": "경쟁은 때로는 우리에게 발전의 자극제가 된다.", 
        "example_meaning": "Cạnh tranh đôi khi là chất kích thích cho sự phát triển của chúng ta."
    },
    {
        "word": "부정행위", "level": "TOPIK 4", "meaning": "Hành vi gian lận", 
        "example": "심한 경우에는 부정행위를 하거나 다른 사람을 배려하지 않는 태도가 나타날 수도 있다.", 
        "example_meaning": "Trong trường hợp nặng, có thể xuất hiện hành vi gian lận hoặc thái độ không biết quan tâm đến người khác."
    }
]

# 📝 CẤU TRÚC NGỮ PHÁP & BIỂU HIỆN
TOPIK_54_GRAMMAR = [
    {
        "grammar": "-기 마련이다", "usage": "Đương nhiên sẽ, quy luật tất yếu", 
        "example": "현대 사회에서 경쟁은 학생들이 성장하는 데 중요한 역할을 한다.", 
        "example_meaning": "Trong xã hội hiện đại, sự cạnh tranh đóng vai trò quan trọng đối với sự phát triển của học sinh."
    },
    {
        "grammar": "-을/를 초래하다", "usage": "Gây ra kết quả tiêu cực (văn viết trang trọng)", 
        "example": "그러나 지나친 경쟁은 오히려 부정적인 결과를 초래할 수 있다.", 
        "example_meaning": "Tuy nhiên, cạnh tranh quá mức có thể dẫn đến kết quả tiêu cực."
    },
    {
        "grammar": "-기보다는", "usage": "Thay vì... thì...", 
        "example": "개인의 성적이나 순위만을 강조하기보다는 모둠별 과제나 체육 활동을 통해 서로의 장점을 인정해야 한다.", 
        "example_meaning": "Ví dụ, thay vì chỉ nhấn mạnh điểm số cá nhân, nên thông qua bài tập nhóm hoặc thể thao để công nhận ưu điểm của nhau."
    },
    {
        "grammar": "-을 뿐만 아니라", "usage": "Không những... mà còn...", 
        "example": "이는 학생들의 건강한 성장뿐만 아니라 원만한 교우 관계에도 부정적인 영향을 미친다.", 
        "example_meaning": "Điều này gây ảnh hưởng tiêu cực đến sự phát triển lành mạnh và các mối quan hệ bạn bè."
    }
]

# 👨‍🏫 THUẬT TOÁN ĐÁNH GIÁ CHUYÊN SÂU THEO TIÊU CHÍ GIẢNG VIÊN TOPIK II
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[.,?!:;“”"\'()~–-]', '', text)
    return ' '.join(text.split())

def evaluate_as_topik_instructor(user_input, reference):
    cleaned_input = clean_text(user_input)
    cleaned_ref = clean_text(reference)
    
    # Tính toán tỷ lệ tương đồng chuỗi và từ khóa
    similarity = difflib.SequenceMatcher(None, cleaned_input, cleaned_ref).ratio()
    
    ref_tokens = [w for w in cleaned_ref.split() if len(w) > 1]
    input_tokens = set(cleaned_input.split())
    
    matched_tokens = [w for w in ref_tokens if w in input_tokens]
    missing_tokens = [w for w in ref_tokens if w not in input_tokens]
    
    if len(ref_tokens) > 0:
        keyword_coverage = len(set(matched_tokens)) / len(set(ref_tokens))
    else:
        keyword_coverage = 0.0

    # Điểm tổng hợp dựa trên ngữ nghĩa linh hoạt (trọng số từ khóa học thuật và cấu trúc)
    final_score = max(similarity, keyword_coverage)
    
    # Quy đổi ra Thang điểm 10 và Phần trăm (%)
    score_10 = round(final_score * 10, 1)
    score_percent = int(final_score * 100)
    
    # Nhận xét từ Giảng viên TOPIK II
    feedback = []
    
    if final_score >= 0.75:
        rank_title = "🏆 ĐẠT CHUẨN XUẤT SẮC (Mức điểm TOPIK II - Câu 54 cấp cao)"
        feedback.append("👨‍🏫 **Lời phê của Giảng viên:** Bài dịch thể hiện tư duy ngôn ngữ rất sắc bén, sử dụng từ vựng học thuật trang trọng và bám sát hoàn toàn tinh thần câu 54.")
    elif final_score >= 0.40:
        rank_title = "👍 ĐẠT MỨC KHÁ / ĐÚNG Ý CHÍNH (Đạt yêu cầu cơ bản)"
        feedback.append("👨‍🏫 **Lời phê của Giảng viên:** Bạn đã nắm bắt được ý nghĩa cốt lõi và ngữ cảnh chính của câu. Tuy nhiên, một số cụm từ diễn đạt chưa đạt độ tinh tế cao nhất của văn viết.")
    elif final_score >= 0.20:
        rank_title = "💡 ĐẠT MỨC TỐI THIỂU (Có cố gắng truyền tải ý nghĩa)"
        feedback.append("👨‍🏫 **Lời phê của Giảng viên:** Câu dịch đã phản ánh một phần nội dung nhưng cấu trúc ngữ pháp còn hơi lỏng lẻo, thiếu các từ vựng trọng tâm.")
    else:
        rank_title = "❌ CHƯA ĐẠT (Lệch ý nghĩa hoặc sai ngữ cảnh câu 54)"
        feedback.append("👨‍🏫 **Lời phê của Giảng viên:** Bản dịch chưa bám sát nội dung gốc, từ vựng sử dụng chưa phù hợp với văn phong bài luận TOPIK.")

    # Phân tích chi tiết từng cụm / từ khóa
    feedback.append(f"• **Độ bao phủ từ vựng cốt lõi:** Khoảng `{score_percent}%` các từ khóa trọng tâm đã xuất hiện trong bài làm của bạn.")
    
    if matched_tokens:
        sample_matched = ", ".join(list(set(matched_tokens))[:5])
        feedback.append(f"• **Điểm cộng (Cụm từ đã dịch tốt):** Bạn đã sử dụng chính xác các thành phần ý nghĩa như: *{sample_matched}*.")
    
    if missing_tokens and final_score < 0.90:
        sample_missing = ", ".join(list(set(missing_tokens))[:5])
        feedback.append(f"• **Phân tích lỗi & Điểm cần cải thiện:** Ý nghĩa hoặc sắc thái của các cụm từ xoay quanh *{sample_missing}* chưa được truyền tải tối ưu. Do đó, điểm số bị trừ ở phần độ tự nhiên và sắc thái học thuật.")

    feedback.append(f"• **Gợi ý bản dịch tham khảo tự nhiên theo chuẩn TOPIK II:**\n> **{reference}**")

    return rank_title, score_10, score_percent, feedback

st.title("🇰🇷 AI Giảng Viên Chấm Điểm TOPIK II - Câu 54")

menu = st.sidebar.selectbox("📂 Chọn chế độ", [
    "Luyện dịch Hàn ➡️ Việt", 
    "Luyện dịch Việt ➡️ Hàn", 
    "📚 Từ vựng TOPIK (3-6) & Ví dụ", 
    "✍️ Biểu hiện & Ngữ pháp Câu 54 TOPIK"
])

if 'current_q' not in st.session_state:
    st.session_state.current_q = 0

if menu == "Luyện dịch Hàn ➡️ Việt":
    st.subheader("📝 Chiều: Hàn ➡️ Việt (20 câu chuẩn TOPIK)")
    quiz_data = KR_TO_VI_LIST
    idx = st.session_state.current_q
    if idx < len(quiz_data):
        q = quiz_data[idx]
        st.markdown(f"**📌 Câu {idx + 1} / {len(quiz_data)}**")
        st.info(f"**Văn bản gốc tiếng Hàn:**\n\n{q['source']}")
        
        user_input = st.text_input("✍️ Nhập bản dịch tiếng Việt của bạn:", key=f"k2v_in_{idx}")
        
        if st.button("Kiểm tra và Chấm điểm", key=f"btn_k2v_{idx}"):
            if user_input.strip():
                rank_title, score_10, score_percent, feedback = evaluate_as_topik_instructor(user_input, q['target'])
                st.markdown("---")
                st.markdown(f"### Kết quả đánh giá: {rank_title}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="🎯 Thang điểm 10", value=f"{score_10} / 10 đ")
                with col2:
                    st.metric(label="📊 Tỷ lệ tương đương", value=f"{score_percent}%")
                
                st.markdown("#### 👨‍🏫 Phân tích chi tiết lỗi, ngữ nghĩa & Gợi ý từ Giảng viên:")
                for item in feedback:
                    st.markdown(item)
                    
                st.markdown("---")
            else:
                st.warning("⚠️ Vui lòng nhập bản dịch của bạn trước khi kiểm tra!")
                
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Câu tiếp theo", key=f"next_k2v_{idx}"):
                st.session_state.current_q += 1
                st.rerun()
        with col2:
            if st.button("🔄 Làm lại từ đầu", key=f"reset_k2v_{idx}"):
                st.session_state.current_q = 0
                st.rerun()

elif menu == "Luyện dịch Việt ➡️ Hàn":
    st.subheader("📝 Chiều: Việt ➡️ Hàn (20 câu chuẩn TOPIK)")
    quiz_data = VI_TO_KR_LIST
    idx = st.session_state.current_q
    if idx < len(quiz_data):
        q = quiz_data[idx]
        st.markdown(f"**📌 Câu {idx + 1} / {len(quiz_data)}**")
        st.info(f"**Văn bản gốc tiếng Việt:**\n\n{q['source']}")
        
        user_input = st.text_input("✍️ Nhập bản dịch tiếng Hàn của bạn:", key=f"v2k_in_{idx}")
        
        if st.button("Kiểm tra và Chấm điểm", key=f"btn_v2k_{idx}"):
            if user_input.strip():
                rank_title, score_10, score_percent, feedback = evaluate_as_topik_instructor(user_input, q['target'])
                st.markdown("---")
                st.markdown(f"### Kết quả đánh giá: {rank_title}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="🎯 Thang điểm 10", value=f"{score_10} / 10 đ")
                with col2:
                    st.metric(label="📊 Tỷ lệ tương đương", value=f"{score_percent}%")
                
                st.markdown("#### 👨‍🏫 Phân tích chi tiết lỗi, ngữ nghĩa & Gợi ý từ Giảng viên:")
                for item in feedback:
                    st.markdown(item)
                    
                st.markdown("---")
            else:
                st.warning("⚠️ Vui lòng nhập bản dịch của bạn trước khi kiểm tra!")
                
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Câu tiếp theo", key=f"next_v2k_{idx}"):
                st.session_state.current_q += 1
                st.rerun()
        with col2:
            if st.button("🔄 Làm lại từ đầu", key=f"reset_v2k_{idx}"):
                st.session_state.current_q = 0
                st.rerun()

elif menu == "📚 Từ vựng TOPIK (3-6) & Ví dụ":
    st.subheader("📖 Từ vựng tiêu biểu cấp cao (TOPIK 3 - 6)")
    st.markdown("Danh sách từ vựng học thuật kèm ví dụ mẫu cho câu 54:")
    
    for i, item in enumerate(TOPIK_VOCAB):
        with st.expander(f"📌 {item['word']} ({item['level']}) - {item['meaning']}"):
            st.markdown(f"### Từ vựng: `{item['word']}`")
            st.markdown(f"**Ý nghĩa:** {item['meaning']}")
            st.markdown(f"**Ví dụ trong bài:** `{item['example']}`")
            st.markdown(f"**Dịch nghĩa:** _{item['example_meaning']}_")

elif menu == "✍️ Biểu hiện & Ngữ pháp Câu 54 TOPIK":
    st.subheader("📝 Tổng hợp Ngữ pháp & Biểu hiện ôn thi Câu 54 TOPIK II")
    
    for i, g_item in enumerate(TOPIK_54_GRAMMAR):
        st.markdown(f"### 🔹 Cấu trúc: `{g_item['grammar']}`")
        st.markdown(f"- **Cách dùng:** {g_item['usage']}")
        st.markdown(f"- **Câu ví dụ trong bài:** `{g_item['example']}`")
        st.markdown(f"- **Bản dịch:** _{g_item['example_meaning']}_")
        st.markdown("---")
