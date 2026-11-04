import streamlit as st
import re
import difflib
import html
import json

st.set_page_config(page_title="Luyện dịch TOPIK II – miễn phí", page_icon="🇰🇷", layout="wide")

# ==========================================
# DỮ LIỆU CÁC ĐỀ THI (104, 105, 106, 107, 108)
# ==========================================

TOPICS_DATA = {
    "Đề 108: Luyện dịch tổng hợp": {
        "kr_vi": [
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
        ],
        "vi_kr": [
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
    },
    "Đề 107: Kinh nghiệm & Tích lũy kinh nghiệm": {
        "kr_vi": [
            {"id": 1, "source": "현대 사회에서는 과학 기술과 정보 통신의 발달로 사람들이 다양한 경험을 얻는 방식이 달라지고 있다.", "target": "Trong xã hội hiện đại, do sự phát triển của khoa học kỹ thuật và công nghệ thông tin, phương thức con người tiếp nhận những trải nghiệm đa dạng đang dần thay đổi."},
            {"id": 2, "source": "특히 직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 점점 많아지고 있다.", "target": "Đặc biệt, ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm."},
            {"id": 3, "source": "이처럼 간접 경험이 많아진 이유로는 먼저 인터넷과 디지털 매체의 발달을 들 수 있다.", "target": "Trước tiên, có thể kể đến sự phát triển của Internet và các phương tiện truyền thông kỹ thuật số là nguyên nhân khiến trải nghiệm gián tiếp ngày càng gia tăng như vậy."},
            {"id": 4, "source": "과거에는 새로운 지식이나 정보를 얻기 위해 직접 현장을 방문해야 했지만, 이제는 인터넷이나 동영상 등을 통해 다양한 정보를 쉽게 접할 수 있게 되었다.", "target": "Trước đây, để có được kiến thức hoặc thông tin mới, người ta phải trực tiếp đến địa điểm thực tế, nhưng ngày nay đã có thể dễ dàng tiếp cận nhiều thông tin khác nhau thông qua Internet hoặc video."},
            {"id": 5, "source": "또한 시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다.", "target": "Ngoài ra, việc có thể tiết kiệm thời gian và chi phí cũng là một nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng."},
            {"id": 6, "source": "그러나 직접 경험을 통해 얻을 수 있는 장점도 많다.", "target": "Tuy nhiên, trải nghiệm trực tiếp cũng mang lại nhiều lợi ích có thể đạt được."},
            {"id": 7, "source": "우선 어떤 일을 직접 해 보는 과정에서 책이나 영상만으로는 알기 어려운 실제적인 지식과 기술을 습득할 수 있다.", "target": "Trước hết, trong quá trình trực tiếp thử làm một việc nào đó, chúng ta có thể tiếp thu những kiến thức và kỹ năng thực tế mà chỉ thông qua sách vở hoặc video thì khó có thể hiểu được."},
            {"id": 8, "source": "또한 예상하지 못한 문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력과 자신감을 기를 수 있다.", "target": "Ngoài ra, trong quá trình đối mặt với những vấn đề không lường trước được và giải quyết chúng, chúng ta có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin."},
            {"id": 9, "source": "이러한 경험은 자신의 부족한 점을 발견하고 앞으로 발전하는 데에도 큰 도움이 된다.", "target": "Những trải nghiệm này cũng giúp ích rất nhiều trong việc phát hiện những điểm còn thiếu sót của bản thân và phát triển hơn trong tương lai."},
            {"id": 10, "source": "그렇다면 개인의 성장을 위해서는 어떻게 경험을 쌓아야 할까?", "target": "Vậy để phát triển bản thân, chúng ta nên tích lũy kinh nghiệm như thế nào?"},
            {"id": 11, "source": "먼저 실패를 두려워하지 말고 새로운 일에 적극적으로 도전하는 태도가 필요하다.", "target": "Trước tiên, cần có thái độ tích cực thử thách bản thân với những điều mới mẻ mà không sợ thất bại."},
            {"id": 12, "source": "또한 다양한 활동에 참여한 후 자신의 경험을 되돌아보고 잘한 점과 부족한 점을 분석해야 한다.", "target": "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót."},
            {"id": 13, "source": "이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다.", "target": "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất."},
            {"id": 14, "source": "이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다.", "target": "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai."}
        ],
        "vi_kr": [
            {"id": 1, "source": "Trong xã hội hiện đại, do sự phát triển của khoa học kỹ thuật và công nghệ thông tin, phương thức con người tiếp nhận những trải nghiệm đa dạng đang dần thay đổi.", "target": "현대 사회에서는 과학 기술과 정보 통신의 발달로 사람들이 다양한 경험을 얻는 방식이 달라지고 있다."},
            {"id": 2, "source": "Đặc biệt, ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm.", "target": "특히 직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 점점 많아지고 있다."},
            {"id": 3, "source": "Trước tiên, có thể kể đến sự phát triển của Internet và các phương tiện truyền thông kỹ thuật số là nguyên nhân khiến trải nghiệm gián tiếp ngày càng gia tăng như vậy.", "target": "이처럼 간접 경험이 많아진 이유로는 먼저 인터넷과 디지털 매체의 발달을 들 수 있다."},
            {"id": 4, "source": "Trước đây, để có được kiến thức hoặc thông tin mới, người ta phải trực tiếp đến địa điểm thực tế, nhưng ngày nay đã có thể dễ dàng tiếp cận nhiều thông tin khác nhau thông qua Internet hoặc video.", "target": "과거에는 새로운 지식이나 정보를 얻기 위해 직접 현장을 방문해야 했지만, 이제는 인터넷이나 동영상 등을 통해 다양한 정보를 쉽게 접할 수 있게 되었다."},
            {"id": 5, "source": "Ngoài ra, việc có thể tiết kiệm thời gian và chi phí cũng là một nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng.", "target": "또한 시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다."},
            {"id": 6, "source": "Tuy nhiên, trải nghiệm trực tiếp cũng mang lại nhiều lợi ích có thể đạt được.", "target": "그러나 직접 경험을 통해 얻을 수 있는 장점도 많다."},
            {"id": 7, "source": "Trước hết, trong quá trình trực tiếp thử làm một việc nào đó, chúng ta có thể tiếp thu những kiến thức và kỹ năng thực tế mà chỉ thông qua sách vở hoặc video thì khó có thể hiểu được.", "target": "우선 어떤 일을 직접 해 보는 과정에서 책이나 영상만으로는 알기 어려운 실제적인 지식과 기술을 습득할 수 있다."},
            {"id": 8, "source": "Ngoài ra, trong quá trình đối mặt với những vấn đề không lường trước được và giải quyết chúng, chúng ta có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin.", "target": "또한 예상하지 못한 문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력과 자신감을 기를 수 있다."},
            {"id": 9, "source": "Những trải nghiệm này cũng giúp ích rất nhiều trong việc phát hiện những điểm còn thiếu sót của bản thân và phát triển hơn trong tương lai.", "target": "이러한 경험은 자신의 부족한 점을 발견하고 앞으로 발전하는 데에도 큰 도움이 된다."},
            {"id": 10, "source": "Vậy để phát triển bản thân, chúng ta nên tích lũy kinh nghiệm như thế nào?", "target": "그렇다면 개인의 성장을 위해서는 어떻게 경험을 쌓아야 할까?"},
            {"id": 11, "source": "Trước tiên, cần có thái độ tích cực thử thách bản thân với những điều mới mẻ mà không sợ thất bại.", "target": "먼저 실패를 두려워하지 말고 새로운 일에 적극적으로 도전하는 태도가 필요하다."},
            {"id": 12, "source": "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót.", "target": "또한 다양한 활동에 참여한 후 자신의 경험을 되돌아보고 잘한 점과 부족한 점을 분석해야 한다."},
            {"id": 13, "source": "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất.", "target": "이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다."},
            {"id": 14, "source": "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai.", "target": "이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다."}
        ]
    },
    "Đề 106: Truyền thông đại chúng & Thanh thiếu niên": {
        "kr_vi": [
            {"id": 1, "source": "현대 사회에서 대중 매체는 청소년들의 일상생활에서 중요한 역할을 하고 있다.", "target": "Trong xã hội hiện đại, truyền thông đại chúng đang đóng vai trò quan trọng trong cuộc sống hằng ngày của thanh thiếu niên."},
            {"id": 2, "source": "청소년들은 텔레비전이나 인터넷, SNS 등 다양한 매체를 통해 많은 정보를 얻고 있다.", "target": "Thanh thiếu niên đang tiếp nhận nhiều thông tin thông qua các phương tiện truyền thông đa dạng như truyền hình, Internet và mạng xã hội."},
            {"id": 3, "source": "먼저 대중 매체를 통해 청소년들은 사회에서 일어나는 다양한 사건과 새로운 지식을 쉽게 접할 수 있다.", "target": "Trước tiên, thông qua truyền thông đại chúng, thanh thiếu niên có thể dễ dàng tiếp cận những sự kiện đa dạng xảy ra trong xã hội và những kiến thức mới."},
            {"id": 4, "source": "이를 통해 세상에 대한 이해의 폭을 넓히고 자신의 관심 분야에 대한 지식과 정보를 얻을 수 있다.", "target": "Thông qua đó, các em có thể mở rộng phạm vi hiểu biết về thế giới và tiếp thu kiến thức, thông tin về lĩnh vực mà bản thân quan tâm."},
            {"id": 5, "source": "또한 다양한 사람들의 생각과 문화를 접하면서 다른 사람의 입장을 이해하고 세상을 바라보는 시각을 넓힐 수 있다.", "target": "Ngoài ra, thông qua việc tiếp xúc với suy nghĩ và văn hóa của nhiều người khác nhau, các em có thể hiểu được lập trường của người khác và mở rộng góc nhìn về thế giới."},
            {"id": 6, "source": "그러나 대중 매체는 청소년들의 가치관에 부정적인 영향을 미치기도 한다.", "target": "Tuy nhiên, truyền thông đại chúng đôi khi cũng gây ra những ảnh hưởng tiêu cực đến hệ giá trị quan của thanh thiếu niên."},
            {"id": 7, "source": "우선 자극적이고 폭력적인 콘텐츠에 반복적으로 노출되면 폭력적인 행동을 가볍게 여겨나 잘못된 행동을 모방할 가능성이 높아진다.", "target": "Trước hết, nếu thường xuyên tiếp xúc với những nội dung kích động và bạo lực, các em sẽ có khả năng xem nhẹ hành vi bạo lực hoặc bắt chước những hành vi sai trái cao hơn."},
            {"id": 8, "source": "또한 SNS에 올라오는 화려한 생활이나 외모를 자주 접하게 되면 다른 사람과 자신을 비교하면서 외모나 물질적인 성공만을 중요하게 생각할 수 있다.", "target": "Ngoài ra, nếu thường xuyên tiếp xúc với những hình ảnh về cuộc sống xa hoa hoặc ngoại hình trên mạng xã hội, các em có thể so sánh bản thân với người khác và chỉ coi trọng ngoại hình hoặc thành công về mặt vật chất."},
            {"id": 9, "source": "이는 자존감을 낮추고 올바른 가치관을 형성하는 데 방해가 될 수 있다.", "target": "Điều này có thể làm giảm lòng tự trọng và cản trở việc hình thành hệ giá trị quan đúng đắn."},
            {"id": 10, "source": "그렇다면 청소년들은 대중 매체를 대할 때 어떤 태도를 가져야 할까?", "target": "Vậy thanh thiếu niên cần có thái độ như thế nào khi tiếp xúc với truyền thông đại chúng?"},
            {"id": 11, "source": "먼저 매체에서 제공하는 정보를 무조건 믿기보다는 사실인지 확인하고 비판적으로 판단하는 습관을 길러야 한다.", "target": "Trước tiên, thay vì tin tưởng một cách vô điều kiện vào thông tin do truyền thông cung cấp, các em cần rèn luyện thói quen kiểm chứng xem thông tin đó có đúng sự thật hay không và đánh giá một cách có tư duy phản biện."},
            {"id": 12, "source": "또한 자신에게 필요한 콘텐츠를 선택하고 이용 시간을 적절히 조절해야 한다.", "target": "Ngoài ra, các em cần lựa chọn những nội dung cần thiết cho bản thân và điều chỉnh thời gian sử dụng một cách hợp lý."},
            {"id": 13, "source": "이를 위해 학교에서는 미디어 교육을 강화하고 올바른 정보 이용 방법을 가르칠 필요가 있다.", "target": "Để làm được điều này, nhà trường cần tăng cường giáo dục truyền thông và giảng dạy phương pháp sử dụng thông tin đúng đắn."},
            {"id": 14, "source": "이처럼 청소년들이 대중 매체를 올바르게 활용한다면 다양한 지식을 얻는 동시에 건강한 가치관을 형성할 수 있을 것이다.", "target": "Nếu thanh thiếu niên sử dụng truyền thông đại chúng một cách đúng đắn như vậy, các em có thể vừa tiếp thu được nhiều kiến thức đa dạng, vừa hình thành hệ giá trị quan lành mạnh."}
        ],
        "vi_kr": [
            {"id": 1, "source": "Trong xã hội hiện đại, truyền thông đại chúng đang đóng vai trò quan trọng trong cuộc sống hằng ngày của thanh thiếu niên.", "target": "현대 사회에서 대중 매체는 청소년들의 일상생활에서 중요한 역할을 하고 있다."},
            {"id": 2, "source": "Thanh thiếu niên đang tiếp nhận nhiều thông tin thông qua các phương tiện truyền thông đa dạng như truyền hình, Internet và mạng xã hội.", "target": "청소년들은 텔레비전이나 인터넷, SNS 등 다양한 매체를 통해 많은 정보를 얻고 있다."},
            {"id": 3, "source": "Trước tiên, thông qua truyền thông đại chúng, thanh thiếu niên có thể dễ dàng tiếp cận những sự kiện đa dạng xảy ra trong xã hội và những kiến thức mới.", "target": "먼저 대중 매체를 통해 청소년들은 사회에서 일어나는 다양한 사건과 새로운 지식을 쉽게 접할 수 있다."},
            {"id": 4, "source": "Thông qua đó, các em có thể mở rộng phạm vi hiểu biết về thế giới và tiếp thu kiến thức, thông tin về lĩnh vực mà bản thân quan tâm.", "target": "이를 통해 세상에 대한 이해의 폭을 넓히고 자신의 관심 분야에 대한 지식과 정보를 얻을 수 있다."},
            {"id": 5, "source": "Ngoài ra, thông qua việc tiếp xúc với suy nghĩ và văn hóa của nhiều người khác nhau, các em có thể hiểu được lập trường của người khác và mở rộng góc nhìn về thế giới.", "target": "또한 다양한 사람들의 생각과 문화를 접하면서 다른 사람의 입장을 이해하고 세상을 바라보는 시각을 넓힐 수 있다."},
            {"id": 6, "source": "Tuy nhiên, truyền thông đại chúng đôi khi cũng gây ra những ảnh hưởng tiêu cực đến hệ giá trị quan của thanh thiếu niên.", "target": "그러나 대중 매체는 청소년들의 가치관에 부정적인 영향을 미치기도 한다."},
            {"id": 7, "source": "Trước hết, nếu thường xuyên tiếp xúc với những nội dung kích động và bạo lực, các em sẽ có khả năng xem nhẹ hành vi bạo lực hoặc bắt chước những hành vi sai trái cao hơn.", "target": "우선 자극적이고 폭력적인 콘텐츠에 반복적으로 노출되면 폭력적인 행동을 가볍게 여겨나 잘못된 행동을 모방할 가능성이 높아진다."},
            {"id": 8, "source": "Ngoài ra, nếu thường xuyên tiếp xúc với những hình ảnh về cuộc sống xa hoa hoặc ngoại hình trên mạng xã hội, các em có thể so sánh bản thân với người khác và chỉ coi trọng ngoại hình hoặc thành công về mặt vật chất.", "target": "또한 SNS에 올라오는 화려한 생활이나 외모를 자주 접하게 되면 다른 사람과 자신을 비교하면서 외모나 물질적인 성공만을 중요하게 생각할 수 있다."},
            {"id": 9, "source": "Điều này có thể làm giảm lòng tự trọng và cản trở việc hình thành hệ giá trị quan đúng đắn.", "target": "이는 자존감을 낮추고 올바른 가치관을 형성하는 데 방해가 될 수 있다."},
            {"id": 10, "source": "Vậy thanh thiếu niên cần có thái độ như thế nào khi tiếp xúc với truyền thông đại chúng?", "target": "그렇다면 청소년들은 대중 매체를 대할 때 어떤 태도를 가져야 할까?"},
            {"id": 11, "source": "Trước tiên, thay vì tin tưởng một cách vô điều kiện vào thông tin do truyền thông cung cấp, các em cần rèn luyện thói quen kiểm chứng xem thông tin đó có đúng sự thật hay không và đánh giá một cách có tư duy phản biện.", "target": "먼저 매체에서 제공하는 정보를 무조건 믿기보다는 사실인지 확인하고 비판적으로 판단하는 습관을 길러야 한다."},
            {"id": 12, "source": "Ngoài ra, các em cần lựa chọn những nội dung cần thiết cho bản thân và điều chỉnh thời gian sử dụng một cách hợp lý.", "target": "또한 자신에게 필요한 콘텐츠를 선택하고 이용 시간을 적절히 조절해야 한다."},
            {"id": 13, "source": "Để làm được điều này, nhà trường cần tăng cường giáo dục truyền thông và giảng dạy phương pháp sử dụng thông tin đúng đắn.", "target": "이를 위해 학교에서는 미디어 교육을 강화하고 올바른 정보 이용 방법을 가르칠 필요가 있다."},
            {"id": 14, "source": "Nếu thanh thiếu niên sử dụng truyền thông đại chúng một cách đúng đắn như vậy, các em có thể vừa tiếp thu được nhiều kiến thức đa dạng, vừa hình thành hệ giá trị quan lành mạnh.", "target": "이처럼 청소년들이 대중 매체를 올바르게 활용한다면 다양한 지식을 얻는 동시에 건강한 가치관을 형성할 수 있을 것이다."}
        ]
    },
    "Đề 105: Tích lũy kinh nghiệm (Tương tự 107)": {
        "kr_vi": [
            {"id": 1, "source": "현대 사회에서는 과학 기술과 정보 통신의 발달로 사람들이 다양한 경험을 얻는 방식이 달라지고 있다.", "target": "Trong xã hội hiện đại, do sự phát triển của khoa học kỹ thuật và công nghệ thông tin, phương thức con người tiếp nhận những trải nghiệm đa dạng đang dần thay đổi."},
            {"id": 2, "source": "특히 직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 점점 많아지고 있다.", "target": "Đặc biệt, ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm."},
            {"id": 3, "source": "이처럼 간접 경험이 많아진 이유로는 먼저 인터넷과 디지털 매체의 발달을 들 수 있다.", "target": "Trước tiên, có thể kể đến sự phát triển của Internet và các phương tiện truyền thông kỹ thuật số là nguyên nhân khiến trải nghiệm gián tiếp ngày càng gia tăng như vậy."},
            {"id": 4, "source": "과거에는 새로운 지식이나 정보를 얻기 위해 직접 현장을 방문해야 했지만, 이제는 인터넷이나 동영상 등을 통해 다양한 정보를 쉽게 접할 수 있게 되었다.", "target": "Trước đây, để có được kiến thức hoặc thông tin mới, người ta phải trực tiếp đến địa điểm thực tế, nhưng ngày nay đã có thể dễ dàng tiếp cận nhiều thông tin khác nhau thông qua Internet hoặc video."},
            {"id": 5, "source": "또한 시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다.", "target": "Ngoài ra, việc có thể tiết kiệm thời gian và chi phí cũng là một nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng."},
            {"id": 6, "source": "그러나 직접 경험을 통해 얻을 수 있는 장점도 많다.", "target": "Tuy nhiên, trải nghiệm trực tiếp cũng mang lại nhiều lợi ích có thể đạt được."},
            {"id": 7, "source": "우선 어떤 일을 직접 해 보는 과정에서 책이나 영상만으로는 알기 어려운 실제적인 지식과 기술을 습득할 수 있다.", "target": "Trước hết, trong quá trình trực tiếp thử làm một việc nào đó, chúng ta có thể tiếp thu những kiến thức và kỹ năng thực tế mà chỉ thông qua sách vở hoặc video thì khó có thể hiểu được."},
            {"id": 8, "source": "또한 예상하지 못한 문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력과 자신감을 기를 수 있다.", "target": "Ngoài ra, trong quá trình đối mặt với những vấn đề không lường trước được và giải quyết chúng, chúng ta có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin."},
            {"id": 9, "source": "이러한 경험은 자신의 부족한 점을 발견하고 앞으로 발전하는 데에도 큰 도움이 된다.", "target": "Những trải nghiệm này cũng giúp ích rất nhiều trong việc phát hiện những điểm còn thiếu sót của bản thân và phát triển hơn trong tương lai."},
            {"id": 10, "source": "그렇다면 개인의 성장을 위해서는 어떻게 경험을 쌓아야 할까?", "target": "Vậy để phát triển bản thân, chúng ta nên tích lũy kinh nghiệm như thế nào?"},
            {"id": 11, "source": "먼저 실패를 두려워하지 말고 새로운 일에 적극적으로 도전하는 태도가 필요하다.", "target": "Trước tiên, cần có thái độ tích cực thử thách bản thân với những điều mới mẻ mà không sợ thất bại."},
            {"id": 12, "source": "또한 다양한 활동에 참여한 후 자신의 경험을 되돌아보고 잘한 점과 부족한 점을 분석해야 한다.", "target": "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót."},
            {"id": 13, "source": "이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다.", "target": "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất."},
            {"id": 14, "source": "이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다.", "target": "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai."}
        ],
        "vi_kr": [
            {"id": 1, "source": "Trong xã hội hiện đại, do sự phát triển của khoa học kỹ thuật và công nghệ thông tin, phương thức con người tiếp nhận những trải nghiệm đa dạng đang dần thay đổi.", "target": "현대 사회에서는 과학 기술과 정보 통신의 발달로 사람들이 다양한 경험을 얻는 방식이 달라지고 있다."},
            {"id": 2, "source": "Đặc biệt, ngày càng có nhiều người tiếp xúc với thế giới thông qua trải nghiệm gián tiếp thay vì trực tiếp trải nghiệm.", "target": "특히 직접 경험하기보다 간접 경험을 통해 세상을 접하는 사람들이 점점 많아지고 있다."},
            {"id": 3, "source": "Trước tiên, có thể kể đến sự phát triển của Internet và các phương tiện truyền thông kỹ thuật số là nguyên nhân khiến trải nghiệm gián tiếp ngày càng gia tăng như vậy.", "target": "이처럼 간접 경험이 많아진 이유로는 먼저 인터넷과 디지털 매체의 발달을 들 수 있다."},
            {"id": 4, "source": "Trước đây, để có được kiến thức hoặc thông tin mới, người ta phải trực tiếp đến địa điểm thực tế, nhưng ngày nay đã có thể dễ dàng tiếp cận nhiều thông tin khác nhau thông qua Internet hoặc video.", "target": "과거에는 새로운 지식이나 정보를 얻기 위해 직접 현장을 방문해야 했지만, 이제는 인터넷이나 동영상 등을 통해 다양한 정보를 쉽게 접할 수 있게 되었다."},
            {"id": 5, "source": "Ngoài ra, việc có thể tiết kiệm thời gian và chi phí cũng là một nguyên nhân quan trọng khiến trải nghiệm gián tiếp gia tăng.", "target": "또한 시간과 비용을 절약할 수 있다는 점도 간접 경험이 증가한 중요한 원인이다."},
            {"id": 6, "source": "Tuy nhiên, trải nghiệm trực tiếp cũng mang lại nhiều lợi ích có thể đạt được.", "target": "그러나 직접 경험을 통해 얻을 수 있는 장점도 많다."},
            {"id": 7, "source": "Trước hết, trong quá trình trực tiếp thử làm một việc nào đó, chúng ta có thể tiếp thu những kiến thức và kỹ năng thực tế mà chỉ thông qua sách vở hoặc video thì khó có thể hiểu được.", "target": "우선 어떤 일을 직접 해 보는 과정에서 책이나 영상만으로는 알기 어려운 실제적인 지식과 기술을 습득할 수 있다."},
            {"id": 8, "source": "Ngoài ra, trong quá trình đối mặt với những vấn đề không lường trước được và giải quyết chúng, chúng ta có thể rèn luyện năng lực giải quyết vấn đề và sự tự tin.", "target": "또한 예상하지 못한 문제에 부딪히고 이를 해결하는 과정에서 문제 해결 능력과 자신감을 기를 수 있다."},
            {"id": 9, "source": "Những trải nghiệm này cũng giúp ích rất nhiều trong việc phát hiện những điểm còn thiếu sót của bản thân và phát triển hơn trong tương lai.", "target": "이러한 경험은 자신의 부족한 점을 발견하고 앞으로 발전하는 데에도 큰 도움이 된다."},
            {"id": 10, "source": "Vậy để phát triển bản thân, chúng ta nên tích lũy kinh nghiệm như thế nào?", "target": "그렇다면 개인의 성장을 위해서는 어떻게 경험을 쌓아야 할까?"},
            {"id": 11, "source": "Trước tiên, cần có thái độ tích cực thử thách bản thân với những điều mới mẻ mà không sợ thất bại.", "target": "먼저 실패를 두려워하지 말고 새로운 일에 적극적으로 도전하는 태도가 필요하다."},
            {"id": 12, "source": "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót.", "target": "또한 다양한 활동에 참여한 후 자신의 경험을 되돌아보고 잘한 점과 부족한 점을 분석해야 한다."},
            {"id": 13, "source": "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất.", "target": "이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다."},
            {"id": 14, "source": "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai.", "target": "이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다."}
        ]
    },
    "Đề 104: Vệ sinh công cộng": {
        "kr_vi": [
            {"id": 1, "source": "현대 사회에서 공공위생은 개인의 건강뿐만 아니라 사회 전체의 안전과 삶의 질에 영향을 미치는 중요한 요소이다.", "target": "Trong xã hội hiện đại, vệ sinh công cộng là một yếu tố quan trọng, gây ảnh hưởng không chỉ đến sức khỏe cá nhân mà còn đến sự an toàn và chất lượng cuộc sống của toàn xã hội."},
            {"id": 2, "source": "특히 많은 사람들이 함께 생활하는 공간일수록 공공위생 관리가 더욱 중요하다.", "target": "Đặc biệt, ở những không gian có nhiều người cùng sinh sống thì việc quản lý vệ sinh công cộng càng trở nên quan trọng hơn."},
            {"id": 3, "source": "먼저 공공위생이 중요한 이유는 감염병의 확산을 예방하고 쾌적한 생활환경을 유지할 수 있기 때문이다.", "target": "Trước tiên, lý do vệ sinh công cộng quan trọng là vì có thể ngăn ngừa sự lây lan của các bệnh truyền nhiễm và duy trì môi trường sống dễ chịu, sạch sẽ."},
            {"id": 4, "source": "공공장소가 깨끗하게 관리되면 세균이나 바이러스에 노출될 위험이 줄어들어 사람들이 보다 안전하게 생활할 수 있다.", "target": "Nếu các địa điểm công cộng được quản lý sạch sẽ, nguy cơ tiếp xúc với vi khuẩn hoặc virus sẽ giảm xuống, nhờ đó mọi người có thể sinh hoạt an toàn hơn."},
            {"id": 5, "source": "또한 깨끗한 환경은 시민들의 건강을 보호하고 생활 만족도를 높이는 데에도 도움이 된다.", "target": "Ngoài ra, môi trường sạch sẽ cũng giúp bảo vệ sức khỏe của người dân và nâng cao mức độ hài lòng trong cuộc sống."},
            {"id": 6, "source": "반면 공공위생 관리가 제대로 이루어지지 않으면 여러 가지 문제가 발생할 수 있다.", "target": "Ngược lại, nếu việc quản lý vệ sinh công cộng không được thực hiện đúng cách thì nhiều vấn đề khác nhau có thể phát sinh."},
            {"id": 7, "source": "우선 쓰레기와 오염 물질이 쌓이면 악취가 발생하고 해충이 번식하여 각종 질병을 유발할 수 있다.", "target": "Trước hết, nếu rác thải và các chất ô nhiễm tích tụ, mùi hôi sẽ phát sinh và côn trùng gây hại sinh sôi, từ đó có thể gây ra nhiều loại bệnh khác nhau."},
            {"id": 8, "source": "또한 감염병이 빠르게 확산될 위험이 커지며, 이는 개인의 건강을 넘어 사회 전체에 경제적 부담을 줄 수도 있다.", "target": "Ngoài ra, nguy cơ các bệnh truyền nhiễm lây lan nhanh chóng sẽ tăng lên, điều này không chỉ ảnh hưởng đến sức khỏe cá nhân mà còn có thể gây ra gánh nặng kinh tế cho toàn xã hội."},
            {"id": 9, "source": "나아가 도시의 이미지가 나빠지고 관광객이나 방문객이 줄어드는 결과로 이어질 수 있다.", "target": "Hơn nữa, điều này có thể dẫn đến kết quả là hình ảnh của thành phố trở nên xấu đi và số lượng khách du lịch hoặc khách tham quan giảm xuống."},
            {"id": 10, "source": "그렇다면 공공위생을 개선하기 위해서는 어떤 노력이 필요할까?", "target": "Vậy cần có những nỗ lực nào để cải thiện vệ sinh công cộng?"},
            {"id": 11, "source": "먼저 정부와 지방자치단체는 공공장소의 청소와 쓰레기 수거를 정기적으로 실시하고 위생 시설을 확충해야 한다.", "target": "Trước tiên, chính phủ và chính quyền địa phương cần thường xuyên tiến hành vệ sinh các địa điểm công cộng, thu gom rác thải và mở rộng các cơ sở, trang thiết bị vệ sinh."},
            {"id": 12, "source": "또한 시민들은 쓰레기를 함부로 버리지 않고 분리배출을 실천하는 등 일상생활에서 위생 수칙을 지켜야 한다.", "target": "Ngoài ra, người dân cần tuân thủ các quy tắc vệ sinh trong cuộc sống hằng ngày, chẳng hạn như không vứt rác bừa bãi và thực hiện phân loại rác thải."},
            {"id": 13, "source": "이와 함께 학교와 지역 사회에서는 위생 교육과 캠페인을 통해 시민들의 인식을 높일 필요가 있다.", "target": "Cùng với đó, nhà trường và cộng đồng địa phương cần nâng cao nhận thức của người dân thông qua giáo dục vệ sinh và các chiến dịch tuyên truyền."},
            {"id": 14, "source": "이처럼 정부의 체계적인 관리와 시민들의 자발적인 참여가 함께 이루어진다면 더욱 깨끗하고 건강한 사회를 만들 수 있을 것이다.", "target": "Nếu việc quản lý có hệ thống của chính phủ và sự tham gia tự giác của người dân được thực hiện đồng thời như vậy thì chúng ta có thể xây dựng một xã hội sạch sẽ và lành mạnh hơn."}
        ],
        "vi_kr": [
            {"id": 1, "source": "Trong xã hội hiện đại, vệ sinh công cộng là một yếu tố quan trọng, gây ảnh hưởng không chỉ đến sức khỏe cá nhân mà còn đến sự an toàn và chất lượng cuộc sống của toàn xã hội.", "target": "현대 사회에서 공공위생은 개인의 건강뿐만 아니라 사회 전체의 안전과 삶의 질에 영향을 미치는 중요한 요소이다."},
            {"id": 2, "source": "Đặc biệt, ở những không gian có nhiều người cùng sinh sống thì việc quản lý vệ sinh công cộng càng trở nên quan trọng hơn.", "target": "특히 많은 사람들이 함께 생활하는 공간일수록 공공위생 관리가 더욱 중요하다."},
            {"id": 3, "source": "Trước tiên, lý do vệ sinh công cộng quan trọng là vì có thể ngăn ngừa sự lây lan của các bệnh truyền nhiễm và duy trì môi trường sống dễ chịu, sạch sẽ.", "target": "먼저 공공위생이 중요한 이유는 감염병의 확산을 예방하고 쾌적한 생활환경을 유지할 수 있기 때문이다."},
            {"id": 4, "source": "Nếu các địa điểm công cộng được quản lý sạch sẽ, nguy cơ tiếp xúc với vi khuẩn hoặc virus sẽ giảm xuống, nhờ đó mọi người có thể sinh hoạt an toàn hơn.", "target": "공공장소가 깨끗하게 관리되면 세균이나 바이러스에 노출될 위험이 줄어들어 사람들이 보다 안전하게 생활할 수 있다."},
            {"id": 5, "source": "Ngoài ra, môi trường sạch sẽ cũng giúp bảo vệ sức khỏe của người dân và nâng cao mức độ hài lòng trong cuộc sống.", "target": "또한 깨끗한 환경은 시민들의 건강을 보호하고 생활 만족도를 높이는 데에도 도움이 된다."},
            {"id": 6, "source": "Ngược lại, nếu việc quản lý vệ sinh công cộng không được thực hiện đúng cách thì nhiều vấn đề khác nhau có thể phát sinh.", "target": "반면 공공위생 관리가 제대로 이루어지지 않으면 여러 가지 문제가 발생할 수 있다."},
            {"id": 7, "source": "Trước hết, nếu rác thải và các chất ô nhiễm tích tụ, mùi hôi sẽ phát sinh và côn trùng gây hại sinh sôi, từ đó có thể gây ra nhiều loại bệnh khác nhau.", "target": "우선 쓰레기와 오염 물질이 쌓이면 악취가 발생하고 해충이 번식하여 각종 질병을 유발할 수 있다."},
            {"id": 8, "source": "Ngoài ra, nguy cơ các bệnh truyền nhiễm lây lan nhanh chóng sẽ tăng lên, điều này không chỉ ảnh hưởng đến sức khỏe cá nhân mà còn có thể gây ra gánh nặng kinh tế cho toàn xã hội.", "target": "또한 감염병이 빠르게 확산될 위험이 커지며, 이는 개인의 건강을 넘어 사회 전체에 경제적 부담을 줄 수도 있다."},
            {"id": 9, "source": "Hơn nữa, điều này có thể dẫn đến kết quả là hình ảnh của thành phố trở nên xấu đi và số lượng khách du lịch hoặc khách tham quan giảm xuống.", "target": "나아가 도시의 이미지가 나빠지고 관광객이나 방문객이 줄어드는 결과로 이어질 수 있다."},
            {"id": 10, "source": "Vậy cần có những nỗ lực nào để cải thiện vệ sinh công cộng?", "target": "그렇다면 공공위생을 개선하기 위해서는 어떤 노력이 필요할까?"},
            {"id": 11, "source": "Trước tiên, chính phủ và chính quyền địa phương cần thường xuyên tiến hành vệ sinh các địa điểm công cộng, thu gom rác thải và mở rộng các cơ sở, trang thiết bị vệ sinh.", "target": "먼저 정부와 지방자치단체는 공공장소의 청소와 쓰레기 수거를 정기적으로 실시하고 위생 시설을 확충해야 한다."},
            {"id": 12, "source": "Ngoài ra, người dân cần tuân thủ các quy tắc vệ sinh trong cuộc sống hằng ngày, chẳng hạn như không vứt rác bừa bãi và thực hiện phân loại rác thải.", "target": "또한 시민들은 쓰레기를 함부로 버리지 않고 분리배출을 실천하는 등 일상생활에서 위생 수칙을 지켜야 한다."},
            {"id": 13, "source": "Cùng với đó, nhà trường và cộng đồng địa phương cần nâng cao nhận thức của người dân thông qua giáo dục vệ sinh và các chiến dịch tuyên truyền.", "target": "이와 함께 학교와 지역 사회에서는 위생 교육과 캠페인을 통해 시민들의 인식을 높일 필요가 있다."},
            {"id": 14, "source": "Nếu việc quản lý có hệ thống của chính phủ và sự tham gia tự giác của người dân được thực hiện đồng thời như vậy thì chúng ta có thể xây dựng một xã hội sạch sẽ và lành mạnh hơn.", "target": "이처럼 정부의 체계적인 관리와 시민들의 자발적인 참여가 함께 이루어진다면 더욱 깨끗하고 건강한 사회를 만들 수 있을 것이다."}
        ]
    }
}

# ==========================================
# TỪ VỰNG & NGỮ PHÁP MỞ RỘNG TOPIK II (3-6)
# ==========================================

TOPIK_VOCAB = [
    {"word": "초래하다", "level": "TOPIK 5-6", "meaning": "Gây ra, dẫn đến (kết quả xấu)", "example": "지나친 경쟁은 부정적인 결과를 초래할 수 있다.", "example_meaning": "Cạnh tranh quá mức có thể dẫn đến kết quả tiêu cực."},
    {"word": "바람직하다", "level": "TOPIK 4-5", "meaning": "Đáng mong muốn, lành mạnh", "example": "바람직한 경쟁이 이루어져야 한다.", "example_meaning": "Cần phải có sự cạnh tranh lành mạnh."},
    {"word": "집착하다", "level": "TOPIK 5-6", "meaning": "Ám ảnh, câu nệ, bám chấp", "example": "결과에 집착하게 된다.", "example_meaning": "Dễ bị ám ảnh bởi kết quả."},
    {"word": "보완하다", "level": "TOPIK 4", "meaning": "Bổ sung, bù đắp phần thiếu sót", "example": "부족한 부분을 보완해야 한다.", "example_meaning": "Cần phải bù đắp phần còn thiếu sót."},
    {"word": "조성하다", "level": "TOPIK 5", "meaning": "Kiến tạo, tạo dựng (môi trường)", "example": "좋은 환경을 조성해야 한다.", "example_meaning": "Cần tạo ra một môi trường tốt."},
    {"word": "습득하다", "level": "TOPIK 5", "meaning": "Lĩnh hội, tiếp thu (kiến thức/kỹ năng)", "example": "실제적인 지식을 습득할 수 있다.", "example_meaning": "Có thể tiếp thu kiến thức thực tế."},
    {"word": "노출되다", "level": "TOPIK 4", "meaning": "Bị phơi nhiễm, tiếp xúc", "example": "자극적인 콘텐츠에 노출되다.", "example_meaning": "Bị tiếp xúc với nội dung kích động."},
    {"word": "모방하다", "level": "TOPIK 5", "meaning": "Mô phỏng, bắt chước", "example": "잘못된 행동을 모방할 가능성이 있다.", "example_meaning": "Có khả năng bắt chước hành vi sai trái."},
    {"word": "유발하다", "level": "TOPIK 5", "meaning": "Gây ra, kích phát (dịch bệnh, sự cố)", "example": "각종 질병을 유발할 수 있다.", "example_meaning": "Có thể gây ra nhiều loại bệnh khác nhau."},
    {"word": "확충하다", "level": "TOPIK 5-6", "meaning": "Mở rộng và tăng cường (cơ sở hạ tầng)", "example": "위생 시설을 확충해야 한다.", "example_meaning": "Cần mở rộng trang thiết bị vệ sinh."}
]

TOPIK_54_GRAMMAR = [
    {"grammar": "-기 마련이다", "usage": "Đương nhiên sẽ, quy luật tất yếu", "example": "시간이 지나면 잊혀지기 마련이다.", "example_meaning": "Thời gian trôi qua thì đương nhiên sẽ bị lãng quên."},
    {"grammar": "-을/를 초래하다", "usage": "Gây ra kết quả tiêu cực (văn viết trang trọng)", "example": "심각한 문제를 초래할 수 있다.", "example_meaning": "Có thể gây ra vấn đề nghiêm trọng."},
    {"grammar": "-기보다는", "usage": "Thay vì... thì...", "example": "결과를 강조하기보다는 과정을 coi trọng.", "example_meaning": "Thay vì nhấn mạnh kết quả thì nên coi trọng quá trình."},
    {"grammar": "-을 뿐만 아니라", "usage": "Không những... mà còn...", "example": "건강뿐만 아니라 삶의 질에도 영향을 미친다.", "example_meaning": "Không những ảnh hưởng tới sức khỏe mà còn tới chất lượng cuộc sống."},
    {"grammar": "-을/를 통해(서)", "usage": "Thông qua...", "example": "경험을 통해 성장할 수 있다.", "example_meaning": "Thông qua trải nghiệm có thể trưởng thành."}
]

SYNONYMS = {
    "좋은 성적": ["điểm số tốt", "thành tích tốt", "kết quả học tập tốt"],
    "높은 순위": ["thứ hạng cao", "vị trí xếp hạng cao", "xếp hạng cao"],
    "결과에 집착하다": ["ám ảnh với kết quả", "quá chú trọng vào kết quả"],
    "경쟁": ["cạnh tranh", "sự cạnh tranh", "thi đua"],
    "능력": ["năng lực", "khả năng", "thực lực"],
    "부족한 점": ["điểm thiếu sót", "điểm còn thiếu", "điểm yếu"],
    "개선하다": ["cải thiện", "khắc phục", "nâng cao"],
    "지나친 경쟁": ["cạnh tranh quá mức", "sự cạnh tranh thái quá"],
    "부정적인 결과": ["kết quả tiêu cực", "hậu quả tiêu cực"],
    "바람직한 경쟁": ["cạnh tranh lành mạnh", "sự cạnh tranh đáng mong muốn"],
    "간접 경험": ["trải nghiệm gián tiếp", "kinh nghiệm gián tiếp"],
    "직접 경험": ["trải nghiệm trực tiếp", "kinh nghiệm trực tiếp"],
    "공공위생": ["vệ sinh công cộng", "y tế công cộng"],
    "대중 매체": ["truyền thông đại chúng", "phương tiện truyền thông"]
}

# ==========================================
# CÁC HÀM XỬ LÝ VÀ CHẤM ĐIỂM
# ==========================================

def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[\s.,?!:;“”\"'()~–\-·]", "", text)
    return text

def token_set(text):
    return set(re.findall(r"[가-힣]+|[a-zA-ZÀ-ỹ]+", text.lower()))

def find_synonym_hits(user_text, reference_text, direction):
    hits = []
    if direction == "kr_vi":
        for kr, variants in SYNONYMS.items():
            if kr in reference_text:
                matched = [v for v in variants if normalize(v) in normalize(user_text)]
                if matched:
                    hits.append((kr, ", ".join(matched)))
    else:
        for kr, variants in SYNONYMS.items():
            matched = [v for v in variants if normalize(v) in normalize(reference_text)]
            if matched and any(normalize(v) in normalize(user_text) for v in variants):
                hits.append((", ".join(variants), kr))
    return hits

def evaluate_rule_based(user_text, reference, direction):
    u, r = normalize(user_text), normalize(reference)
    seq = difflib.SequenceMatcher(None, u, r).ratio() if u and r else 0.0
    ut, rt = token_set(user_text), token_set(reference)
    overlap = len(ut & rt) / max(1, len(rt))
    synonym_hits = find_synonym_hits(user_text, reference, direction)

    synonym_bonus = min(0.25, 0.07 * len(synonym_hits))
    estimate = min(1.0, max(seq * 0.55 + overlap * 0.45, overlap + synonym_bonus))
    score = round(estimate * 10, 1)
    percent = round(estimate * 100)

    missing = sorted(rt - ut)
    notes = []
    notes.append("Đây là điểm ước lượng theo quy tắc/từ khóa miễn phí, không phải phần trăm hiểu đúng ngữ nghĩa.")
    if synonym_hits:
        notes.append("Có nhận diện được cách diễn đạt tương đương: " + "; ".join(f"{a} ↔ {b}" for a, b in synonym_hits[:8]))
    else:
        notes.append("Chưa nhận diện được cụm tương đương trong từ điển nhỏ của ứng dụng; điều này không đồng nghĩa bản dịch sai.")
    if missing:
        notes.append("Một số từ trong đáp án tham khảo chưa xuất hiện nguyên dạng: " + ", ".join(missing[:12]))
        notes.append("Hãy kiểm tra xem bạn đã diễn đạt bằng từ đồng nghĩa hay vô tình bỏ sót ý.")
    if estimate >= 0.8:
        level = "Mức tương đồng từ ngữ khá cao"
    elif estimate >= 0.5:
        level = "Có một phần từ/cụm tương ứng"
    else:
        level = "Cần tự đối chiếu lại nội dung"
    return score, percent, level, notes, synonym_hits

def speak_button(text, key, label="🔊 Nghe phát âm"):
    safe_text = json.dumps(text, ensure_ascii=False)
    component = f"""
    <button id="b_{key}" style="padding:8px 13px;border:1px solid #bbb;border-radius:8px;background:white;cursor:pointer">
      {html.escape(label)}
    </button>
    <script>
    const btn = document.getElementById("b_{key}");
    btn.onclick = () => {{
      if (!('speechSynthesis' in window)) {{
        alert('Trình duyệt này không hỗ trợ đọc văn bản. Hãy thử Chrome.');
        return;
      }}
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance({safe_text});
      u.lang = 'ko-KR';
      u.rate = 0.85;
      const voices = window.speechSynthesis.getVoices();
      const korean = voices.find(v => v.lang && v.lang.toLowerCase().startsWith('ko'));
      if (korean) u.voice = korean;
      window.speechSynthesis.speak(u);
    }};
    </script>
    """
    st.components.v1.html(component, height=48)

# ==========================================
# GIAO DIỆN CHÍNH STREAMLIT
# ==========================================

st.title("🇰🇷 Luyện dịch Hàn – Việt theo định hướng TOPIK II")
st.caption("Phiên bản miễn phí: không dùng OpenAI API, không cần API Key, không phát sinh phí API từ ứng dụng.")

# Chọn bài đề thi
selected_topic_name = st.sidebar.selectbox("📂 Chọn Đề thi / Chủ đề luyện tập", list(TOPICS_DATA.keys()))
current_topic = TOPICS_DATA[selected_topic_name]

menu = st.sidebar.selectbox("Chọn chế độ", [
    "Luyện dịch Hàn → Việt", "Luyện dịch Việt → Hàn",
    "📚 Từ vựng TOPIK", "✍️ Ngữ pháp TOPIK 54", "📝 Chấm câu tự nhập"
])

if "idx_k2v" not in st.session_state: st.session_state.idx_k2v = 0
if "idx_v2k" not in st.session_state: st.session_state.idx_v2k = 0

def render_practice(direction, data):
    is_k2v = direction == "kr_vi"
    state_key = "idx_k2v" if is_k2v else "idx_v2k"
    idx = st.session_state[state_key]
    title = "Hàn → Việt" if is_k2v else "Việt → Hàn"
    
    st.subheader(f"Luyện dịch {title} - [{selected_topic_name}]")
    if idx >= len(data):
        st.success(f"Bạn đã hoàn thành tất cả {len(data)} câu của {selected_topic_name}.")
        if st.button("Làm lại từ câu 1", key=f"restart_{direction}"):
            st.session_state[state_key] = 0
            st.rerun()
        return
        
    q = data[idx]
    st.write(f"**Câu {idx+1}/{len(data)}**")
    st.info(q["source"])
    
    if is_k2v:
        speak_button(q["source"], f"source_{direction}_{idx}")
        answer = st.text_area("Nhập bản dịch tiếng Việt:", key=f"answer_{direction}_{idx}", height=100)
    else:
        answer = st.text_area("Nhập bản dịch tiếng Hàn:", key=f"answer_{direction}_{idx}", height=100)
        speak_button(q["target"], f"reference_{direction}_{idx}", "🔊 Nghe câu tham khảo")
        
    if st.button("Chấm thử", key=f"grade_{direction}_{idx}"):
        if not answer.strip():
            st.warning("Bạn hãy nhập bản dịch trước.")
        else:
            score, pct, level, notes, hits = evaluate_rule_based(answer, q["target"], direction)
            st.markdown("### Kết quả tham khảo")
            c1, c2 = st.columns(2)
            c1.metric("Điểm ước lượng", f"{score}/10")
            c2.metric("Chỉ số từ ngữ", f"{pct}%")
            st.write(f"**Nhận xét:** {level}")
            for note in notes: st.write("• " + note)
            if hits:
                st.write("**Cụm tương đương được nhận diện:**")
                for a, b in hits: st.write(f"- {a} ↔ {b}")
            st.write("**Đáp án tham khảo:**")
            st.success(q["target"])
            if not is_k2v:
                speak_button(q["target"], f"answer_{direction}_{idx}", "🔊 Nghe đáp án tiếng Hàn")
            st.caption("Lưu ý: công cụ miễn phí này không thể xác nhận chính xác ngữ nghĩa như giảng viên hoặc mô hình AI. Đừng xem % là xác suất dịch đúng.")
            
    a, b = st.columns(2)
    with a:
        if st.button("Câu tiếp theo ➡️", key=f"next_{direction}_{idx}"):
            st.session_state[state_key] += 1
            st.rerun()
    with b:
        if st.button("🔄 Làm lại phần này", key=f"reset_{direction}_{idx}"):
            st.session_state[state_key] = 0
            st.rerun()

if menu == "Luyện dịch Hàn → Việt":
    render_practice("kr_vi", current_topic["kr_vi"])
elif menu == "Luyện dịch Việt → Hàn":
    render_practice("vi_kr", current_topic["vi_kr"])
elif menu == "📚 Từ vựng TOPIK":
    st.subheader("Từ vựng TOPIK 3–6 trọng tâm")
    for i, item in enumerate(TOPIK_VOCAB):
        with st.expander(f"{item['word']} ({item['level']}) – {item['meaning']}"):
            st.write("**Nghĩa:**", item["meaning"])
            st.write("**Ví dụ:**", item["example"])
            speak_button(item["word"], f"vocab_{i}", "🔊 Nghe từ")
            speak_button(item["example"], f"vocab_ex_{i}", "🔊 Nghe câu ví dụ")
            st.write("**Dịch:**", item["example_meaning"])
elif menu == "✍️ Ngữ pháp TOPIK 54":
    st.subheader("Biểu hiện và ngữ pháp TOPIK 54")
    for i, item in enumerate(TOPIK_54_GRAMMAR):
        with st.expander(item["grammar"]):
            st.write("**Cách dùng:**", item["usage"])
            st.write("**Ví dụ:**", item["example"])
            speak_button(item["example"], f"grammar_{i}", "🔊 Nghe câu ví dụ")
            st.write("**Dịch:**", item["example_meaning"])
elif menu == "📝 Chấm câu tự nhập":
    st.subheader("Luyện dịch câu tự nhập – chế độ miễn phí")
    direction_label = st.radio("Chiều dịch", ["Hàn → Việt", "Việt → Hàn"], horizontal=True)
    direction = "kr_vi" if direction_label == "Hàn → Việt" else "vi_kr"
    source_text = st.text_area("Câu gốc")
    answer_text = st.text_area("Bản dịch của bạn")
    reference_text = st.text_area("Đáp án tham khảo (cùng ngôn ngữ với bản dịch, nếu có)")
    if direction == "kr_vi" and source_text.strip():
        speak_button(source_text, "custom_source")
    if direction == "vi_kr" and answer_text.strip():
        speak_button(answer_text, "custom_answer")
    if st.button("Đánh giá tham khảo", key="custom_grade"):
        if not source_text.strip() or not answer_text.strip():
            st.warning("Hãy nhập cả câu gốc và bản dịch.")
        elif not reference_text.strip():
            st.info("Bạn chưa nhập đáp án tham khảo. Ứng dụng miễn phí không thể tự hiểu và chấm chính xác một cặp câu khác ngôn ngữ nếu không có đáp án đối chiếu. Hãy thêm đáp án tham khảo bằng ngôn ngữ đích để xem chỉ số từ ngữ.")
        else:
            score, pct, level, notes, hits = evaluate_rule_based(answer_text, reference_text, direction)
            st.metric("Điểm ước lượng", f"{score}/10")
            st.metric("Chỉ số từ ngữ", f"{pct}%")
            st.write(level)
            for note in notes: st.write("• " + note)

st.sidebar.markdown("---")
st.sidebar.caption("Miễn phí, không tích hợp OpenAI API. Phát âm dùng giọng tiếng Hàn có sẵn trong trình duyệt/thiết bị; có thể không hoạt động nếu thiết bị không có giọng ko-KR.")
