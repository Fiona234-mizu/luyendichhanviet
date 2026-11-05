# -*- coding: utf-8 -*-
"""
Ứng dụng luyện dịch Hàn–Việt / Việt–Hàn TOPIK II miễn phí, không cần API trả phí.
"""
import os
import json
import re
from typing import Any, Dict

import streamlit as st

st.set_page_config(
    page_title="Luyện dịch TOPIK II miễn phí",
    page_icon="🇰🇷",
    layout="wide",
)

# ------------------------- Cấu hình -------------------------
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

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

st.title("🇰🇷 Luyện dịch TOPIK II – Miễn phí")
st.caption(
    "Luyện dịch hai chiều, giữ nguyên các đề đã có và liên tục bổ sung đề mới. "
    "Không cần OpenAI API Key hoặc dịch vụ AI trả phí."
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


# ------------------------- BỔ SUNG DỮ LIỆU CÁC ĐỀ TOPIK -------------------------
# Mỗi câu lưu theo cặp tiếng Hàn - tiếng Việt. Chiều Việt -> Hàn được tạo tự động
# từ cùng một cặp để bảo đảm nội dung hai chiều luôn khớp nhau.
def make_pairs(rows):
    return [{"id": i, "source": kr, "target": vi} for i, (kr, vi) in enumerate(rows, 1)]

EXAM_DATA = {
    "Đề 108 – Cạnh tranh lành mạnh": {
        "title": "Tầm quan trọng và tác động của cạnh tranh lành mạnh",
        "kr_vi": KR_TO_VI_LIST,
    },
    "Đề 105 – Kinh nghiệm": {
        "title": "Tầm quan trọng của kinh nghiệm và phương pháp tích lũy kinh nghiệm đúng đắn",
        "kr_vi": make_pairs([
            ("현대 사회에서는 과학 기술과 정보 통신의 발달로 사람들이 다양한 경험을 얻는 방식이 달라지고 있다.", "Trong xã hội hiện đại, do sự phát triển của khoa học kỹ thuật và công nghệ thông tin, phương thức con người tiếp nhận những trải nghiệm đa dạng đang dần thay đổi."),
            ("특히 직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 점점 많아지고 있다.", "Đặc biệt, ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm."),
            ("이처럼 간접 경험이 많아진 이유로는 먼저 인터넷과 디지털 매체의 발달을 들 수 있다.", "Trước tiên, có thể kể đến sự phát triển của Internet và các phương tiện truyền thông kỹ thuật số là nguyên nhân khiến trải nghiệm gián tiếp ngày càng gia tăng như vậy."),
            ("과거에는 새로운 지식이나 정보를 얻기 위해 직접 현장을 방문해야 했지만, 이제는 인터넷이나 동영상 등을 통해 다양한 정보를 쉽게 접할 수 있게 되었다.", "Trước đây, để có được kiến thức hoặc thông tin mới, người ta phải trực tiếp đến địa điểm thực tế, nhưng ngày nay đã có thể dễ dàng tiếp cận nhiều thông tin khác nhau thông qua Internet hoặc video."),
            ("또한 시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다.", "Ngoài ra, việc có thể tiết kiệm thời gian và chi phí cũng là một nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng."),
            ("그러나 직접 경험을 통해 얻을 수 있는 장점도 많다.", "Tuy nhiên, trải nghiệm trực tiếp cũng mang lại nhiều lợi ích có thể đạt được."),
            ("우선 어떤 일을 직접 해 보는 과정에서 책이나 영상만으로는 알기 어려운 실제적인 지식과 기술을 습득할 수 있다.", "Trước hết, trong quá trình trực tiếp thử làm một việc nào đó, chúng ta có thể tiếp thu những kiến thức và kỹ năng thực tế mà chỉ thông qua sách vở hoặc video thì khó có thể hiểu được."),
            ("또한 예상하지 못한 문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력과 자신감을 기를 수 있다.", "Ngoài ra, trong quá trình đối mặt với những vấn đề không lường trước được và giải quyết chúng, chúng ta có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin."),
            ("이러한 경험은 자신의 부족한 점을 발견하고 앞으로 발전하는 데에도 큰 도움이 된다.", "Những trải nghiệm này cũng giúp ích rất nhiều trong việc phát hiện những điểm còn thiếu sót của bản thân và phát triển hơn trong tương lai."),
            ("그렇다면 개인의 성장을 위해서는 어떻게 경험을 쌓아야 할까?", "Vậy để phát triển bản thân, chúng ta nên tích lũy kinh nghiệm như thế nào?"),
            ("먼저 실패를 두려워하지 말고 새로운 일에 적극적으로 도전하는 태도가 필요하다.", "Trước tiên, cần có thái độ tích cực thử thách bản thân với những điều mới mẻ mà không sợ thất bại."),
            ("또한 다양한 활동에 참여한 후 자신의 경험을 되돌아보고 잘한 점과 부족한 점을 분석해야 한다.", "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót."),
            ("이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다.", "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất."),
            ("이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다.", "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai."),
        ]),
    },
    "Đề 103 – Vệ sinh công cộng": {
        "title": "Tầm quan trọng và phương án cải thiện vệ sinh công cộng",
        "kr_vi": make_pairs([
            ("현대 사회에서 공공위생은 개인의 건강뿐만 아니라 사회 전체의 안전과 삶의 질에 영향을 미치는 중요한 요소이다.", "Trong xã hội hiện đại, vệ sinh công cộng là một yếu tố quan trọng, gây ảnh hưởng không chỉ đến sức khỏe cá nhân mà còn đến sự an toàn và chất lượng cuộc sống của toàn xã hội."),
            ("특히 많은 사람들이 함께 생활하는 공간일수록 공공위생 관리가 더욱 중요하다.", "Đặc biệt, ở những không gian có nhiều người cùng sinh sống thì việc quản lý vệ sinh công cộng càng trở nên quan trọng hơn."),
            ("먼저 공공위생이 중요한 이유는 감염병의 확산을 예방하고 쾌적한 생활환경을 유지할 수 있기 때문이다.", "Trước tiên, lý do vệ sinh công cộng quan trọng là vì có thể ngăn ngừa sự lây lan của các bệnh truyền nhiễm và duy trì môi trường sống dễ chịu, sạch sẽ."),
            ("공공장소가 깨끗하게 관리되면 세균이나 바이러스에 노출될 위험이 줄어들어 사람들이 보다 안전하게 생활할 수 있다.", "Nếu các địa điểm công cộng được quản lý sạch sẽ, nguy cơ tiếp xúc với vi khuẩn hoặc virus sẽ giảm xuống, nhờ đó mọi người có thể sinh hoạt an toàn hơn."),
            ("또한 깨끗한 환경은 시민들의 건강을 보호하고 생활 만족도를 높이는 데에도 도움이 된다.", "Ngoài ra, môi trường sạch sẽ cũng giúp bảo vệ sức khỏe của người dân và nâng cao mức độ hài lòng trong cuộc sống."),
            ("반면 공공위생 관리가 제대로 이루어지지 않으면 여러 가지 문제가 발생할 수 있다.", "Ngược lại, nếu việc quản lý vệ sinh công cộng không được thực hiện đúng cách thì nhiều vấn đề khác nhau có thể phát sinh."),
            ("우선 쓰레기와 오염 물질이 쌓이면 악취가 발생하고 해충이 번식하여 각종 질병을 유발할 수 있다.", "Trước hết, nếu rác thải và các chất ô nhiễm tích tụ, mùi hôi sẽ phát sinh và côn trùng gây hại sinh sôi, từ đó có thể gây ra nhiều loại bệnh khác nhau."),
            ("또한 감염병이 빠르게 확산될 위험이 커지며, 이는 개인의 건강을 넘어 사회 전체에 경제적 부담을 줄 수도 있다.", "Ngoài ra, nguy cơ các bệnh truyền nhiễm lây lan nhanh chóng sẽ tăng lên, điều này không chỉ ảnh hưởng đến sức khỏe cá nhân mà còn có thể gây ra gánh nặng kinh tế cho toàn xã hội."),
            ("나아가 도시의 이미지가 나빠지고 관광객이나 방문객이 줄어드는 결과로 이어질 수 있다.", "Hơn nữa, điều này có thể dẫn đến kết quả là hình ảnh của thành phố trở nên xấu đi và số lượng khách du lịch hoặc khách tham quan giảm xuống."),
            ("그렇다면 공공위생을 개선하기 위해서는 어떤 노력이 필요할까?", "Vậy cần có những nỗ lực nào để cải thiện vệ sinh công cộng?"),
            ("먼저 정부와 지방자치단체는 공공장소의 청소와 쓰레기 수거를 정기적으로 실시하고 위생 시설을 확충해야 한다.", "Trước tiên, chính phủ và chính quyền địa phương cần thường xuyên tiến hành vệ sinh các địa điểm công cộng, thu gom rác thải và mở rộng các cơ sở, trang thiết bị vệ sinh."),
            ("또한 시민들은 쓰레기를 함부로 버리지 않고 분리배출을 실천하는 등 일상생활에서 위생 수칙을 지켜야 한다.", "Ngoài ra, người dân cần tuân thủ các quy tắc vệ sinh trong cuộc sống hằng ngày, chẳng hạn như không vứt rác bừa bãi và thực hiện phân loại rác thải."),
            ("이와 함께 학교와 지역 사회에서는 위생 교육과 캠페인을 통해 시민들의 인식을 높일 필요가 있다.", "Cùng với đó, nhà trường và cộng đồng địa phương cần nâng cao nhận thức của người dân thông qua giáo dục vệ sinh và các chiến dịch tuyên truyền."),
            ("이처럼 정부의 체계적인 관리와 시민들의 자발적인 참여가 함께 이루어진다면 더욱 깨끗하고 건강한 사회를 만들 수 있을 것이다.", "Nếu việc quản lý có hệ thống của chính phủ và sự tham gia tự giác của người dân được thực hiện đồng thời như vậy thì chúng ta có thể xây dựng một xã hội sạch sẽ và lành mạnh hơn."),
        ]),
    },
    "Đề 83 – Năng lực sáng tạo": {
        "title": "Tầm quan trọng, thành quả và phương pháp rèn luyện năng lực sáng tạo",
        "kr_vi": make_pairs([
            ("변화와 발전을 끊임없이 요구하는 현대 사회에서 창의력은 꼭 필요하다.", "Trong xã hội hiện đại, nơi không ngừng đòi hỏi sự thay đổi và phát triển, năng lực sáng tạo là điều vô cùng cần thiết."),
            ("먼저 창의력은 새로운 관점을 가져온다.", "Trước tiên, năng lực sáng tạo mang đến những góc nhìn mới."),
            ("정보가 넘쳐나는 오늘날 새로운 관점이 있으면 차별화된 시각으로 정보를 통합하고 활용할 수 있다.", "Trong thời đại ngày nay, khi thông tin tràn ngập, nếu có góc nhìn mới, chúng ta có thể tổng hợp và sử dụng thông tin bằng một cách nhìn khác biệt."),
            ("또한 우리 사회는 새로운 시도 없이는 발전하기 어려운데 창의력은 기존 사고에 머무르지 않고 변화를 시도할 수 있게 돕는다.", "Ngoài ra, xã hội chúng ta khó có thể phát triển nếu không có những thử nghiệm mới. Trong khi đó, năng lực sáng tạo giúp chúng ta không bị bó hẹp trong lối tư duy cũ mà có thể thử nghiệm những thay đổi mới."),
            ("나아가 창의력은 기존의 사고만으로는 해결하기 어려운 문제를 해결하는 데에 중요한 역할을 한다.", "Hơn nữa, năng lực sáng tạo đóng vai trò quan trọng trong việc giải quyết những vấn đề khó có thể giải quyết chỉ bằng lối tư duy truyền thống."),
            ("이와 같이 창의력은 새로운 사고를 할 수 있게 하므로 창의력을 발휘했을 때 우리는 다양한 성과를 얻을 수 있다.", "Như vậy, vì năng lực sáng tạo giúp chúng ta có thể tư duy theo những cách mới nên khi phát huy năng lực sáng tạo, chúng ta có thể đạt được nhiều thành quả khác nhau."),
            ("창의력을 발휘하면 자신의 업무 분야에서 뛰어난 업무 성과를 보일 수 있다.", "Nếu phát huy năng lực sáng tạo, chúng ta có thể đạt được thành tích công việc xuất sắc trong lĩnh vực chuyên môn của mình."),
            ("또한 예술과 문화의 영역에서 음악이나 영화 등 새로운 콘텐츠를 만들어 냄으로써 사람들에게 신선한 감동을 줄 수도 있다.", "Ngoài ra, trong lĩnh vực nghệ thuật và văn hóa, thông qua việc tạo ra những nội dung mới như âm nhạc, phim ảnh, chúng ta cũng có thể mang đến cho mọi người những cảm xúc mới mẻ."),
            ("뿐만 아니라 획기적인 사고를 바탕으로 삶의 질을 높여 주는 새로운 상품이나 기술을 발명하여 사회에 기여할 수 있다.", "Không chỉ vậy, dựa trên tư duy mang tính đột phá, chúng ta có thể phát minh ra những sản phẩm hoặc công nghệ mới giúp nâng cao chất lượng cuộc sống, qua đó đóng góp cho xã hội."),
            ("창의력을 기르기 위해서는 먼저 독서 및 다양한 경험을 통해 사고의 폭을 넓혀야 한다.", "Để rèn luyện năng lực sáng tạo, trước tiên chúng ta cần mở rộng phạm vi tư duy thông qua việc đọc sách và tích lũy nhiều trải nghiệm khác nhau."),
            ("또한 눈에 보이는 현상에만 집중하는 것이 아니라 현상 뒤에 숨겨진 원인을 탐색하고 새로운 관점으로 문제에 접근하는 태도를 가져야 한다.", "Ngoài ra, chúng ta không nên chỉ tập trung vào những hiện tượng có thể nhìn thấy trước mắt mà cần tìm hiểu những nguyên nhân ẩn giấu phía sau hiện tượng đó và có thái độ tiếp cận vấn đề từ những góc nhìn mới."),
            ("마지막으로 기존의 정답에만 머무는 것이 아니라 비판적 사고를 바탕으로 새로운 해결 방안이 없는지를 모색하는 노력을 기울여야 한다.", "Cuối cùng, chúng ta không nên chỉ bó hẹp trong những đáp án có sẵn mà cần nỗ lực tìm kiếm xem liệu có phương án giải quyết mới nào hay không, dựa trên tư duy phản biện."),
        ]),
    },
}

for exam in EXAM_DATA.values():
    exam["vi_kr"] = [
        {"id": q["id"], "source": q["target"], "target": q["source"]}
        for q in exam["kr_vi"]
    ]

# Từ vựng học thuật được rút chọn từ chính các đề đang có trong ứng dụng.
EXTRA_VOCAB = [
    ("간접 경험", "TOPIK 4-5", "Trải nghiệm gián tiếp", "간접 경험을 통해 세상을 접하는 사람들이 많아지고 있다.", "Ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp.", "Đề 105"),
    ("직접 경험", "TOPIK 3-4", "Trải nghiệm trực tiếp", "직접 경험을 통해 실제적인 지식과 기술을 습득할 수 있다.", "Có thể tiếp thu kiến thức và kỹ năng thực tế thông qua trải nghiệm trực tiếp.", "Đề 105"),
    ("디지털 매체", "TOPIK 4-5", "Phương tiện truyền thông kỹ thuật số", "인터넷과 디지털 매체의 발달로 간접 경험이 많아졌다.", "Trải nghiệm gián tiếp gia tăng do sự phát triển của Internet và phương tiện truyền thông kỹ thuật số.", "Đề 105"),
    ("습득하다", "TOPIK 4-5", "Tiếp thu, lĩnh hội", "실제적인 지식과 기술을 습득할 수 있다.", "Có thể tiếp thu kiến thức và kỹ năng thực tế.", "Đề 105"),
    ("부딪히다", "TOPIK 4", "Va phải; đối mặt với (khó khăn/vấn đề)", "예상하지 못한 문제에 부딪히고 이를 해결한다.", "Đối mặt với những vấn đề không lường trước và giải quyết chúng.", "Đề 105"),
    ("문제 해결 능력", "TOPIK 4-5", "Năng lực giải quyết vấn đề", "문제 해결 능력과 자신감을 기를 수 있다.", "Có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin.", "Đề 105"),
    ("부족한 점", "TOPIK 3-4", "Điểm thiếu sót", "자신의 부족한 점을 발견해야 한다.", "Cần phát hiện những điểm còn thiếu sót của bản thân.", "Đề 105"),
    ("도전하다", "TOPIK 3-4", "Thử thách, dám thử sức", "실패를 두려워하지 말고 새로운 일에 도전해야 한다.", "Không nên sợ thất bại mà cần thử sức với những điều mới.", "Đề 105"),
    ("되돌아보다", "TOPIK 4-5", "Nhìn lại, xem xét lại", "자신의 경험을 되돌아보고 잘한 점을 분석해야 한다.", "Cần nhìn lại trải nghiệm và phân tích những điểm đã làm tốt.", "Đề 105"),
    ("실질적인 성장", "TOPIK 5", "Sự phát triển thực chất", "경험을 실질적인 성장으로 연결할 수 있다.", "Có thể chuyển hóa kinh nghiệm thành sự phát triển thực chất.", "Đề 105"),
    ("공공위생", "TOPIK 4-5", "Vệ sinh công cộng", "공공위생은 사회 전체의 안전에 영향을 미친다.", "Vệ sinh công cộng ảnh hưởng đến sự an toàn của toàn xã hội.", "Đề 103"),
    ("감염병", "TOPIK 4-5", "Bệnh truyền nhiễm", "감염병의 확산을 예방해야 한다.", "Cần ngăn ngừa sự lây lan của bệnh truyền nhiễm.", "Đề 103"),
    ("확산", "TOPIK 4-5", "Sự lan rộng, lây lan", "감염병이 빠르게 확산될 위험이 있다.", "Có nguy cơ bệnh truyền nhiễm lây lan nhanh chóng.", "Đề 103"),
    ("쾌적하다", "TOPIK 4", "Dễ chịu, thoải mái, trong lành", "쾌적한 생활환경을 유지해야 한다.", "Cần duy trì môi trường sống trong lành, dễ chịu.", "Đề 103"),
    ("노출되다", "TOPIK 4-5", "Bị phơi nhiễm, tiếp xúc với", "세균이나 바이러스에 노출될 위험이 줄어든다.", "Nguy cơ tiếp xúc với vi khuẩn hoặc virus giảm xuống.", "Đề 103"),
    ("해충", "TOPIK 4", "Côn trùng gây hại", "해충이 번식하여 질병을 유발할 수 있다.", "Côn trùng gây hại sinh sôi và có thể gây bệnh.", "Đề 103"),
    ("번식하다", "TOPIK 4-5", "Sinh sôi, sinh sản", "오염된 환경에서는 해충이 번식하기 쉽다.", "Trong môi trường ô nhiễm, côn trùng gây hại dễ sinh sôi.", "Đề 103"),
    ("유발하다", "TOPIK 5", "Gây ra, làm phát sinh", "각종 질병을 유발할 수 있다.", "Có thể gây ra nhiều loại bệnh.", "Đề 103"),
    ("경제적 부담", "TOPIK 5", "Gánh nặng kinh tế", "사회 전체에 경제적 부담을 줄 수 있다.", "Có thể tạo gánh nặng kinh tế cho toàn xã hội.", "Đề 103"),
    ("확충하다", "TOPIK 5", "Mở rộng, tăng cường (cơ sở/vật lực)", "위생 시설을 확충해야 한다.", "Cần mở rộng cơ sở vật chất vệ sinh.", "Đề 103"),
    ("분리배출", "TOPIK 4-5", "Phân loại và thải bỏ rác đúng quy định", "일상생활에서 분리배출을 실천해야 한다.", "Cần thực hiện phân loại rác trong sinh hoạt hằng ngày.", "Đề 103"),
    ("자발적인 참여", "TOPIK 5", "Sự tham gia tự giác", "시민들의 자발적인 참여가 필요하다.", "Cần có sự tham gia tự giác của người dân.", "Đề 103"),
    ("창의력", "TOPIK 4-5", "Năng lực sáng tạo", "현대 사회에서 창의력은 꼭 필요하다.", "Trong xã hội hiện đại, năng lực sáng tạo là điều cần thiết.", "Đề 83"),
    ("관점", "TOPIK 4-5", "Quan điểm, góc nhìn", "창의력은 새로운 관점을 가져온다.", "Năng lực sáng tạo mang đến góc nhìn mới.", "Đề 83"),
    ("차별화되다", "TOPIK 5", "Được tạo sự khác biệt", "차별화된 시각으로 정보를 활용할 수 있다.", "Có thể sử dụng thông tin bằng góc nhìn khác biệt.", "Đề 83"),
    ("통합하다", "TOPIK 4-5", "Tổng hợp, tích hợp", "정보를 통합하고 활용할 수 있다.", "Có thể tổng hợp và sử dụng thông tin.", "Đề 83"),
    ("발휘하다", "TOPIK 5", "Phát huy, thể hiện (năng lực)", "창의력을 발휘하면 다양한 성과를 얻을 수 있다.", "Nếu phát huy năng lực sáng tạo, có thể đạt nhiều thành quả.", "Đề 83"),
    ("성과", "TOPIK 4-5", "Thành quả, kết quả đạt được", "뛰어난 업무 성과를 보일 수 있다.", "Có thể thể hiện thành tích công việc xuất sắc.", "Đề 83"),
    ("획기적이다", "TOPIK 5-6", "Mang tính đột phá", "획기적인 사고를 바탕으로 새로운 기술을 발명한다.", "Dựa trên tư duy đột phá để phát minh công nghệ mới.", "Đề 83"),
    ("기여하다", "TOPIK 4-5", "Đóng góp", "새로운 기술을 발명하여 사회에 기여할 수 있다.", "Có thể phát minh công nghệ mới và đóng góp cho xã hội.", "Đề 83"),
    ("사고의 폭", "TOPIK 5", "Phạm vi/tầm rộng tư duy", "독서와 경험을 통해 사고의 폭을 넓혀야 한다.", "Cần mở rộng tư duy thông qua đọc sách và trải nghiệm.", "Đề 83"),
    ("탐색하다", "TOPIK 5", "Tìm tòi, khảo sát, truy tìm", "현상 뒤에 숨겨진 원인을 탐색해야 한다.", "Cần tìm hiểu nguyên nhân ẩn sau hiện tượng.", "Đề 83"),
    ("비판적 사고", "TOPIK 5", "Tư duy phản biện", "비판적 사고를 바탕으로 해결 방안을 모색해야 한다.", "Cần tìm kiếm phương án giải quyết dựa trên tư duy phản biện.", "Đề 83"),
    ("모색하다", "TOPIK 5", "Tìm kiếm, tìm tòi (phương án/giải pháp)", "새로운 해결 방안을 모색해야 한다.", "Cần tìm kiếm phương án giải quyết mới.", "Đề 83"),
]
for word, level, meaning, example, example_meaning, exam in EXTRA_VOCAB:
    TOPIK_VOCAB.append({"word": word, "level": level, "meaning": meaning,
                        "example": example, "example_meaning": example_meaning, "exam": exam})

EXTRA_GRAMMAR = [
    ("-기보다(는)", "Thay vì làm A, nhấn mạnh/lựa chọn B.", "직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 많아지고 있다.", "Ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm.", "Đề 105"),
    ("-을/를 통해(서)", "Thông qua, bằng cách; chỉ phương tiện hoặc con đường thực hiện.", "직접 경험을 통해 실제적인 지식과 기술을 습득할 수 있다.", "Có thể tiếp thu kiến thức và kỹ năng thực tế thông qua trải nghiệm trực tiếp.", "Đề 105"),
    ("-다는 점도 ... 원인이다", "Việc ... cũng là một nguyên nhân; dùng để bổ sung nguyên nhân.", "시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다.", "Việc có thể tiết kiệm thời gian và chi phí cũng là nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng.", "Đề 105"),
    ("-는 과정에서", "Trong quá trình làm gì; nhấn mạnh quá trình phát sinh kết quả.", "문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력을 기를 수 있다.", "Có thể rèn luyện năng lực giải quyết vấn đề trong quá trình đối mặt và giải quyết vấn đề.", "Đề 105"),
    ("-는 데(에) 도움이 되다", "Có ích cho việc..., giúp ích trong việc...", "자신의 부족한 점을 발견하는 데에도 큰 도움이 된다.", "Cũng rất có ích trong việc phát hiện những điểm thiếu sót của bản thân.", "Đề 105"),
    ("-지 말고", "Đừng ... mà hãy ...; khuyên hoặc yêu cầu chuyển sang hành động khác.", "실패를 두려워하지 말고 새로운 일에 도전해야 한다.", "Không nên sợ thất bại mà cần thử thách bản thân với điều mới.", "Đề 105"),
    ("-을/를 ...으로 연결하다", "Kết nối/chuyển hóa A thành B.", "경험을 실제적인 성장으로 연결할 수 있다.", "Có thể chuyển hóa kinh nghiệm thành sự phát triển thực chất.", "Đề 105"),
    ("-뿐만 아니라", "Không chỉ ... mà còn ...; nối hai đối tượng hoặc nội dung cùng được nhấn mạnh.", "공공위생은 개인의 건강뿐만 아니라 사회 전체의 안전에도 영향을 미친다.", "Vệ sinh công cộng ảnh hưởng không chỉ đến sức khỏe cá nhân mà còn đến sự an toàn của toàn xã hội.", "Đề 103"),
    ("-을수록", "Càng ... thì càng ...; biểu thị mức độ tăng tiến.", "많은 사람들이 함께 생활하는 공간일수록 공공위생 관리가 중요하다.", "Không gian càng có nhiều người cùng sinh sống thì việc quản lý vệ sinh công cộng càng quan trọng.", "Đề 103"),
    ("-면(으)로 인해 / -면", "Nếu ... thì ...; dùng để nêu điều kiện và kết quả.", "공공장소가 깨끗하게 관리되면 감염 위험이 줄어든다.", "Nếu địa điểm công cộng được quản lý sạch sẽ thì nguy cơ lây nhiễm giảm xuống.", "Đề 103"),
    ("-을/를 넘어", "Vượt ra ngoài, không chỉ dừng ở phạm vi ...", "이는 개인의 건강을 넘어 사회 전체에 경제적 부담을 줄 수 있다.", "Điều này có thể tạo gánh nặng kinh tế cho toàn xã hội, vượt ra ngoài phạm vi sức khỏe cá nhân.", "Đề 103"),
    ("-는 결과로 이어지다", "Dẫn đến kết quả là ...; diễn đạt hệ quả.", "관광객이나 방문객이 줄어드는 결과로 이어질 수 있다.", "Có thể dẫn đến kết quả là số lượng khách du lịch hoặc khách tham quan giảm xuống.", "Đề 103"),
    ("-을/를 통해 인식을 높이다", "Nâng cao nhận thức thông qua ...; cụm diễn đạt học thuật.", "위생 교육과 캠페인을 통해 시민들의 인식을 높일 필요가 있다.", "Cần nâng cao nhận thức người dân thông qua giáo dục vệ sinh và chiến dịch tuyên truyền.", "Đề 103"),
    ("-와/과 함께 이루어지다", "Được thực hiện đồng thời/cùng với ...", "정부의 체계적인 관리와 시민들의 참여가 함께 이루어져야 한다.", "Việc quản lý có hệ thống của chính phủ và sự tham gia của người dân cần được thực hiện đồng thời.", "Đề 103"),
    ("-지 않고", "Không làm A mà ...; nối hành động phủ định với hành động tiếp theo.", "기존 사고에 머무르지 않고 변화를 시도해야 한다.", "Không nên dừng lại ở tư duy cũ mà cần thử nghiệm sự thay đổi.", "Đề 83"),
    ("-게 하다", "Khiến/giúp cho ai hoặc điều gì trở nên/thực hiện ...", "창의력은 새로운 사고를 할 수 있게 한다.", "Năng lực sáng tạo giúp chúng ta có thể tư duy theo cách mới.", "Đề 83"),
    ("-(으)므로", "Bởi vì/do ... nên ...; liên kết nguyên nhân với kết quả trong văn viết.", "창의력은 새로운 사고를 가능하게 하므로 다양한 성과를 얻을 수 있다.", "Vì năng lực sáng tạo giúp tư duy mới trở nên khả thi nên có thể đạt nhiều thành quả.", "Đề 83"),
    ("-아/어 냄으로써", "Bằng việc hoàn thành/tạo ra ...; nêu phương thức và kết quả.", "새로운 콘텐츠를 만들어 냄으로써 사람들에게 감동을 줄 수 있다.", "Bằng việc tạo ra nội dung mới, chúng ta có thể mang đến cảm xúc cho mọi người.", "Đề 83"),
    ("-을/를 바탕으로", "Dựa trên, lấy ... làm nền tảng.", "획기적인 사고를 바탕으로 새로운 기술을 발명할 수 있다.", "Có thể phát minh công nghệ mới dựa trên tư duy đột phá.", "Đề 83"),
    ("-는 것이 아니라", "Không phải là ... mà là ...; phủ định cách hiểu/hành động trước và chuyển sang nội dung đúng.", "눈에 보이는 현상에만 집중하는 것이 아니라 숨겨진 원인을 탐색해야 한다.", "Không chỉ tập trung vào hiện tượng nhìn thấy mà cần tìm hiểu nguyên nhân ẩn giấu.", "Đề 83"),
    ("-는 데 중요한 역할을 하다", "Đóng vai trò quan trọng trong việc ...", "창의력은 문제를 해결하는 데 중요한 역할을 한다.", "Năng lực sáng tạo đóng vai trò quan trọng trong việc giải quyết vấn đề.", "Đề 83"),
]
for grammar, usage, example, example_meaning, exam in EXTRA_GRAMMAR:
    TOPIK_54_GRAMMAR.append({"grammar": grammar, "usage": usage, "example": example,
                             "example_meaning": example_meaning, "exam": exam})



# ------------------------- Chấm đối chiếu miễn phí, chạy ngoại tuyến -------------------------
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

def _tokens_for_matching(text: str, direction: str) -> list[str]:
    """Tách đơn vị từ đơn giản để đối chiếu tham khảo, không hiểu ngữ nghĩa như AI."""
    tokens = re.findall(r"[가-힣]+|[a-zA-ZÀ-ỹ]+", text.lower())
    if direction == "kr_vi":
        stop = {"và", "là", "của", "cho", "trong", "được", "có", "thể", "những", "các", "một", "để", "với", "đó", "này", "thì", "sẽ", "đã", "rằng", "khi", "từ", "ra", "đến", "không", "như", "hơn", "cũng", "vì", "do", "nên", "về", "bởi", "mà"}
    else:
        stop = {"은", "는", "이", "가", "을", "를", "에", "에서", "으로", "로", "와", "과", "도", "만", "의", "하다", "수", "있다", "없다"}
    return [t for t in tokens if t not in stop and len(t) > 1]


def evaluate_translation(direction: str, source: str, user_translation: str,
                          reference: str, model: str = "") -> Dict[str, Any]:
    """Chấm đối chiếu ngoại tuyến. Điểm chỉ phản ánh độ trùng khớp từ/cụm."""
    weights = KR_TO_VI_WEIGHTS if direction == "kr_vi" else VI_TO_KR_WEIGHTS
    ref_tokens = _tokens_for_matching(reference, direction)
    user_tokens = _tokens_for_matching(user_translation, direction)
    ref_set, user_set = set(ref_tokens), set(user_tokens)
    overlap = ref_set & user_set
    precision = len(overlap) / max(len(user_set), 1)
    recall = len(overlap) / max(len(ref_set), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    # Tính cả độ dài để cảnh báo bài quá ngắn/dài, nhưng không phạt máy móc nặng.
    length_ratio = min(len(user_tokens), len(ref_tokens)) / max(len(user_tokens), len(ref_tokens), 1)
    score = round(100 * (0.75 * f1 + 0.25 * length_ratio))
    score = max(0, min(100, score))

    if score >= 85:
        comment = "Bản dịch có mức độ trùng khớp từ khóa cao với bản tham khảo. Hãy kiểm tra thêm sắc thái và độ tự nhiên."
        status = "Khớp nhiều từ khóa"
    elif score >= 60:
        comment = "Bản dịch đã có một số ý/từ khóa chính, nhưng có thể còn thiếu hoặc dùng cách diễn đạt khác bản tham khảo."
        status = "Khớp một phần"
    else:
        comment = "Mức độ trùng khớp từ khóa còn thấp. Hãy đối chiếu lại nội dung và các ý chính; điểm thấp không đồng nghĩa chắc chắn dịch sai."
        status = "Cần đối chiếu lại"

    criteria = {}
    for key, weight in weights.items():
        criteria[key] = {
            "score": score,
            "max_score": 100,
            "comment": "Điểm đối chiếu tự động dựa trên từ khóa và độ dài; không phải đánh giá ngữ nghĩa của AI."
        }
    missing = sorted(ref_set - user_set)
    matched = sorted(overlap)
    if direction == "kr_vi":
        missing_text = ", ".join(missing[:12]) if missing else "Không phát hiện từ khóa tham khảo bị thiếu."
        matched_text = ", ".join(matched[:12]) if matched else "Chưa tìm thấy từ khóa trùng rõ ràng."
    else:
        missing_text = ", ".join(missing[:12]) if missing else "Không phát hiện từ khóa tham khảo bị thiếu."
        matched_text = ", ".join(matched[:12]) if matched else "Chưa tìm thấy từ khóa trùng rõ ràng."

    return {
        "overall_comment": f"{comment} Đây là công cụ đối chiếu ngoại tuyến, không thể xác nhận mọi cách diễn đạt đồng nghĩa.",
        "semantic_accuracy_percent": score,
        "weighted_score_10": round(score / 10, 1),
        "weighted_score_percent": score,
        "criteria": criteria,
        "segments": [{
            "source_chunk": source,
            "user_chunk": user_translation,
            "status": status,
            "explanation": f"Từ khóa trùng với bản tham khảo: {matched_text}",
            "suggestion": f"Từ khóa có trong bản tham khảo nhưng chưa thấy trong bài làm: {missing_text}",
            "accepted_alternatives": []
        }],
        "correct_points": [f"Đã sử dụng được các từ khóa trùng khớp: {matched_text}"],
        "errors": [],
        "revised_translation": reference,
        "other_valid_translations": [],
        "vocabulary_notes": [],
        "grammar_notes": [],
        "confidence_note": "Chấm tự động miễn phí bằng đối chiếu từ khóa/độ dài. Không đánh giá được đầy đủ ngữ nghĩa, từ đồng nghĩa, sắc thái hoặc ngữ pháp; hãy dùng bản dịch tham khảo để tự kiểm tra."
    }

def render_evaluation(result: Dict[str, Any], direction: str) -> None:
    st.divider()
    st.subheader("📊 Kết quả chấm")
    c1, c2, c3 = st.columns(3)
    c1.metric("Điểm tổng", f"{result['weighted_score_10']}/10")
    c2.metric("Chất lượng tổng hợp", f"{result['weighted_score_percent']}%")
    c3.metric("Tương đương ngữ nghĩa", f"{result['semantic_accuracy_percent']}%")
    st.caption(
        "Điểm được tính tự động bằng cách đối chiếu từ khóa và độ dài với bản tham khảo; "
        "không phải điểm ngữ nghĩa do AI đánh giá hay điểm chính thức của TOPIK."
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
        st.write("Chưa có nhận xét bổ sung.")

    st.markdown("### 4. Lỗi cần sửa")
    errors = result.get("errors", [])
    if errors:
        for item in errors:
            st.error(item)
    else:
        st.info("Công cụ miễn phí không tự kết luận lỗi ngữ nghĩa; hãy tự đối chiếu bản dịch tham khảo.")

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

# ------------------------- Phát âm tiếng Hàn miễn phí -------------------------
def play_korean_audio(text: str, key: str, button_label: str = "🔊 Nghe phát âm") -> None:
    'Dùng giọng đọc tiếng Hàn có sẵn trên trình duyệt/thiết bị, không gọi API. '
    if not text or not text.strip():
        return
    if not any("\uac00" <= ch <= "\ud7a3" for ch in text):
        st.caption("Nội dung này không có ký tự tiếng Hàn để phát âm.")
        return
    import streamlit.components.v1 as components
    safe_text = json.dumps(text, ensure_ascii=False)
    html = f'''<div style="font-family: sans-serif;">
    <button id="speak_{key}" style="padding:7px 12px;border:1px solid #888;border-radius:8px;background:#fff;cursor:pointer;">{button_label}</button>
    <span id="msg_{key}" style="font-size:12px;color:#666;margin-left:8px;"></span>
    </div>
    <script>
    const btn = document.getElementById("speak_{key}");
    btn.onclick = () => {{
      if (!window.speechSynthesis) {{ document.getElementById("msg_{key}").textContent = "Thiết bị/trình duyệt không hỗ trợ đọc văn bản."; return; }}
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance({safe_text});
      utter.lang = "ko-KR"; utter.rate = 0.85;
      const voices = window.speechSynthesis.getVoices();
      const korean = voices.find(v => v.lang && v.lang.toLowerCase().startsWith("ko"));
      if (korean) utter.voice = korean;
      window.speechSynthesis.speak(utter);
    }};
    </script>'''
    components.html(html, height=42)


def render_korean_pronunciation_lab(text: str, key: str) -> None:
    if not text or not any("\uac00" <= ch <= "\ud7a3" for ch in text):
        return
    st.markdown("#### 🎧 Luyện phát âm tiếng Hàn")
    st.caption("Sử dụng chức năng đọc tiếng Hàn có sẵn trên trình duyệt hoặc điện thoại. Giọng đọc tùy thuộc thiết bị.")
    play_korean_audio(text, key, "🔊 Nghe câu tiếng Hàn")


def pronunciation_player(text: str, key: str = "audio") -> None:
    render_korean_pronunciation_lab(text, key)


# ------------------------- Thanh bên -------------------------
with st.sidebar:
    st.header("⚙️ Cài đặt")
    st.success("Chế độ miễn phí: không cần API Key, không phát sinh phí OpenAI.")
    st.caption("Chấm bài bằng đối chiếu từ khóa và độ dài. Phát âm dùng giọng đọc sẵn có trên thiết bị.")

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
    title = MENU_K2V if is_k2v else MENU_V2K
    st.subheader(title)
    exam_name = st.selectbox(
        "📑 Chọn đề TOPIK",
        options=list(EXAM_DATA.keys()),
        key=f"selected_exam_{direction}",
        format_func=lambda name: f"{name} | {EXAM_DATA[name]['title']}",
    )
    exam = EXAM_DATA[exam_name]
    data = exam["kr_vi"] if is_k2v else exam["vi_kr"]
    exam_slug = str(list(EXAM_DATA.keys()).index(exam_name))
    index_key = f"question_index_{direction}_{exam_slug}"
    if index_key not in st.session_state:
        st.session_state[index_key] = 0
    idx = st.session_state[index_key]

    if idx >= len(data):
        st.success(f"Bạn đã hoàn thành {exam_name} – {exam['title']}!")
        if st.button("🔄 Làm lại từ câu 1", key=f"restart_{direction}_{exam_slug}"):
            st.session_state[index_key] = 0
            st.rerun()
        return

    q = data[idx]
    st.caption(f"{exam['title']} · {len(data)} câu · Câu {idx + 1}/{len(data)}")
    source_label = "Câu gốc tiếng Hàn" if is_k2v else "Câu gốc tiếng Việt"
    st.info(f"**{source_label}:**\n\n{q['source']}")
    if is_k2v:
        pronunciation_player(q["source"], f"source_{direction}_{exam_slug}_{idx}")
        input_label = "Nhập bản dịch tiếng Việt của bạn"
    else:
        input_label = "Nhập bản dịch tiếng Hàn của bạn"
    answer = st.text_area(input_label, key=f"answer_{direction}_{exam_slug}_{idx}", height=110)

    if not is_k2v and answer.strip():
        pronunciation_player(answer, f"answer_{direction}_{exam_slug}_{idx}")

    result_key = f"result_{direction}_{exam_slug}_{idx}"
    if st.button("📊 Đối chiếu bản dịch miễn phí", type="primary", key=f"grade_{direction}_{exam_slug}_{idx}"):
        if not answer.strip():
            st.warning("Bạn hãy nhập bản dịch trước khi chấm.")
        else:
            try:
                with st.spinner("Đang đối chiếu từ khóa với bản tham khảo..."):
                    result = evaluate_translation(
                        direction, q["source"], answer.strip(), q["target"],
                        "offline",
                    )
                st.session_state[result_key] = result
            except Exception as exc:
                st.error(f"Không thể chấm bài: {exc}")
    stored = st.session_state.get(result_key)
    if stored:
        render_evaluation(stored, direction)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ Câu tiếp theo", key=f"next_{direction}_{exam_slug}_{idx}"):
            st.session_state[index_key] += 1
            st.rerun()
    with col2:
        if st.button("🔄 Làm lại đề này", key=f"reset_{direction}_{exam_slug}_{idx}"):
            st.session_state[index_key] = 0
            st.rerun()

if menu == MENU_K2V:
    show_quiz("kr_vi")

elif menu == MENU_V2K:
    show_quiz("vi_kr")

elif menu == MENU_VOCAB:
    st.subheader("📚 Từ vựng TOPIK – nghe và luyện phát âm")
    st.caption("Mỗi mục có nghĩa tiếng Việt, ví dụ và nút nghe phát âm bằng giọng đọc sẵn có trên thiết bị.")
    vocab_exam_options = ["Tất cả các đề"] + sorted({item.get("exam", "Đề 108") for item in TOPIK_VOCAB})
    vocab_exam = st.selectbox("Lọc theo đề", vocab_exam_options, key="vocab_exam_filter")
    vocab_level = st.multiselect("Lọc theo cấp độ", ["TOPIK 3", "TOPIK 4", "TOPIK 5", "TOPIK 6"], default=["TOPIK 3", "TOPIK 4", "TOPIK 5", "TOPIK 6"], key="vocab_level_filter")
    selected_level_numbers = {level[-1] for level in vocab_level}
    filtered_vocab = [item for item in TOPIK_VOCAB
                      if (vocab_exam == "Tất cả các đề" or item.get("exam", "Đề 108") == vocab_exam)
                      and bool(selected_level_numbers.intersection(re.findall(r"\d", item["level"])))]
    st.caption(f"Hiển thị {len(filtered_vocab)} mục từ.")
    for i, item in enumerate(filtered_vocab):
        with st.expander(f"{item['word']} ({item['level']}) – {item['meaning']}"):
            st.markdown(f"### {item['word']}")
            st.write(item["meaning"])
            if item.get("exam"):
                st.caption(item["exam"])
            pronunciation_player(item["word"], f"vocab_word_{i}")
            st.markdown(f"**Ví dụ:** {item['example']}")
            st.write(item["example_meaning"])
            pronunciation_player(item["example"], f"vocab_example_{i}")

elif menu == MENU_GRAMMAR:
    st.subheader("✍️ Biểu hiện và ngữ pháp TOPIK II câu 54")
    grammar_exam_options = ["Tất cả các đề"] + sorted({item.get("exam", "Đề 108") for item in TOPIK_54_GRAMMAR})
    grammar_exam = st.selectbox("Lọc biểu hiện/ngữ pháp theo đề", grammar_exam_options, key="grammar_exam_filter")
    filtered_grammar = [item for item in TOPIK_54_GRAMMAR
                        if grammar_exam == "Tất cả các đề" or item.get("exam", "Đề 108") == grammar_exam]
    st.caption(f"Hiển thị {len(filtered_grammar)} cấu trúc/biểu hiện.")
    for i, item in enumerate(filtered_grammar):
        with st.expander(item["grammar"]):
            st.write(item["usage"])
            if item.get("exam"):
                st.caption(item["exam"])
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
        "Bản dịch tham khảo (không bắt buộc)",
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
    if st.button("📊 Đối chiếu câu tự nhập", type="primary"):
        if not source.strip() or not answer.strip():
            st.warning("Cần nhập câu nguồn và bản dịch của bạn.")
        else:
            try:
                with st.spinner("Đang đối chiếu từ khóa..."):
                    result = evaluate_translation(
                        direction,
                        source.strip(),
                        answer.strip(),
                        reference.strip() or "(Không cung cấp bản dịch tham khảo)",
                        "offline",
                    )
                render_evaluation(result, direction)
            except Exception as exc:
                st.error(f"Không thể chấm bài: {exc}")

st.divider()
st.caption(
    "Ứng dụng không sử dụng API trả phí. Điểm đối chiếu từ khóa chỉ mang tính tham khảo; "
    "các cách dịch đồng nghĩa có thể không được nhận diện tự động. Hãy kiểm tra bản dịch theo ngữ cảnh."
)
