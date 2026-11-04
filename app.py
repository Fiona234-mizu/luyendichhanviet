import streamlit as st
import re
import difflib
import html
import json

st.set_page_config(page_title="Luyện dịch TOPIK II câu 54 – Miễn phí", page_icon="🇰🇷", layout="wide")

# ==========================================
# 1. DỮ LIỆU BÀI LUYỆN DỊCH (8 ĐỀ TOPIK 54)
# ==========================================
TOPIK_54_TOPICS = {
    "Đề 107: 직업 체험 교육 (Giáo dục trải nghiệm nghề nghiệp)": {
        "kr_vi": [
            {"id": 1, "source": "청소년기는 자신의 적성과 흥미를 발견하고 미래의 진로를 결정하는 중요한 시기이다.", "target": "Tuổi thanh thiếu niên là giai đoạn quan trọng để khám phá năng lực, sở thích của bản thân và quyết định con đường nghề nghiệp trong tương lai."},
            {"id": 2, "source": "그러나 많은 청소년들이 진로를 선택하는 과정에서 여러 가지 어려움을 겪고 있다.", "target": "Tuy nhiên, nhiều thanh thiếu niên đang gặp phải nhiều khó khăn khác nhau trong quá trình lựa chọn nghề nghiệp."},
            {"id": 3, "source": "먼저 자신의 적성과 능력을 정확하게 파악하지 못한다는 점을 들 수 있다.", "target": "Trước tiên, có thể kể đến việc không thể xác định chính xác năng lực và sở trường của bản thân."},
            {"id": 4, "source": "자신이 무엇을 좋아하고 어떤 분야에 소질이 있는지 충분히 알지 못하기 때문에 진로를 결정하는 데 어려움을 느끼는 것이다.", "target": "Vì không hiểu rõ bản thân thích điều gì và có năng khiếu trong lĩnh vực nào nên các em cảm thấy khó khăn trong việc quyết định nghề nghiệp."},
            {"id": 5, "source": "또한 직업에 대한 정보와 실제 경험이 부족하여 부모나 주변 사람들의 기대에 따라 진로를 선택하는 경우도 적지 않다.", "target": "Ngoài ra, do thiếu thông tin và kinh nghiệm thực tế về nghề nghiệp nên cũng có không ít trường hợp lựa chọn nghề nghiệp theo kỳ vọng của cha mẹ hoặc những người xung quanh."},
            {"id": 6, "source": "이러한 상황에서 직업 체험 교육은 청소년들에게 큰 도움을 줄 수 있다.", "target": "Trong hoàn cảnh đó, giáo dục trải nghiệm nghề nghiệp có thể mang lại nhiều lợi ích cho thanh thiếu niên."},
            {"id": 7, "source": "우선 다양한 직업을 직접 경험함으로써 자신의 적성과 흥미를 구체적으로 파악할 수 있다.", "target": "Trước hết, thông qua việc trực tiếp trải nghiệm nhiều nghề nghiệp khác nhau, các em có thể xác định cụ thể năng lực và sở thích của bản thân."},
            {"id": 8, "source": "이를 통해 막연하게 생각했던 진로를 현실적으로 계획하고 자신에게 적합한 직업을 선택할 수 있게 된다.", "target": "Thông qua đó, các em có thể lập kế hoạch thực tế cho con đường nghề nghiệp mà trước đây mình chỉ nghĩ đến một cách mơ hồ, đồng thời có thể lựa chọn công việc phù hợp với bản thân."},
            {"id": 9, "source": "또한 실제 직업 현장을 경험하면서 해당 직업에 필요한 능력과 책임감을 이해할 수 있으며, 미래를 준비하는 데 필요한 동기와 자신감도 얻을 수 있다.", "target": "Ngoài ra, thông qua việc trải nghiệm môi trường làm việc thực tế, các em có thể hiểu được những năng lực và tinh thần trách nhiệm cần thiết đối với nghề nghiệp đó, đồng thời có được động lực và sự tự tin cần thiết để chuẩn bị cho tương lai."},
            {"id": 10, "source": "그렇다면 학교는 의미 있는 직업 체험 교육을 위해 무엇을 해야 할까?", "target": "Vậy nhà trường cần làm gì để tổ chức hoạt động giáo dục trải nghiệm nghề nghiệp có ý nghĩa?"},
            {"id": 11, "source": "먼저 학생들의 관심 분야와 적성을 고려하여 다양한 직업 체험 프로그램을 마련해야 한다.", "target": "Trước tiên, nhà trường cần xây dựng nhiều chương trình trải nghiệm nghề nghiệp đa dạng, có cân nhắc đến lĩnh vực quan tâm và năng lực của học sinh."},
            {"id": 12, "source": "단순히 직업을 소개하는 데 그치지 않고 실제 업무를 직접 해 볼 수 있는 기회를 제공하는 것이 중요하다.", "target": "Điều quan trọng là không chỉ dừng lại ở việc giới thiệu nghề nghiệp đơn thuần mà còn phải cung cấp cơ hội để học sinh trực tiếp thử sức với công việc thực tế."},
            {"id": 13, "source": "또한 기업이나 지역 사회와 협력하여 전문가와의 만남, 현장 견학 및 실습 활동을 확대해야 한다.", "target": "Ngoài ra, cần mở rộng các hoạt động gặp gỡ chuyên gia, tham quan nơi làm việc và thực hành thông qua việc hợp tác với các doanh nghiệp hoặc cộng đồng địa phương."},
            {"id": 14, "source": "이처럼 체계적이고 실질적인 직업 체험 교육이 이루어진다면 청소년들은 자신의 미래를 주도적으로 설계하고 올바른 진로를 선택하는 데 큰 도움을 받을 수 있을 것이다.", "target": "Nếu hoạt động giáo dục trải nghiệm nghề nghiệp được thực hiện một cách có hệ thống và thiết thực như vậy, thanh thiếu niên sẽ nhận được sự hỗ trợ lớn trong việc chủ động hoạch định tương lai và lựa chọn con đường nghề nghiệp đúng đắn."}
        ]
    },
    "Đề 106: 올바른 대중매체 활용 (Sử dụng truyền thông đúng đắn)": {
        "kr_vi": [
            {"id": 1, "source": "아울러 자신에게 필요한 내용을 선택하고 이용 시간을 적절하게 조절해야 한다.", "target": "Ngoài ra, các em cần lựa chọn những nội dung cần thiết cho bản thân và điều chỉnh thời gian sử dụng một cách hợp lý."},
            {"id": 2, "source": "이를 위해 학교에서는 미디어 교육을 강화하고 올바른 정보 이용 방법을 가르칠 필요가 있다.", "target": "Để làm được điều này, nhà trường cần tăng cường giáo dục truyền thông và giảng dạy phương pháp sử dụng thông tin đúng đắn."},
            {"id": 3, "source": "이처럼 청소년들이 대중 매체를 올바르게 활용한다면 다양한 지식을 얻는 동시에 건강한 가치관을 형성할 수 있을 것이다.", "target": "Nếu thanh thiếu niên sử dụng truyền thông đại chúng một cách đúng đắn như vậy, các em có thể vừa tiếp thu được nhiều kiến thức đa dạng, vừa hình thành hệ giá trị quan lành mạnh."}
        ]
    },
    "Đề 105: 경험의 중요성과 활용 (Tầm quan trọng và cách vận dụng kinh nghiệm)": {
        "kr_vi": [
            {"id": 1, "source": "아울러 다양한 활동에 참여한 후에는 자신의 경험을 돌아보고 잘한 점과 부족한 점을 분석해야 한다.", "target": "Ngoài ra, sau khi tham gia các hoạt động đa dạng, chúng ta cần nhìn lại trải nghiệm của bản thân và phân tích những điểm đã làm tốt cũng như những điểm còn thiếu sót."},
            {"id": 2, "source": "이를 통해 같은 실수를 반복하지 않고 경험을 실제적인 성장으로 연결할 수 있다.", "target": "Thông qua đó, chúng ta có thể không lặp lại những sai lầm giống nhau và biến kinh nghiệm thành sự phát triển thực chất."},
            {"id": 3, "source": "이처럼 간접 경험과 직접 경험을 적절히 활용하고 꾸준히 새로운 경험을 쌓는다면 개인의 능력을 향상시키고 더욱 주도적으로 미래를 준비할 수 있을 것이다.", "target": "Nếu biết sử dụng hợp lý cả trải nghiệm gián tiếp lẫn trải nghiệm trực tiếp, đồng thời không ngừng tích lũy những trải nghiệm mới như vậy, chúng ta có thể nâng cao năng lực cá nhân và chủ động hơn trong việc chuẩn bị cho tương lai."}
        ]
    },
    "Đề 104: 공정한 보상 제도 (Chế độ khen thưởng công bằng)": {
        "kr_vi": [
            {"id": 1, "source": "이를 통해 구성원들이 서로 돕고 함께 성장하는 분위기를 만들 수 있다.", "target": "Thông qua đó, có thể tạo ra bầu không khí trong đó các thành viên giúp đỡ lẫn nhau và cùng nhau phát triển."},
            {"id": 2, "source": "또한 단기적인 결과만으로 평가하지 않고 업무의 과정과 장기적인 발전 가능성까지 종합적으로 고려해야 한다.", "target": "Ngoài ra, không nên chỉ đánh giá dựa trên kết quả ngắn hạn mà cần xem xét một cách toàn diện cả quá trình làm việc và khả năng phát triển lâu dài."},
            {"id": 3, "source": "이처럼 공정하고 균형 잡힌 보상 제도가 마련된다면 구성원들의 만족도를 높이는 동시에 조직 전체의 지속적인 발전에도 기여할 수 있을 것이다.", "target": "Nếu một chế độ khen thưởng công bằng và cân bằng được xây dựng như vậy thì có thể vừa nâng cao mức độ hài lòng của các thành viên, vừa đóng góp vào sự phát triển bền vững của toàn bộ tổ chức."}
        ]
    },
    "Đề 103: 환경 위생과 시민 의식 (Vệ sinh môi trường và ý thức công dân)": {
        "kr_vi": [
            {"id": 1, "source": "아울러 시민들은 쓰레기를 함부로 버리지 않고 분리배출을 실천하는 등 일상생활에서 위생 수칙을 준수해야 한다.", "target": "Ngoài ra, người dân cần tuân thủ các quy tắc vệ sinh trong cuộc sống hằng ngày, chẳng hạn như không vứt rác bừa bãi và thực hiện phân loại rác thải."},
            {"id": 2, "source": "이와 함께 학교와 지역 사회에서는 위생 교육과 캠페인을 통해 시민들의 인식을 높일 필요가 있다.", "target": "Cùng với đó, nhà trường và cộng đồng địa phương cần nâng cao nhận thức của người dân thông qua giáo dục vệ sinh và các chiến dịch tuyên truyền."},
            {"id": 3, "source": "이처럼 정부의 체계적인 관리와 시민들의 자발적인 참여가 함께 이루어진다면 더욱 깨끗하고 건강한 사회를 만들 수 있을 것이다.", "target": "Nếu việc quản lý có hệ thống của chính phủ và sự tham gia tự giác của người dân được thực hiện đồng thời như vậy thì chúng ta có thể xây dựng một xã hội sạch sẽ và lành mạnh hơn."}
        ]
    },
    "Đề 102: 디지털 정보 격차 해소 (Xóa bỏ khoảng cách thông tin kỹ thuật số)": {
        "kr_vi": [
            {"id": 1, "source": "아울러 사회적으로는 고령자와 장애인을 위한 교육 프로그램을 확대하고, 누구나 쉽게 sử dụng할 수 있도록 기기의 화면과 기능을 개선해야 한다.", "target": "Ngoài ra, về mặt xã hội, cần mở rộng các chương trình giáo dục dành cho người cao tuổi và người khuyết tật, đồng thời cải thiện màn hình và chức능 của thiết bị để bất kỳ ai cũng có thể dễ dàng sử dụng."},
            {"id": 2, "source": "아울러 디지털 기기 사용이 어려운 사람들을 위해 대면 서비스도 함께 제공할 필요가 있다.", "target": "Đồng thời, cần cung cấp cả dịch vụ trực tiếp dành cho những người gặp khó khăn trong việc sử dụng thiết bị kỹ thuật số."},
            {"id": 3, "source": "이처럼 개인의 노력과 사회의 제도적 지원이 함께 이루어진다면 누구나 디지털 기술의 혜택을 누릴 수 있는 포용적인 사회를 만들 수 있을 것이다.", "target": "Nếu nỗ lực của cá nhân và sự hỗ trợ về mặt chính sách, thể chế của xã hội được thực hiện đồng thời như vậy thì chúng ta có thể xây dựng một xã hội hòa nhập, nơi bất kỳ ai cũng có thể tận hưởng những lợi ích của công nghệ số."}
        ]
    },
    "Đề 101: 재택근무의 정착 (Định hình hình thức làm việc tại nhà)": {
        "kr_vi": [
            {"id": 1, "source": "우선 기업은 화상 회의나 메신저 등 온라인 소통 수단을 적극 활용하여 직원 간의 원활한 정보 공유를 지원해야 한다.", "target": "Trước tiên, doanh nghiệp cần tích cực sử dụng các phương tiện giao tiếp trực tuyến như họp trực tuyến hoặc ứng dụng nhắn tin để hỗ trợ việc trao đổi thông tin thuận lợi giữa các nhân viên."},
            {"id": 2, "source": "또한 직원들은 정해진 근무 시간과 휴식 시간을 지키고 업무 공간을 별도로 마련하는 등 스스로 업무 환경을 관리해야 한다.", "target": "Ngoài ra, nhân viên cần tự quản lý môi trường làm việc của mình bằng cách tuân thủ thời gian làm việc và nghỉ ngơi đã quy định, đồng thời bố trí không gian làm việc riêng biệt."},
            {"id": 3, "source": "이처럼 기업의 체계적인 지원과 직원들의 자발적인 노력이 함께 이루어진다면 재택근무의 장점을 살리면서 문제점을 줄일 수 있을 것이다.", "target": "Nếu sự hỗ trợ có hệ thống của doanh nghiệp và nỗ lực tự giác của nhân viên được thực hiện đồng thời như vậy thì có thể phát huy những ưu điểm của hình thức làm việc tại nhà đồng thời giảm thiểu các vấn đề của nó."}
        ]
    },
    "Đề 100 & 99: 인공지능 활용 / 마음의 회복 (Sử dụng AI & Chữa lành tâm hồn)": {
        "kr_vi": [
            {"id": 1, "source": "아울러 인공지능에 지나치게 의존하지 않고 스스로 생각하고 판단하는 능력을 길러야 한다.", "target": "Ngoài ra, cần rèn luyện khả năng tự suy nghĩ và phán đoán mà không phụ thuộc quá mức vào AI."},
            {"id": 2, "source": "아울러 개인정보를 함부로 입력하지 않는 등 안전한 사용 방법을 익혀야 한다.", "target": "Bên cạnh đó, cần học cách sử dụng an toàn, chẳng hạn như không tùy tiện nhập thông tin cá nhân vào AI."},
            {"id": 3, "source": "이처럼 인공지능은 어떻게 활용하느냐에 따라 긍정적인 결과를 가져올 수도 있고 부정적인 결과를 초래할 수도 있다.", "target": "Như vậy, tùy thuộc vào cách sử dụng, AI có thể mang lại kết quả tích cực nhưng cũng có thể gây ra những hậu quả tiêu cực."},
            {"id": 4, "source": "그러므로 인공지능의 장점을 적극적으로 활용하되 인간의 판단력과 책임감을 바탕으로 올바르게 사용하는 것이 중요하다.", "target": "Do đó, điều quan trọng là tích cực tận dụng những ưu điểm của AI, đồng thời sử dụng nó một cách đúng đắn dựa trên khả năng phán đoán và tinh thần trách nhiệm của con người."},
            {"id": 5, "source": "아울러 운동이나 취미 활동을 통해 스트레스를 해소하고, 새로운 목표를 세워 일상에 활력을 되찾는 것도 중요하다.", "target": "Bên cạnh đó, việc giải tỏa căng thẳng thông qua tập thể dục hoặc các hoạt động sở thích, đồng thời đặt ra mục tiêu mới để lấy lại sức sống trong cuộc sống hằng ngày cũng rất quan trọng."},
            {"id": 6, "source": "이처럼 마음의 상처를 회복하는 데에는 시간이 필요하지만, 자신의 감정을 이해하고 긍정적으로 극복하려는 노력을 꾸준히 한다면 다시 건강한 마음으로 살아갈 수 있을 것이다.", "target": "Như vậy, mặc dù cần có thời gian để chữa lành những tổn thương tinh thần, nhưng nếu kiên trì nỗ lực thấu hiểu cảm xúc của bản thân và vượt qua chúng theo hướng tích cực, chúng ta sẽ có thể tiếp tục sống với một tinh thần khỏe mạnh."}
        ]
    }
}

# ==========================================
# 2. TỪ VỰNG & NGỮ PHÁP MỞ RỘNG (TOPIK 3-6)
# ==========================================
TOPIK_VOCAB = [
    {"word": "적성", "level": "TOPIK 4", "meaning": "Năng khiếu, sở trường", "example": "자신의 적성과 흥미를 발견하는 것이 중요하다.", "example_meaning": "Việc phát hiện năng khiếu và sở thích của bản thân là rất quan trọng."},
    {"word": "소질", "level": "TOPIK 4", "meaning": "Tố chất, năng khiếu", "example": "어떤 분야에 소질이 있는지 파악해야 한다.", "example_meaning": "Cần phải nắm bắt được bản thân có tố chất ở lĩnh vực nào."},
    {"word": "체계적이다", "level": "TOPIK 5", "meaning": "Có hệ thống, bài bản", "example": "체계적인 직업 체험 교육이 필요하다.", "example_meaning": "Cần có giáo dục trải nghiệm nghề nghiệp mang tính hệ thống."},
    {"word": "주도적이다", "level": "TOPIK 5", "meaning": "Chủ động, dẫn dắt", "example": "미래를 주도적으로 설계할 수 있다.", "example_meaning": "Có thể chủ động hoạch định tương lai."},
    {"word": "자발적이다", "level": "TOPIK 5", "meaning": "Tự giác, tự nguyện", "example": "시민들의 자발적인 참여가 중요하다.", "example_meaning": "Sự tham gia tự giác của người dân là rất quan trọng."},
    {"word": "포용적이다", "level": "TOPIK 6", "meaning": "Bao hàm, hòa nhập, bao용", "example": "포용적인 사회를 만들어야 한다.", "example_meaning": "Cần phải tạo ra một xã hội hòa nhập."},
    {"word": "초래하다", "level": "TOPIK 5-6", "meaning": "Gây ra, dẫn đến (kết quả xấu)", "example": "부정적인 결과를 초래할 수 있다.", "example_meaning": "Có thể gây ra kết quả tiêu cực."},
    {"word": "구체적이다", "level": "TOPIK 4", "meaning": "Cụ thể, rõ ràng", "example": "적성과 흥미를 구체적으로 파악한다.", "example_meaning": "Xác định cụ thể năng lực và sở thích."}
]

TOPIK_54_GRAMMAR = [
    {"grammar": "이처럼 ~ -ㄴ/는다/ㄹ 것이다", "usage": "Viết câu kết luận cho bài văn TOPIK 54 (Như vậy... thì sẽ...)", "example": "이처럼 체계적인 교육이 이루어진다면 올바른 진로를 선택하는 데 큰 도움이 될 것이다.", "example_meaning": "Như vậy nếu giáo dục có hệ thống được thực hiện thì sẽ trợ giúp lớn cho việc lựa chọn con đường đúng đắn."},
    {"grammar": "-는 동시에", "usage": "Đồng thời, vừa... vừa... (Diễn tả 2 hành động/trạng thái song song)", "example": "지식을 얻는 동시에 건강한 가치관을 형성할 수 있다.", "example_meaning": "Vừa tiếp thu được kiến thức, đồng thời vừa hình thành được giá trị quan lành mạnh."},
    {"grammar": "-을/를 바탕으로", "usage": "Dựa trên cơ sở..., lấy... làm nền tảng", "example": "인간의 판단력과 책임감을 바탕으로 올바르게 사용해야 한다.", "example_meaning": "Cần sử dụng đúng đắn dựa trên khả năng phán đoán và tinh thần trách nhiệm của con người."},
    {"grammar": "-에 그치지 않고", "usage": "Không dừng lại ở... (mà còn tiếp tục...)", "example": "단순히 소개하는 데 그치지 않고 직접 경험을 제공해야 한다.", "example_meaning": "Không dừng lại ở việc giới thiệu đơn thuần mà còn phải cung cấp trải nghiệm trực tiếp."}
]

SYNONYMS = {
    "청소년": ["thanh thiếu niên", "giới trẻ", "học sinh"],
    "진로": ["con đường nghề nghiệp", "hướng đi", "tương lai nghề nghiệp"],
    "적성": ["năng khiếu", "sở trường", "khả năng"],
    "흥미": ["sở thích", "hứng thú"],
    "체계적": ["có hệ thống", "bài bản"],
    "주도적": ["chủ động", "tự mình"],
    "자발적": ["tự giác", "tự nguyện"],
    "포용적": ["hòa nhập", "bao dung"]
}

# ==========================================
# 3. HÀM XỬ LÝ KỸ THUẬT & ĐÁNH GIÁ
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
    notes.append("Đây là điểm ước lượng từ vựng/cụm từ theo quy tắc tự động.")
    if synonym_hits:
        notes.append("Nhận diện được diễn đạt tương đương: " + "; ".join(f"{a} ↔ {b}" for a, b in synonym_hits[:8]))
    if missing:
        notes.append("Một số từ trong đáp án chưa xuất hiện nguyên dạng: " + ", ".join(missing[:10]))
    
    if estimate >= 0.8:
        level = "Mức tương đồng khá cao"
    elif estimate >= 0.5:
        level = "Có một số từ/cụm tương ứng"
    else:
        level = "Cần kiểm tra và chỉnh sửa lại"
    return score, percent, level, notes, synonym_hits

def speak_button(text, key, label="🔊 Nghe phát âm"):
    safe_text = json.dumps(text, ensure_ascii=False)
    component = f"""
    <button id="b_{key}" style="padding:6px 12px;border:1px solid #ccc;border-radius:6px;background:#f9f9f9;cursor:pointer">
      {html.escape(label)}
    </button>
    <script>
    const btn = document.getElementById("b_{key}");
    btn.onclick = () => {{
      if (!('speechSynthesis' in window)) {{
        alert('Trình duyệt không hỗ trợ phát âm.');
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
    st.components.v1.html(component, height=42)

# ==========================================
# 4. GIAO DIỆN STREAMLIT MAIN
# ==========================================
st.title("🇰🇷 Luyện dịch TOPIK II Câu 54 (8 Bài văn mẫu)")
st.caption("Ứng dụng miễn phí: Hệ thống chấm câu theo từ khóa & phát âm Web Speech API chuẩn giọng Hàn.")

menu = st.sidebar.selectbox("Chọn chế độ luyện tập", [
    "📝 Luyện dịch Hàn → Việt (8 Đề)", 
    "📝 Luyện dịch Việt → Hàn (8 Đề)",
    "📚 Từ vựng TOPIK 3-6", 
    "✍️ Ngữ pháp & Biểu hiện TOPIK 54", 
    "🔍 Chấm câu tự nhập"
])

# Quản lý State
if "topic_idx" not in st.session_state: st.session_state.topic_idx = 0

def render_multi_topic_practice(direction):
    is_k2v = direction == "kr_vi"
    dir_label = "Hàn → Việt" if is_k2v else "Việt → Hàn"
    
    # Chọn đề TOPIK
    selected_topic_name = st.selectbox("📌 Chọn đề TOPIK 54:", list(TOPIK_54_TOPICS.keys()))
    data_list = TOPIK_54_TOPICS[selected_topic_name]["kr_vi"]
    
    # Đặt key quản lý riêng cho từng đề
    state_key = f"idx_{direction}_{selected_topic_name}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    idx = st.session_state[state_key]

    st.subheader(f"Luyện dịch {dir_label}: {selected_topic_name}")
    
    if idx >= len(data_list):
        st.success(f"🎉 Bạn đã hoàn thành toàn bộ {len(data_list)} câu của bài này!")
        if st.button("Làm lại từ đầu", key=f"restart_{selected_topic_name}"):
            st.session_state[state_key] = 0
            st.rerun()
        return

    q = data_list[idx]
    st.markdown(f"### **Câu {idx+1} / {len(data_list)}**")
    
    # Câu nguồn
    if is_k2v:
        st.info(f"**Tiếng Hàn:** {q['source']}")
        speak_button(q["source"], f"src_{selected_topic_name}_{idx}")
        user_ans = st.text_area("Nhập bản dịch tiếng Việt của bạn:", key=f"ans_{selected_topic_name}_{idx}", height=100)
        ref_text = q["target"]
    else:
        st.info(f"**Tiếng Việt:** {q['target']}")
        user_ans = st.text_area("Nhập bản dịch tiếng Hàn của bạn:", key=f"ans_{selected_topic_name}_{idx}", height=100)
        ref_text = q["source"]
        speak_button(q["source"], f"ref_spk_{selected_topic_name}_{idx}", "🔊 Nghe câu tham khảo")

    # Chấm bài
    if st.button("Chấm câu", key=f"grade_{selected_topic_name}_{idx}"):
        if not user_ans.strip():
            st.warning("Vui lòng nhập bản dịch trước khi chấm.")
        else:
            score, pct, level, notes, hits = evaluate_rule_based(user_ans, ref_text, direction)
            st.markdown("---")
            st.markdown("#### 📊 Kết quả phân tích tham khảo")
            col1, col2 = st.columns(2)
            col1.metric("Điểm ước lượng", f"{score} / 10")
            col2.metric("Chỉ số trùng khớp từ ngữ", f"{pct}%")
            
            st.write(f"**Đánh giá:** {level}")
            for n in notes: st.write("• " + n)
            
            if hits:
                st.write("**Cụm từ tương đương nhận diện được:**")
                for a, b in hits: st.write(f"- {a} ↔ {b}")
                
            st.write("**Đáp án mẫu:**")
            st.success(ref_text)
            if is_k2v:
                speak_button(q["source"], f"ans_spk_{selected_topic_name}_{idx}", "🔊 Nghe lại tiếng Hàn")
            else:
                speak_button(q["source"], f"ans_spk_{selected_topic_name}_{idx}", "🔊 Nghe đáp án tiếng Hàn")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Câu tiếp theo ➡️", key=f"next_{selected_topic_name}_{idx}"):
            st.session_state[state_key] += 1
            st.rerun()
    with col_b:
        if st.button("🔄 Làm lại bài này", key=f"reset_{selected_topic_name}_{idx}"):
            st.session_state[state_key] = 0
            st.rerun()

# RENDER MENU SELECTION
if menu == "📝 Luyện dịch Hàn → Việt (8 Đề)":
    render_multi_topic_practice("kr_vi")
elif menu == "📝 Luyện dịch Việt → Hàn (8 Đề)":
    render_practice_v2k = render_multi_topic_practice("vi_kr")

elif menu == "📚 Từ vựng TOPIK 3-6":
    st.subheader("📚 Từ vựng quan trọng trong các bài TOPIK 54 mẫu")
    for i, item in enumerate(TOPIK_VOCAB):
        with st.expander(f"📌 {item['word']} ({item['level']}) – {item['meaning']}"):
            st.write("**Nghĩa:**", item["meaning"])
            st.write("**Ví dụ:**", item["example"])
            speak_button(item["word"], f"voc_{i}", "🔊 Nghe từ")
            speak_button(item["example"], f"voc_ex_{i}", "🔊 Nghe câu ví dụ")
            st.write("**Dịch:**", item["example_meaning"])

elif menu == "✍️ Ngữ pháp & Biểu hiện TOPIK 54":
    st.subheader("✍️ Ngữ pháp & Biểu hiện cao cấp dùng cho bài viết 54")
    for i, item in enumerate(TOPIK_54_GRAMMAR):
        with st.expander(f"🔑 {item['grammar']}"):
            st.write("**Cách dùng:**", item["usage"])
            st.write("**Ví dụ:**", item["example"])
            speak_button(item["example"], f"grm_{i}", "🔊 Nghe ví dụ")
            st.write("**Dịch:**", item["example_meaning"])

elif menu == "🔍 Chấm câu tự nhập":
    st.subheader("🔍 Chấm bản dịch tự nhập")
    dir_sel = st.radio("Chiều dịch", ["Hàn → Việt", "Việt → Hàn"], horizontal=True)
    direction = "kr_vi" if dir_sel == "Hàn → Việt" else "vi_kr"
    
    src = st.text_area("Nhập câu gốc:")
    ans = st.text_area("Nhập bản dịch của bạn:")
    ref = st.text_area("Nhập đáp án tham khảo (để đối chiếu):")
    
    if direction == "kr_vi" and src.strip():
        speak_button(src, "cust_src")
        
    if st.button("Đánh giá ngay"):
        if not src.strip() or not ans.strip() or not ref.strip():
            st.warning("Vui lòng nhập đầy đủ câu gốc, bản dịch và đáp án tham khảo.")
        else:
            score, pct, level, notes, hits = evaluate_rule_based(ans, ref, direction)
            st.metric("Điểm ước lượng", f"{score}/10")
            st.metric("Tỷ lệ khớp từ ngữ", f"{pct}%")
            st.write(level)
            for n in notes: st.write("• " + n)

st.sidebar.markdown("---")
st.sidebar.caption("Ứng dụng tự động hóa dành riêng cho học viên ôn thi TOPIK II. Phát âm sử dụng giọng đọc hệ thống ko-KR.")
