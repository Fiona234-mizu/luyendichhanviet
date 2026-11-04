import streamlit as st
import re
import difflib
import html
import json

st.set_page_config(page_title="Luyện dịch TOPIK II – miễn phí", page_icon="🇰🇷", layout="wide")

# Dữ liệu luyện tập được giữ từ phiên bản bạn gửi.
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

SYNONYMS = {
    "좋은 성적": ["điểm số tốt", "thành tích tốt", "kết quả học tập tốt"],
    "높은 순위": ["thứ hạng cao", "vị trí xếp hạng cao", "xếp hạng cao"],
    "결과에 집착하다": ["ám ảnh với kết quả", "quá chú trọng vào kết quả", "bám chấp vào kết quả"],
    "경쟁": ["cạnh tranh", "sự cạnh tranh", "thi đua"],
    "능력": ["năng lực", "khả năng", "thực lực"],
    "부족한 점": ["điểm thiếu sót", "điểm còn thiếu", "điểm yếu"],
    "개선하다": ["cải thiện", "khắc phục", "nâng cao"],
    "지나친 경쟁": ["cạnh tranh quá mức", "sự cạnh tranh thái quá"],
    "부정적인 결과": ["kết quả tiêu cực", "hậu quả tiêu cực", "kết quả không tốt"],
    "바람직한 경쟁": ["cạnh tranh lành mạnh", "sự cạnh tranh đáng mong muốn"],
    "심리적 부담": ["áp lực tâm lý", "gánh nặng tâm lý"],
    "부정행위": ["hành vi gian lận", "việc gian lận"],
    "협력하다": ["hợp tác", "phối hợp"],
    "장점": ["ưu điểm", "điểm mạnh", "thế mạnh"],
    "보완하다": ["bù đắp", "bổ sung", "khắc phục"],
    "조성하다": ["tạo ra", "tạo dựng", "xây dựng", "kiến tạo"],
    "자극제": ["động lực", "yếu tố thúc đẩy", "chất xúc tác"],
    "성장하다": ["trưởng thành", "phát triển"],
    "존중하다": ["tôn trọng", "coi trọng"],
    "교우 관계": ["quan hệ bạn bè", "mối quan hệ bạn bè"],
}

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
        level = "Mức tương đồng từ ngữ khá cao 🎉"
    elif estimate >= 0.5:
        level = "Có một phần từ/cụm tương ứng 👍"
    else:
        level = "Cần tự đối chiếu lại nội dung 💡"
    return score, percent, level, notes, synonym_hits, estimate

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

st.title("🇰🇷 Luyện dịch Hàn – Việt theo định hướng TOPIK II")
st.caption("Phiên bản miễn phí: không dùng OpenAI API, không cần API Key, không phát sinh phí API từ ứng dụng.")

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
    st.subheader(f"Luyện dịch {title}")
    if idx >= len(data):
        st.success(f"Bạn đã hoàn thành {len(data)} câu của phần {title}.")
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
            score, pct, level, notes, hits, estimate = evaluate_rule_based(answer, q["target"], direction)
            st.markdown("### Kết quả đánh giá")
            
            # Hiển thị tỷ lệ phần trăm chính xác trực quan
            st.metric(label="📊 Mức độ chính xác so với đáp án", value=f"{pct}%")
            st.progress(float(min(1.0, max(0.0, estimate))))
            
            c1, c2 = st.columns(2)
            c1.metric("Điểm ước lượng", f"{score}/10")
            c2.metric("Trạng thái", level)
            
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
    render_practice("kr_vi", KR_TO_VI_LIST)
elif menu == "Luyện dịch Việt → Hàn":
    render_practice("vi_kr", VI_TO_KR_LIST)
elif menu == "📚 Từ vựng TOPIK":
    st.subheader("Từ vựng TOPIK 3–6")
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
            score, pct, level, notes, hits, estimate = evaluate_rule_based(answer_text, reference_text, direction)
            st.metric(label="📊 Mức độ chính xác so với đáp án", value=f"{pct}%")
            st.progress(float(min(1.0, max(0.0, estimate))))
            
            c1, c2 = st.columns(2)
            c1.metric("Điểm ước lượng", f"{score}/10")
            c2.metric("Trạng thái", level)
            
            for note in notes: st.write("• " + note)

st.sidebar.markdown("---")
st.sidebar.caption("Miễn phí, không tích hợp OpenAI API. Phát âm dùng giọng tiếng Hàn có sẵn trong trình duyệt/thiết bị; có thể không hoạt động nếu thiết bị không có giọng ko-KR.")
