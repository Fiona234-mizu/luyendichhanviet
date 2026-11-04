# -*- coding: utf-8 -*-
"""
Ứng dụng luyện dịch Hàn–Việt / Việt–Hàn theo định hướng TOPIK II câu 54.
Chấm ngữ nghĩa bằng OpenAI API; phát âm tiếng Hàn bằng OpenAI Text-to-Speech.
"""
import os
import json
import hashlib
from typing import Any, Dict

import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="AI Giảng viên chấm dịch TOPIK II",
    page_icon="🇰🇷",
    layout="wide",
)

# ------------------------- Cấu hình -------------------------
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
DEFAULT_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
DEFAULT_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
DEFAULT_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")

def get_secret(name: str, default: str = "") -> str:
    """Đọc cấu hình từ Streamlit Secrets trước, sau đó từ biến môi trường."""
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

def check_password() -> None:
    """Chỉ bật khóa ứng dụng nếu APP_PASSWORD được cấu hình."""
    if not APP_PASSWORD:
        return
    if st.session_state.get("authenticated"):
        return
    st.title("🔒 Đăng nhập")
    entered = st.text_input("Mật khẩu ứng dụng", type="password")
    if st.button("Đăng nhập"):
        if entered == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mật khẩu chưa chính xác.")
    st.stop()

check_password()

st.title("🇰🇷 AI Giảng viên chấm dịch TOPIK II – Câu 54")
st.caption(
    "Luyện dịch hai chiều, phân tích ngữ nghĩa theo từng cụm, "
    "sửa tiếng Hàn và nghe phát âm tiếng Hàn."
)

# ------------------------- Dữ liệu học tập gốc -------------------------
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
    {"id": 14, "source": "Thay vì chỉ nhấn mạnh điểm số, nên tổ chức bài tập nhóm.", "target": "성적만을 강조하기보다는 모둠별 과제를 실시하는 것이 좋다."},
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
        "word": "자극제", "level": "TOPIK 5-6", "meaning": "Động lực, yếu tố thúc đẩy sự phát triển", 
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
        "grammar": "-기 마련이다", "usage": "Đương nhiên sẽ, thường có xu hướng tất yếu xảy ra", 
        "example": "지나친 경쟁은 학생들에게 심한 스트레스를 주기 마련이다.", 
        "example_meaning": "Cạnh tranh quá mức thường tất yếu gây ra căng thẳng nghiêm trọng cho học sinh."
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


# ------------------------- AI chấm dịch -------------------------
KR_TO_VI_WEIGHTS = {
    "semantic_accuracy": 40,
    "phrase_accuracy": 25,
    "context": 15,
    "target_naturalness": 10,
    "completeness": 10,
}
VI_TO_KR_WEIGHTS = {
    "semantic_accuracy": 35,
    "grammar": 25,
    "vocabulary_collocation": 20,
    "topik_style": 10,
    "spelling_particles": 10,
}

CRITERION_LABELS = {
    "semantic_accuracy": "Truyền tải đúng ý nghĩa",
    "phrase_accuracy": "Độ chính xác của cụm từ",
    "context": "Mức độ phù hợp ngữ cảnh",
    "target_naturalness": "Độ tự nhiên của tiếng Việt",
    "completeness": "Tính đầy đủ, không thêm/bớt ý",
    "grammar": "Ngữ pháp tiếng Hàn",
    "vocabulary_collocation": "Từ vựng và kết hợp từ",
    "topik_style": "Văn phong nghị luận TOPIK 54",
    "spelling_particles": "Chính tả, tiểu từ và khoảng cách",
}

SYSTEM_PROMPT = """
Bạn là giảng viên tiếng Hàn chuyên sâu, đánh giá bản dịch Hàn–Việt và Việt–Hàn
cho người học hướng đến TOPIK 5–6, đặc biệt là văn phong nghị luận TOPIK II câu 54.

NGUYÊN TẮC BẮT BUỘC:
1. Đánh giá ý nghĩa, ngữ cảnh, quan hệ logic và sắc thái; KHÔNG chấm bằng cách
   đếm từ trùng hoặc so sánh chuỗi.
2. Không bắt buộc bản dịch giống đáp án tham khảo. Chấp nhận từ đồng nghĩa,
   cách diễn đạt khác và cấu trúc khác nếu đúng nghĩa, tự nhiên, đúng ngữ cảnh.
3. Chỉ trừ điểm khi có lỗi thực chất: sai nghĩa, đảo quan hệ, thiếu ý quan trọng,
   thêm ý không có căn cứ, dùng từ sai sắc thái, ngữ pháp sai hoặc diễn đạt khó hiểu.
4. Phân tích từng cụm có thể đối chiếu được giữa câu nguồn và câu người học.
   Không được gán ghép máy móc theo từng từ nếu hai ngôn ngữ có trật tự khác nhau.
5. Với Việt→Hàn, đánh giá ngữ pháp, tiểu từ, chia đuôi câu, kết hợp từ và văn phong
   viết nghị luận. Không ép buộc chỉ một cấu trúc ngữ pháp.
6. Với Hàn→Việt, ưu tiên bản dịch tiếng Việt đúng nghĩa, rõ ràng, tự nhiên.
7. Tỷ lệ ngữ nghĩa là ước lượng chuyên môn trên thang 0–100, KHÔNG phải xác suất
   thống kê hay chứng nhận chính thức của TOPIK.
8. Nếu thiếu ngữ cảnh hoặc có nhiều cách hiểu, nói rõ điểm chưa chắc chắn.
9. Không bịa lỗi. Nếu bản dịch đúng, hãy ghi nhận đúng và không cố tìm lỗi.
10. Trả lời bằng tiếng Việt, giữ nguyên ví dụ tiếng Hàn khi phân tích.

Chỉ trả về JSON hợp lệ, không thêm markdown hoặc văn bản bên ngoài JSON.
"""

def build_user_prompt(direction: str, source: str, user_translation: str,
                      reference: str, weights: Dict[str, int]) -> str:
    direction_text = (
        "Hàn sang Việt: câu nguồn là tiếng Hàn, bài làm là tiếng Việt."
        if direction == "kr_vi"
        else "Việt sang Hàn: câu nguồn là tiếng Việt, bài làm là tiếng Hàn."
    )
    return f"""
HƯỚNG DỊCH: {direction_text}

CÂU NGUỒN:
{source}

BẢN DỊCH CỦA NGƯỜI HỌC:
{user_translation}

BẢN DỊCH THAM KHẢO (chỉ dùng để hiểu nội dung, KHÔNG coi là đáp án duy nhất):
{reference}

TRỌNG SỐ TIÊU CHÍ:
{json.dumps(weights, ensure_ascii=False)}

Hãy trả về JSON theo cấu trúc:
{{
  "overall_comment": "Nhận xét tổng quan cụ thể",
  "semantic_accuracy_percent": 0,
  "criteria": {{
    "criterion_key": {{
      "score": 0,
      "max_score": 100,
      "comment": "Giải thích ngắn gọn"
    }}
  }},
  "segments": [
    {{
      "source_chunk": "cụm trong câu nguồn",
      "user_chunk": "cụm tương ứng trong bài làm hoặc ghi Không có",
      "status": "Chính xác | Chấp nhận được | Chưa tự nhiên | Sai nghĩa | Thiếu ý",
      "explanation": "Giải thích tại sao",
      "suggestion": "Cách sửa nếu cần",
      "accepted_alternatives": ["cách diễn đạt khác vẫn đúng"]
    }}
  ],
  "correct_points": ["những phần người học làm đúng"],
  "errors": ["lỗi thực sự; nếu không có, trả mảng rỗng"],
  "revised_translation": "bản dịch sửa tốt nhất, tự nhiên",
  "other_valid_translations": ["cách dịch khác hợp lệ"],
  "vocabulary_notes": [
    {{"korean": "từ/cụm tiếng Hàn", "meaning": "nghĩa tiếng Việt", "note": "sắc thái/cách dùng"}}
  ],
  "grammar_notes": [
    {{"pattern": "cấu trúc", "explanation": "giải thích", "example": "ví dụ tiếng Hàn"}}
  ],
  "confidence_note": "mức độ chắc chắn và giới hạn nếu có"
}}

LƯU Ý:
- semantic_accuracy_percent chỉ đánh giá mức độ giữ đúng ý nghĩa câu nguồn.
- criteria chỉ dùng đúng các khóa trong trọng số được cung cấp; điểm mỗi tiêu chí từ 0 đến 100.
- Với segments, hãy chia theo cụm ý nghĩa, thường 2–8 cụm tùy độ dài câu.
- Nếu không có lỗi thì errors là [] và phải nói rõ bản dịch đã tốt.
- Không đánh đồng cách diễn đạt khác đáp án tham khảo với lỗi.
- Bản dịch sửa phải giữ nguyên nội dung, không tự ý thêm ý.
"""

def get_openai_client() -> OpenAI:
    api_key = st.session_state.get("openai_api_key") or get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Chưa có OpenAI API Key. Hãy nhập API Key ở thanh bên hoặc cấu hình OPENAI_API_KEY."
        )
    return OpenAI(api_key=api_key)

def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise

def evaluate_translation(direction: str, source: str, user_translation: str,
                          reference: str, model: str) -> Dict[str, Any]:
    weights = KR_TO_VI_WEIGHTS if direction == "kr_vi" else VI_TO_KR_WEIGHTS
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(
                direction, source, user_translation, reference, weights
            )},
        ],
    )
    content = response.choices[0].message.content or "{}"
    result = _extract_json(content)

    # Tính điểm tổng theo trọng số tại ứng dụng, không tin điểm tổng do mô hình tự đặt.
    criteria = result.get("criteria", {})
    weighted_total = 0.0
    used_weight = 0
    for key, weight in weights.items():
        item = criteria.get(key, {})
        try:
            score = max(0.0, min(100.0, float(item.get("score", 0))))
        except (TypeError, ValueError):
            score = 0.0
        weighted_total += score * weight
        used_weight += weight
    result["weighted_score_10"] = round((weighted_total / max(used_weight, 1)) / 10, 1)
    result["weighted_score_percent"] = round(weighted_total / max(used_weight, 1))
    result["semantic_accuracy_percent"] = max(
        0, min(100, int(result.get("semantic_accuracy_percent", 0)))
    )
    return result

def render_evaluation(result: Dict[str, Any], direction: str) -> None:
    st.divider()
    st.subheader("📊 Kết quả chấm")
    c1, c2, c3 = st.columns(3)
    c1.metric("Điểm tổng", f"{result['weighted_score_10']}/10")
    c2.metric("Chất lượng tổng hợp", f"{result['weighted_score_percent']}%")
    c3.metric("Tương đương ngữ nghĩa", f"{result['semantic_accuracy_percent']}%")
    st.caption(
        "Các tỷ lệ là ước lượng đánh giá của AI, không phải xác suất tuyệt đối "
        "hay thang điểm chính thức của TOPIK."
    )
    st.info(result.get("overall_comment", "Chưa có nhận xét tổng quan."))

    st.markdown("### 1. Điểm theo tiêu chí")
    weights = KR_TO_VI_WEIGHTS if direction == "kr_vi" else VI_TO_KR_WEIGHTS
    criteria = result.get("criteria", {})
    for key, weight in weights.items():
        item = criteria.get(key, {})
        score = item.get("score", 0)
        label = CRITERION_LABELS.get(key, key)
        st.markdown(f"**{label}** — {score}/100 (trọng số {weight}%)")
        st.progress(max(0.0, min(1.0, float(score or 0) / 100)))
        if item.get("comment"):
            st.caption(item["comment"])

    st.markdown("### 2. Đối chiếu từng cụm từ")
    for i, seg in enumerate(result.get("segments", []), start=1):
        status = seg.get("status", "Chưa phân loại")
        with st.expander(f"{i}. {seg.get('source_chunk', '')} — {status}", expanded=True):
            st.markdown(f"**Cụm bạn dịch:** {seg.get('user_chunk', 'Không có')}")
            st.markdown(f"**Nhận xét:** {seg.get('explanation', '')}")
            if seg.get("suggestion"):
                st.markdown(f"**Gợi ý sửa:** {seg['suggestion']}")
            alternatives = seg.get("accepted_alternatives", [])
            if alternatives:
                st.markdown("**Những cách diễn đạt khác vẫn chấp nhận được:**")
                for alt in alternatives:
                    st.write(f"• {alt}")

    st.markdown("### 3. Những điểm bạn đã làm đúng")
    correct = result.get("correct_points", [])
    if correct:
        for item in correct:
            st.success(item)
    else:
        st.write("AI chưa nêu điểm mạnh cụ thể.")

    st.markdown("### 4. Lỗi cần sửa")
    errors = result.get("errors", [])
    if errors:
        for item in errors:
            st.error(item)
    else:
        st.success("Không phát hiện lỗi thực chất trong bản dịch.")

    st.markdown("### 5. Bản dịch tham khảo đã hiệu chỉnh")
    st.write(result.get("revised_translation", "Chưa có bản dịch hiệu chỉnh."))

    alternatives = result.get("other_valid_translations", [])
    if alternatives:
        st.markdown("**Các cách dịch khác có thể chấp nhận:**")
        for alt in alternatives:
            st.write(f"• {alt}")

    vocab = result.get("vocabulary_notes", [])
    if vocab:
        st.markdown("### 6. Từ vựng cần ghi nhớ")
        for item in vocab:
            st.write(
                f"**{item.get('korean', '')}** — {item.get('meaning', '')}. "
                f"{item.get('note', '')}"
            )

    grammar = result.get("grammar_notes", [])
    if grammar:
        st.markdown("### 7. Ngữ pháp cần ghi nhớ")
        for item in grammar:
            st.write(
                f"**{item.get('pattern', '')}**: {item.get('explanation', '')}"
            )
            if item.get("example"):
                st.caption(item["example"])

    if result.get("confidence_note"):
        st.caption(f"Giới hạn đánh giá: {result['confidence_note']}")

# ------------------------- Phát âm tiếng Hàn -------------------------
@st.cache_data(show_spinner=False, ttl=86400, max_entries=100)
def make_korean_audio(text: str, model: str, voice: str, api_key_fingerprint: str) -> bytes:
    """Tạo MP3 qua OpenAI TTS và lưu cache theo câu/giọng/model."""
    # api_key_fingerprint chỉ tham gia khóa cache; không được dùng để xác thực.
    client = get_openai_client()
    audio_response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="mp3",
    )
    return audio_response.content

def pronunciation_player(text: str, key: str = "audio") -> None:
    if not text or not text.strip():
        return
    if not any("\uac00" <= ch <= "\ud7a3" for ch in text):
        st.caption("Nội dung này không có ký tự tiếng Hàn để phát âm.")
        return
    if st.button("🔊 Tạo và nghe phát âm tiếng Hàn", key=f"play_{key}"):
        try:
            api_key = st.session_state.get("openai_api_key") or get_secret("OPENAI_API_KEY")
            if not api_key:
                st.warning("Nhập OpenAI API Key ở thanh bên để sử dụng phát âm.")
                return
            fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:12]
            with st.spinner("Đang tạo giọng đọc tiếng Hàn..."):
                audio = make_korean_audio(
                    text,
                    st.session_state.get("tts_model", DEFAULT_TTS_MODEL),
                    st.session_state.get("tts_voice", DEFAULT_TTS_VOICE),
                    fingerprint,
                )
            st.audio(audio, format="audio/mp3")
        except Exception as exc:
            st.error(f"Không tạo được âm thanh: {exc}")

# ------------------------- Thanh bên -------------------------
with st.sidebar:
    st.header("⚙️ Cài đặt")
    st.caption("AI chấm dịch và TTS cần OpenAI API Key.")
    saved_key = get_secret("OPENAI_API_KEY")
    if saved_key:
        st.success("Đã tìm thấy API Key trong cấu hình.")
    else:
        st.text_input(
            "OpenAI API Key",
            type="password",
            key="openai_api_key",
            help="Chỉ lưu trong phiên chạy hiện tại. Không chia sẻ API Key.",
        )
    st.text_input("Mô hình chấm dịch", value=DEFAULT_TEXT_MODEL, key="text_model")
    st.selectbox(
        "Mô hình phát âm",
        options=["tts-1", "tts-1-hd", "gpt-4o-mini-tts"],
        index=0,
        key="tts_model",
    )
    st.selectbox(
        "Giọng đọc",
        options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        index=0,
        key="tts_voice",
        help="Các giọng có thể phát âm tiếng Hàn; chất giọng và độ tự nhiên có thể khác nhau.",
    )
    st.caption("Chi phí API chấm dịch và tạo âm thanh được tính theo tài khoản OpenAI của bạn.")

# ------------------------- Giao diện luyện dịch -------------------------
MENU_K2V = "Luyện dịch Hàn ➡️ Việt"
MENU_V2K = "Luyện dịch Việt ➡️ Hàn"
MENU_VOCAB = "📚 Từ vựng TOPIK & phát âm"
MENU_GRAMMAR = "✍️ Biểu hiện & ngữ pháp TOPIK 54"

menu = st.sidebar.radio(
    "📂 Chọn chế độ",
    [MENU_K2V, MENU_V2K, MENU_VOCAB, MENU_GRAMMAR, "🧑‍🎓 Chấm câu tự nhập"],
)

if "question_index_k2v" not in st.session_state:
    st.session_state.question_index_k2v = 0
if "question_index_v2k" not in st.session_state:
    st.session_state.question_index_v2k = 0

def show_quiz(direction: str) -> None:
    is_k2v = direction == "kr_vi"
    data = KR_TO_VI_LIST if is_k2v else VI_TO_KR_LIST
    index_key = "question_index_k2v" if is_k2v else "question_index_v2k"
    title = MENU_K2V if is_k2v else MENU_V2K
    st.subheader(title)
    idx = st.session_state[index_key]

    if idx >= len(data):
        st.success("Bạn đã hoàn thành toàn bộ câu hỏi trong phần này!")
        if st.button("🔄 Làm lại từ câu 1", key=f"restart_{direction}"):
            st.session_state[index_key] = 0
            st.rerun()
        return

    q = data[idx]
    st.markdown(f"**Câu {idx + 1}/{len(data)}**")
    source_label = "Câu gốc tiếng Hàn" if is_k2v else "Câu gốc tiếng Việt"
    st.info(f"**{source_label}:**\n\n{q['source']}")
    if is_k2v:
        pronunciation_player(q["source"], f"source_{direction}_{idx}")
        input_label = "Nhập bản dịch tiếng Việt của bạn"
    else:
        input_label = "Nhập bản dịch tiếng Hàn của bạn"
    answer = st.text_area(input_label, key=f"answer_{direction}_{idx}", height=110)

    if not is_k2v and answer.strip():
        pronunciation_player(answer, f"answer_{direction}_{idx}")

    if st.button("🧠 Chấm và phân tích bản dịch", type="primary", key=f"grade_{direction}_{idx}"):
        if not answer.strip():
            st.warning("Bạn hãy nhập bản dịch trước khi chấm.")
        else:
            try:
                with st.spinner("AI đang phân tích ngữ nghĩa và từng cụm từ..."):
                    result = evaluate_translation(
                        direction, q["source"], answer.strip(), q["target"],
                        st.session_state.get("text_model", DEFAULT_TEXT_MODEL),
                    )
                st.session_state[f"result_{direction}_{idx}"] = result
            except Exception as exc:
                st.error(f"Không thể chấm bài: {exc}")
    stored = st.session_state.get(f"result_{direction}_{idx}")
    if stored:
        render_evaluation(stored, direction)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ Câu tiếp theo", key=f"next_{direction}_{idx}"):
            st.session_state[index_key] += 1
            st.rerun()
    with col2:
        if st.button("🔄 Làm lại phần này", key=f"reset_{direction}_{idx}"):
            st.session_state[index_key] = 0
            st.rerun()

if menu == MENU_K2V:
    show_quiz("kr_vi")

elif menu == MENU_V2K:
    show_quiz("vi_kr")

elif menu == MENU_VOCAB:
    st.subheader("📚 Từ vựng TOPIK – nghe và luyện phát âm")
    st.caption("Nhấn nút dưới từng từ hoặc ví dụ để nghe giọng đọc tiếng Hàn.")
    for i, item in enumerate(TOPIK_VOCAB):
        with st.expander(f"{item['word']} ({item['level']}) – {item['meaning']}"):
            st.markdown(f"### {item['word']}")
            st.write(item["meaning"])
            pronunciation_player(item["word"], f"vocab_word_{i}")
            st.markdown(f"**Ví dụ:** {item['example']}")
            st.write(item["example_meaning"])
            pronunciation_player(item["example"], f"vocab_example_{i}")

elif menu == MENU_GRAMMAR:
    st.subheader("✍️ Biểu hiện và ngữ pháp TOPIK II câu 54")
    for i, item in enumerate(TOPIK_54_GRAMMAR):
        with st.expander(item["grammar"]):
            st.write(item["usage"])
            st.markdown(f"**Ví dụ:** {item['example']}")
            st.write(item["example_meaning"])
            pronunciation_player(item["example"], f"grammar_{i}")

elif menu == "🧑‍🎓 Chấm câu tự nhập":
    st.subheader("🧑‍🎓 Luyện dịch với câu tự chọn")
    direction_label = st.radio(
        "Chọn chiều dịch",
        ["Hàn ➡️ Việt", "Việt ➡️ Hàn"],
        horizontal=True,
    )
    direction = "kr_vi" if direction_label.startswith("Hàn") else "vi_kr"
    source = st.text_area(
        "Câu nguồn tiếng Hàn" if direction == "kr_vi" else "Câu nguồn tiếng Việt",
        height=100,
    )
    reference = st.text_area(
        "Bản dịch tham khảo (không bắt buộc; AI không coi đây là đáp án duy nhất)",
        height=100,
    )
    answer = st.text_area(
        "Bản dịch của bạn",
        height=120,
    )
    if direction == "kr_vi":
        pronunciation_player(source, "custom_source")
    else:
        pronunciation_player(answer, "custom_answer")
    if st.button("🧠 Chấm câu tự nhập", type="primary"):
        if not source.strip() or not answer.strip():
            st.warning("Cần nhập câu nguồn và bản dịch của bạn.")
        else:
            try:
                with st.spinner("AI đang phân tích..."):
                    result = evaluate_translation(
                        direction,
                        source.strip(),
                        answer.strip(),
                        reference.strip() or "(Không cung cấp bản dịch tham khảo)",
                        st.session_state.get("text_model", DEFAULT_TEXT_MODEL),
                    )
                render_evaluation(result, direction)
            except Exception as exc:
                st.error(f"Không thể chấm bài: {exc}")

st.divider()
st.caption(
    "Lưu ý: AI có thể mắc sai sót. Hãy xem điểm số như phản hồi học tập tham khảo; "
    "đối với bài thi thật, tiêu chí chấm chính thức của TOPIK có thể khác."
)
