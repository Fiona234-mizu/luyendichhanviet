# -*- coding: utf-8 -*-
"""
Ứng dụng luyện dịch Hàn–Việt / Việt–Hàn TOPIK II miễn phí, không cần API trả phí.
"""
import os
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
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

# ------------------------- Sổ câu dịch đã lưu -------------------------
# SQLite giúp dữ liệu còn nguyên sau mỗi lần tải lại/chuyển trang ứng dụng.
# Trên một số nền tảng cloud, ổ đĩa cục bộ có thể bị làm mới khi triển khai lại;
# vì vậy ứng dụng có chức năng xuất/nhập bản sao lưu JSON ở mục Sổ câu đã lưu.
DB_PATH = Path(__file__).resolve().with_name("saved_custom_translations.sqlite3")


from contextlib import contextmanager


@contextmanager
def get_saved_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS saved_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            source TEXT NOT NULL,
            translation TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.commit()
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_custom_translation(direction: str, source: str, translation: str) -> None:
    with get_saved_db() as conn:
        conn.execute(
            "INSERT INTO saved_translations (direction, source, translation, created_at) VALUES (?, ?, ?, ?)",
            (direction, source.strip(), translation.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def get_custom_translations():
    with get_saved_db() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT id, direction, source, translation, created_at FROM saved_translations ORDER BY id DESC"
        ).fetchall()]


def delete_custom_translation(item_id: int) -> None:
    with get_saved_db() as conn:
        conn.execute("DELETE FROM saved_translations WHERE id = ?", (int(item_id),))


def import_custom_translations(records) -> int:
    added = 0
    with get_saved_db() as conn:
        for item in records:
            direction = item.get("direction")
            source = str(item.get("source", "")).strip()
            translation = str(item.get("translation", "")).strip()
            if direction not in ("kr_vi", "vi_kr") or not source or not translation:
                continue
            exists = conn.execute(
                "SELECT 1 FROM saved_translations WHERE direction = ? AND source = ? AND translation = ? LIMIT 1",
                (direction, source, translation),
            ).fetchone()
            if exists:
                continue
            created_at = str(item.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            conn.execute(
                "INSERT INTO saved_translations (direction, source, translation, created_at) VALUES (?, ?, ?, ?)",
                (direction, source, translation, created_at),
            )
            added += 1
    return added


# ------------------------- Ngân hàng đề tự thêm -------------------------
def init_user_exam_table() -> None:
    with get_saved_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS user_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            pairs_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")


def get_user_exams():
    init_user_exam_table()
    with get_saved_db() as conn:
        rows = conn.execute(
            "SELECT id, exam_key, title, pairs_json, created_at, updated_at FROM user_exams ORDER BY id"
        ).fetchall()
    result = []
    for row in rows:
        try:
            pairs = json.loads(row["pairs_json"])
        except (TypeError, json.JSONDecodeError):
            pairs = []
        result.append({**dict(row), "pairs": pairs if isinstance(pairs, list) else []})
    return result


def create_user_exam(title: str, first_kr: str, first_vi: str) -> str:
    title = title.strip()
    first_kr, first_vi = first_kr.strip(), first_vi.strip()
    if not title or not first_kr or not first_vi:
        raise ValueError("Bạn cần nhập tên đề và ít nhất một cặp câu Hàn–Việt.")
    exam_key = "Đề tự thêm – " + title
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_saved_db() as conn:
        existing = conn.execute("SELECT 1 FROM user_exams WHERE exam_key = ?", (exam_key,)).fetchone()
        if existing or exam_key in EXAM_DATA:
            raise ValueError("Tên đề này đã tồn tại. Hãy đặt tên khác để tránh trùng đề.")
        conn.execute(
            "INSERT INTO user_exams (exam_key, title, pairs_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (exam_key, title, json.dumps([[first_kr, first_vi]], ensure_ascii=False), now, now),
        )
    return exam_key


def add_pair_to_user_exam(exam_id: int, korean: str, vietnamese: str) -> None:
    korean, vietnamese = korean.strip(), vietnamese.strip()
    if not korean or not vietnamese:
        raise ValueError("Bạn cần nhập đủ câu tiếng Hàn và bản dịch tiếng Việt.")
    with get_saved_db() as conn:
        row = conn.execute("SELECT pairs_json FROM user_exams WHERE id = ?", (int(exam_id),)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy đề cần bổ sung.")
        pairs = json.loads(row["pairs_json"])
        if [korean, vietnamese] in pairs:
            raise ValueError("Cặp câu này đã có trong đề.")
        pairs.append([korean, vietnamese])
        conn.execute(
            "UPDATE user_exams SET pairs_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(pairs, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(exam_id)),
        )


def delete_user_exam(exam_id: int) -> None:
    with get_saved_db() as conn:
        conn.execute("DELETE FROM user_exams WHERE id = ?", (int(exam_id),))


def update_pair_in_user_exam(exam_id: int, pair_index: int, korean: str, vietnamese: str) -> None:
    korean, vietnamese = korean.strip(), vietnamese.strip()
    if not korean or not vietnamese:
        raise ValueError("Không được để trống câu tiếng Hàn hoặc bản dịch tiếng Việt.")
    with get_saved_db() as conn:
        row = conn.execute("SELECT pairs_json FROM user_exams WHERE id = ?", (int(exam_id),)).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy đề cần chỉnh sửa.")
        pairs = json.loads(row["pairs_json"])
        if not 0 <= pair_index < len(pairs):
            raise ValueError("Không tìm thấy câu cần chỉnh sửa.")
        pairs[pair_index] = [korean, vietnamese]
        conn.execute(
            "UPDATE user_exams SET pairs_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(pairs, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(exam_id)),
        )


def delete_pair_from_user_exam(exam_id: int, pair_index: int) -> None:
    with get_saved_db() as conn:
        row = conn.execute("SELECT pairs_json FROM user_exams WHERE id = ?", (int(exam_id),)).fetchone()
        if row is None:
            return
        pairs = json.loads(row["pairs_json"])
        if 0 <= pair_index < len(pairs):
            pairs.pop(pair_index)
            conn.execute(
                "UPDATE user_exams SET pairs_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(pairs, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(exam_id)),
            )


def import_user_exams(records) -> int:
    added = 0
    for item in records:
        title = str(item.get("title", "")).strip()
        pairs = item.get("pairs", [])
        if not title or not isinstance(pairs, list):
            continue
        valid_pairs = []
        for pair in pairs:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                kr, vi = str(pair[0]).strip(), str(pair[1]).strip()
            elif isinstance(pair, dict):
                kr = str(pair.get("kr", pair.get("korean", ""))).strip()
                vi = str(pair.get("vi", pair.get("vietnamese", ""))).strip()
            else:
                continue
            if kr and vi and [kr, vi] not in valid_pairs:
                valid_pairs.append([kr, vi])
        if not valid_pairs:
            continue
        key = "Đề tự thêm – " + title
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_saved_db() as conn:
            if key in EXAM_DATA or conn.execute("SELECT 1 FROM user_exams WHERE exam_key = ?", (key,)).fetchone():
                continue
            conn.execute(
                "INSERT INTO user_exams (exam_key, title, pairs_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (key, title, json.dumps(valid_pairs, ensure_ascii=False), now, now),
            )
            added += 1
    return added


init_user_exam_table()


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

    "Đề mẫu 1 – Các mối quan hệ giữa người với người": {
        "title": "Tầm quan trọng, khó khăn và phương pháp xây dựng mối quan hệ hài hòa",
        "kr_vi": make_pairs([
            ("인간은 사회적인 존재로 누구나 다른 사람들과 교류하며 살아가게 된다.", "Con người là những sinh vật mang tính xã hội, vì vậy ai cũng sống bằng cách giao lưu, tương tác với những người khác."),
            ("그래서 원만한 인간관계를 맺는 것이 중요하다.", "Vì vậy, việc xây dựng các mối quan hệ hài hòa với mọi người là điều quan trọng."),
            ("예를 들면 직장에서 동료들과 원만한 관계를 맺지 못하면 스트레스를 받게 되고 일하기가 힘들어질 수 있다.", "Ví dụ, nếu không thể xây dựng mối quan hệ tốt đẹp với đồng nghiệp tại nơi làm việc, chúng ta sẽ bị căng thẳng và công việc có thể trở nên khó khăn hơn."),
            ("이에 반해 다른 사람들과의 관계가 원만하면 서로 도움을 주고받을 수 있으므로 일도 잘 되고 자기 발전에도 도움이 된다.", "Ngược lại, nếu có mối quan hệ hòa thuận với những người khác, chúng ta có thể giúp đỡ lẫn nhau, nhờ đó công việc cũng diễn ra thuận lợi và điều này còn có ích cho sự phát triển của bản thân."),
            ("이렇듯 인간관계는 우리 생활에 미치는 영향이 크다는 점에서 아주 중요하다.", "Như vậy, các mối quan hệ giữa người với người vô cùng quan trọng bởi chúng có ảnh hưởng lớn đến cuộc sống của chúng ta."),
            ("이처럼 원만한 관계를 맺는 일은 아주 중요하지만 이는 쉬운 일이 아니다.", "Như đã nói, việc xây dựng các mối quan hệ hài hòa rất quan trọng, nhưng đây không phải là một việc dễ dàng."),
            ("그 이유로는 두 가지를 들 수 있다.", "Có thể kể ra hai nguyên nhân dẫn đến điều đó."),
            ("첫째, 성격 및 가치관의 차이로 인해 사람마다 생활 방식에 차이가 있다.", "Thứ nhất, do sự khác biệt về tính cách và quan điểm giá trị nên mỗi người có một lối sống khác nhau."),
            ("그 차이를 받아들이지 못하면 관계를 유지하기 어렵다.", "Nếu không thể chấp nhận những khác biệt đó thì sẽ khó duy trì được mối quan hệ."),
            ("둘째, 이기적인 태도에도 그 원인이 있다.", "Thứ hai, thái độ ích kỷ cũng là một nguyên nhân dẫn đến vấn đề này."),
            ("어떤 이익을 얻기 위해 관계를 맺으려고 하거나 만날 때마다 자기중심적으로 행동하면 상대방에게 피해를 끼치거나 마음의 상처를 주게 된다.", "Nếu cố gắng xây dựng mối quan hệ chỉ để đạt được một lợi ích nào đó, hoặc mỗi khi gặp nhau lại hành động theo hướng chỉ nghĩ đến bản thân, chúng ta sẽ gây thiệt hại cho đối phương hoặc khiến họ bị tổn thương về mặt tinh thần."),
            ("따라서 원만한 인간관계를 맺기 위해서는 우선 상대방을 이해하고 존중하고자 노력해야 한다.", "Do đó, để xây dựng các mối quan hệ hài hòa, trước tiên chúng ta cần nỗ lực thấu hiểu và tôn trọng đối phương."),
            ("자신과 생각이 다르다고 해서 타인을 쉽게 비난하거나 판단하면 안 된다.", "Không nên dễ dàng chỉ trích hoặc phán xét người khác chỉ vì họ có suy nghĩ khác với mình."),
            ("또한 상대방을 진실한 마음으로 대하는 것이 중요하다.", "Ngoài ra, việc đối xử với đối phương bằng tấm lòng chân thành cũng rất quan trọng."),
            ("자신의 이익과 필요에 따라 관계를 맺으려고 하거나 도움만 받으려고 하면 결코 원만한 관계를 유지할 수 없을 것이다.", "Nếu cố gắng xây dựng mối quan hệ dựa trên lợi ích và nhu cầu của bản thân, hoặc chỉ muốn nhận sự giúp đỡ từ người khác thì chắc chắn sẽ không thể duy trì được một mối quan hệ hài hòa."),
        ]),
    },
    "Đề mẫu 2 – Sức khỏe": {
        "title": "Sự quan tâm đến sức khỏe, khó khăn khi mất sức khỏe và phương pháp duy trì sức khỏe",
        "kr_vi": make_pairs([
            ("건강에 대한 사람들의 관심이 갈수록 커지고 있다.", "Sự quan tâm của mọi người đối với sức khỏe đang ngày càng tăng lên."),
            ("삶의 조건들이 점점 나빠지고 있어서 건강을 잃을 위험도 높아지고 있기 때문이다.", "Bởi vì các điều kiện sống ngày càng trở nên xấu đi, khiến nguy cơ mất đi sức khỏe cũng tăng lên."),
            ("오염된 환경과 심한 스트레스 속에서 살아가다 보니 건강하게 사는 일이 더 중요해진 것이다.", "Do phải sống trong môi trường ô nhiễm và tình trạng căng thẳng nghiêm trọng nên việc sống khỏe mạnh trở nên quan trọng hơn."),
            ("또한 아무리 의학 기술이 발달했다 하더라도 건강을 잃으면 회복하는 데 시간과 비용이 많이 들기 때문에 건강을 지키는 것을 최우선으로 생각할 수밖에 없게 되었다.", "Hơn nữa, dù công nghệ y học có phát triển đến đâu đi chăng nữa, một khi mất đi sức khỏe thì việc hồi phục cũng đòi hỏi rất nhiều thời gian và chi phí. Vì vậy, chúng ta không còn cách nào khác ngoài việc xem bảo vệ sức khỏe là ưu tiên hàng đầu."),
            ("건강을 잃으면 우리는 경제적, 심리적으로 어려움을 겪게 된다.", "Khi mất đi sức khỏe, chúng ta sẽ phải đối mặt với những khó khăn cả về kinh tế lẫn tâm lý."),
            ("먼저 경제적으로는 치료가 어려운 큰 병에 걸릴 경우 병원비 부담이 커진다.", "Trước hết, về mặt kinh tế, nếu mắc phải căn bệnh nghiêm trọng khó chữa trị thì gánh nặng viện phí sẽ tăng lên."),
            ("그래서 예상하지 못한 재정적 어려움에 빠질 수 있다.", "Vì vậy, chúng ta có thể rơi vào những khó khăn tài chính ngoài dự kiến."),
            ("또한 심리적으로도 병에 걸리면 할 수 없는 일이 많아져서 크게 위축될 수 있다.", "Ngoài ra, về mặt tâm lý, khi mắc bệnh, những việc chúng ta không thể làm sẽ tăng lên, khiến chúng ta trở nên mặc cảm và mất tự tin rất nhiều."),
            ("특히 투병 생활이 길어질수록 불안감도 커지고 자신을 돌봐주는 가족들에게도 미안한 마음이 들어서 삶의 여유를 느끼기 어렵게 된다.", "Đặc biệt, thời gian chống chọi với bệnh tật càng kéo dài thì cảm giác bất an càng tăng lên. Đồng thời, chúng ta cũng cảm thấy có lỗi với những người thân trong gia đình đang chăm sóc mình, khiến bản thân khó có thể cảm nhận được sự thảnh thơi trong cuộc sống."),
            ("그러므로 건강을 유지하기 위해서는 우선 자신만의 스트레스 해소 방법이 있어야 한다.", "Vì vậy, để duy trì sức khỏe, trước tiên mỗi người cần có phương pháp giải tỏa căng thẳng của riêng mình."),
            ("스트레스는 현대인들이 앓는 질병의 근원으로 손꼽히므로 충분한 휴식과 적절한 여가 활동을 통해 스트레스를 제때 풀어주는 것이 중요하다.", "Vì căng thẳng được xem là một trong những nguyên nhân chính gây ra các căn bệnh mà người hiện đại mắc phải, nên việc giải tỏa căng thẳng kịp thời thông qua nghỉ ngơi đầy đủ và các hoạt động giải trí phù hợp là rất quan trọng."),
            ("또한 평소 규칙적인 생활을 하는 것이 건강에 좋다.", "Ngoài ra, duy trì lối sống điều độ trong sinh hoạt hằng ngày cũng rất tốt cho sức khỏe."),
            ("꾸준히 운동하고 충분히 잠을 자야 한다.", "Chúng ta cần kiên trì tập thể dục và ngủ đủ giấc."),
            ("마지막으로 바른 식습관을 가져야 한다.", "Cuối cùng, chúng ta cần hình thành thói quen ăn uống lành mạnh."),
            ("야식과 과식을 피하고 채소나 과일 등을 자주 챙겨 먹는 것이 도움이 될 것이다.", "Tránh ăn đêm và ăn quá nhiều, đồng thời thường xuyên bổ sung rau xanh, trái cây và những thực phẩm tương tự sẽ có ích cho sức khỏe."),
        ]),
    },
    "Đề mẫu 3 – Năng lực hợp tác": {
        "title": "Tầm quan trọng, khó khăn và phương pháp hợp tác hiệu quả",
        "kr_vi": make_pairs([
            ("오늘날 많은 기업에서는 인재의 조건 중 하나로 협업 능력을 손꼽는다.", "Ngày nay, nhiều doanh nghiệp xem năng lực hợp tác là một trong những tiêu chí cần có ở nhân tài."),
            ("사람마다 가진 능력이 다르기 때문에 각자 잘하는 분야를 맡아서 일을 나누어 하는 것이 더욱 효율적이기 때문이다.", "Bởi vì năng lực của mỗi người khác nhau, nên việc mỗi người đảm nhận lĩnh vực mình làm tốt và phân chia công việc để thực hiện sẽ hiệu quả hơn."),
            ("이렇게 하면 혼자서 일을 하는 것보다 일을 처리하는 속도도 빨라지고 더 좋은 성과를 얻을 수도 있다.", "Nếu làm như vậy, so với việc làm một mình, tốc độ xử lý công việc sẽ nhanh hơn và chúng ta cũng có thể đạt được kết quả tốt hơn."),
            ("서로 부족함을 채워주고 때로는 자극을 주고받으면서 시너지 효과가 생기기 때문이다.", "Bởi vì mọi người có thể bù đắp những thiếu sót cho nhau, đôi khi còn tạo động lực cho nhau, từ đó tạo ra hiệu ứng cộng hưởng."),
            ("그런데 효율적으로 협업을 하기란 결코 쉽지 않다.", "Tuy nhiên, để hợp tác một cách hiệu quả không phải là điều dễ dàng."),
            ("먼저 의견을 일치시키기가 어렵다.", "Trước hết, việc thống nhất ý kiến là rất khó khăn."),
            ("물론 사람마다 생각이 다르므로 의견 차이는 생길 수밖에 없다.", "Tất nhiên, vì mỗi người có suy nghĩ khác nhau nên sự khác biệt về ý kiến là điều không thể tránh khỏi."),
            ("문제는 자신의 의견만 옳다고 고집하는 경우이다.", "Vấn đề nằm ở những trường hợp chỉ khăng khăng cho rằng ý kiến của bản thân là đúng."),
            ("이는 일의 진행을 어렵게 만들고 팀워크에도 악영향을 미쳐 일의 효율성을 떨어뜨린다.", "Điều này khiến công việc khó được tiến hành, đồng thời gây ảnh hưởng tiêu cực đến tinh thần làm việc nhóm và làm giảm hiệu quả công việc."),
            ("또한 책임감이 부족한 사람이 있으면 불화가 생길 수 있다.", "Ngoài ra, nếu có người thiếu tinh thần trách nhiệm thì có thể nảy sinh bất hòa."),
            ("그 사람이 하지 못한 일을 다른 팀원들이 대신해야 하기 때문이다.", "Bởi vì những thành viên khác trong nhóm phải làm thay phần công việc mà người đó không hoàn thành được."),
            ("따라서 효율적으로 협업하기 위해서는 팀원들의 의견을 존중할 줄 알아야 한다.", "Vì vậy, để hợp tác hiệu quả, chúng ta cần biết tôn trọng ý kiến của các thành viên trong nhóm."),
            ("의견이 다를 때에는 충분한 소통을 통해 설득을 해 보고 그 후에도 의견이 좁혀지지 않는다면 다른 팀원들의 의견을 받아들일 수 있어야 한다.", "Khi có ý kiến khác nhau, trước tiên cần thử thuyết phục thông qua việc trao đổi đầy đủ. Nếu sau đó các ý kiến vẫn chưa thể đi đến thống nhất thì chúng ta cần có khả năng tiếp nhận ý kiến của những thành viên khác."),
            ("그리고 맡은 일에 책임 의식을 가지고 최선을 다해야 한다.", "Ngoài ra, cần có ý thức trách nhiệm đối với công việc được giao và cố gắng hết sức để hoàn thành công việc đó."),
            ("다른 사람에게 일을 미루거나 일의 마감 날짜를 지키지 않아서 팀 전체에 피해를 주는 일이 없도록 주의해야 할 것이다.", "Cần chú ý để không gây ảnh hưởng xấu đến cả nhóm bằng cách đùn đẩy công việc cho người khác hoặc không tuân thủ thời hạn hoàn thành công việc."),
        ]),
    },
    "Bài luyện bổ sung – Năng lực đồng cảm": {
        "title": "Tầm quan trọng, vấn đề do thiếu và phương pháp rèn luyện năng lực đồng cảm",
        "kr_vi": make_pairs([
            ("날이 갈수록 타인의 감정에 무관심하거나 공감하지 못하는 사람이 늘고 있다.", "Ngày càng có nhiều người thờ ơ hoặc không thể đồng cảm với cảm xúc của người khác."),
            ("그러나 공감 능력은 원만한 인간관계를 맺게 해 준다는 점에서 아주 중요하다.", "Tuy nhiên, năng lực đồng cảm rất quan trọng ở chỗ nó giúp chúng ta xây dựng các mối quan hệ hài hòa với người khác."),
            ("예를 들어 친구가 슬퍼할 때 공감해주지 못한다면 서로 믿고 의지하는 사이가 되기는 힘들 것이다.", "Ví dụ, nếu không thể đồng cảm khi bạn bè buồn thì sẽ khó có thể trở thành những người tin tưởng và dựa dẫm vào nhau."),
            ("또한 공감 능력이 높으면 어려운 상황에 처한 사람을 도울 수 있다.", "Ngoài ra, nếu có năng lực đồng cảm cao, chúng ta có thể giúp đỡ những người đang rơi vào hoàn cảnh khó khăn."),
            ("그 사람이 얼마나 힘든지 느낄 수 있기 때문에 자신의 일처럼 나서서 돕게 되는 것이다.", "Bởi vì có thể cảm nhận được người đó đang khó khăn đến mức nào nên chúng ta sẽ chủ động đứng ra giúp đỡ họ như thể đó là chuyện của chính mình."),
            ("이 때문에 공감 능력이 부족하면 여러 문제가 생길 수 있다.", "Vì lý do này, nếu thiếu năng lực đồng cảm thì có thể phát sinh nhiều vấn đề."),
            ("첫째 사회생활을 잘하기가 어려워질 것이다.", "Thứ nhất, việc hòa nhập và ứng xử tốt trong đời sống xã hội sẽ trở nên khó khăn hơn."),
            ("공감 능력 부족으로 다른 사람의 감정을 잘 읽지 못하고 자기중심적으로 행동하게 되기 때문이다.", "Bởi vì do thiếu khả năng đồng cảm, chúng ta không thể hiểu rõ cảm xúc của người khác và có xu hướng hành động theo cách lấy bản thân làm trung tâm."),
            ("둘째 타인의 아픔을 느끼지 못해 폭력성이 증가할 수 있다.", "Thứ hai, do không cảm nhận được nỗi đau của người khác nên tính bạo lực có thể gia tăng."),
            ("그래서 학교 폭력, 집단 따돌림 등 사회 문제가 커질 수 있다.", "Vì vậy, các vấn đề xã hội như bạo lực học đường, bắt nạt tập thể có thể trở nên nghiêm trọng hơn."),
            ("따라서 공감 능력을 기르기 위해서는 다음과 같은 노력을 할 필요가 있다.", "Vì vậy, để rèn luyện năng lực đồng cảm, chúng ta cần thực hiện những nỗ lực sau đây."),
            ("먼저 다른 사람에게 관심을 가지고 그 사람의 입장과 상황에서 생각해보는 연습을 해야 한다.", "Trước tiên, cần quan tâm đến người khác và luyện tập cách suy nghĩ từ vị trí cũng như hoàn cảnh của họ."),
            ("그리고 같은 일이 자신에게 생긴다면 어떤 느낌이 들지를 상상해보는 훈련이 필요하다.", "Ngoài ra, cần rèn luyện khả năng tưởng tượng xem bản thân sẽ cảm thấy thế nào nếu chuyện tương tự xảy ra với mình."),
            ("또 다른 방법은 문학, 영화 등 예술 작품을 많이 접하는 것이다.", "Một phương pháp khác là tiếp xúc nhiều với các tác phẩm nghệ thuật như văn học, phim ảnh."),
            ("작품 속 다양한 인물의 감정을 간접적으로 느낌으로써 공감 능력을 키울 수 있다.", "Thông qua việc gián tiếp cảm nhận cảm xúc của nhiều nhân vật khác nhau trong tác phẩm, chúng ta có thể nâng cao năng lực đồng cảm."),
        ]),
    },
    "Đề mẫu 4 – Văn hóa truyền thống": {
        "title": "Giá trị, nguyên nhân khó bảo tồn và phương pháp kế thừa văn hóa truyền thống",
        "kr_vi": make_pairs([
            ("나라마다 고유한 전통문화가 있다.", "Mỗi quốc gia đều có nền văn hóa truyền thống mang nét đặc trưng riêng."),
            ("그런데 오늘날에는 세계화와 산업화의 영향으로 각국의 생활 모습이 비슷해지면서 전통문화가 점점 잊혀지고 있다.", "Tuy nhiên, ngày nay, dưới ảnh hưởng của toàn cầu hóa và công nghiệp hóa, lối sống của các quốc gia ngày càng trở nên giống nhau, khiến văn hóa truyền thống dần bị lãng quên."),
            ("그러나 전통문화에는 조상들의 지혜가 담겨 있다.", "Tuy nhiên, trong văn hóa truyền thống có chứa đựng trí tuệ của tổ tiên."),
            ("가령 어른을 공경하는 예절 문화는 함께 살아가기 위한 옛 사람들의 지혜를 보여준다.", "Chẳng hạn, văn hóa lễ nghi kính trọng người lớn tuổi thể hiện trí tuệ của người xưa trong việc chung sống với nhau."),
            ("또 전통문화에는 예술적 가치가 높은 것도 많다.", "Ngoài ra, trong văn hóa truyền thống cũng có nhiều giá trị mang tính nghệ thuật cao."),
            ("세월이 아무리 흘러도 '백자'의 아름다움은 변하지 않을 것이다.", "Dù thời gian có trôi qua bao lâu thì vẻ đẹp của đồ sứ trắng vẫn sẽ không thay đổi."),
            ("이런 점에서 전통문화는 보존해야 할 가치가 있다고 생각한다.", "Xét ở những khía cạnh này, tôi cho rằng văn hóa truyền thống có giá trị cần được bảo tồn."),
            ("그럼에도 보존하기가 어려운 이유로는 두 가지를 들 수 있다.", "Mặc dù vậy, có thể kể đến hai nguyên nhân khiến việc bảo tồn văn hóa truyền thống trở nên khó khăn."),
            ("첫째 사람들의 무관심과 편견 때문이다.", "Thứ nhất, đó là do sự thờ ơ và định kiến của mọi người."),
            ("전통문화라고 하면 옛날 것이기 때문에 요즘에는 쓸모가 없고 도움이 되지 않는다고 생각하는 사람들도 많다.", "Khi nhắc đến văn hóa truyền thống, nhiều người cho rằng vì đó là những thứ thuộc về thời xưa nên ngày nay chúng không còn có ích và cũng không mang lại lợi ích gì."),
            ("둘째, 현대인의 기호와 생활 모습이 달라진 데에도 원인이 있다.", "Thứ hai, nguyên nhân còn nằm ở sự thay đổi trong sở thích và lối sống của con người hiện đại."),
            ("가령 요즘 한복은 일상복이 아니며 사람들은 판소리보다 K-pop을 더 자주 듣는다.", "Chẳng hạn, ngày nay Hanbok không còn là trang phục mặc thường ngày, và mọi người nghe nhạc K-pop thường xuyên hơn Pansori (loại hình hát kể chuyện truyền thống của Hàn Quốc)."),
            ("시대가 바뀌면서 한복은 불편하고 판소리는 내용을 알 수 없는 노래가 된 것이다.", "Cùng với sự thay đổi của thời đại, Hanbok trở thành trang phục bị xem là bất tiện, còn Pansori trở thành loại hình âm nhạc mà người nghe không hiểu được nội dung."),
            ("따라서 전통문화를 지키고 계승할 인재를 키우는 것이 중요하다.", "Vì vậy, việc đào tạo những nhân tài có khả năng gìn giữ và kế thừa văn hóa truyền thống là rất quan trọng."),
            ("이를 위해서는 시민들의 노력은 물론 정부 차원의 지원이 필요하다.", "Để làm được điều này, không chỉ cần sự nỗ lực của người dân mà còn cần sự hỗ trợ ở cấp chính phủ."),
            ("또한 뮤지컬 '난타'처럼 현대인의 기호에 맞게 전통문화를 변형해 계승하는 것도 좋은 방법 중의 하나이다.", "Ngoài ra, việc cải biến văn hóa truyền thống để kế thừa sao cho phù hợp với sở thích của người hiện đại, giống như vở nhạc kịch Nanta, cũng là một trong những phương pháp tốt."),
            ("이때 지나치게 많이 변형해서 그 가치가 떨어지지 않도록 주의한다면 더 많은 사람들이 전통문화에 관심을 가지게 될 것이다.", "Trong quá trình đó, nếu chú ý không cải biến quá nhiều đến mức làm giảm giá trị của văn hóa truyền thống thì sẽ có nhiều người quan tâm đến văn hóa truyền thống hơn."),
        ]),
    },
    "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc": {
        "title": "Lợi ích, tác động tiêu cực và phương án phát huy tính tự chủ trong công việc",
        "kr_vi": make_pairs([
            ("사회의 변화로 개인의 자율성을 중시하는 사람들이 많아졌다.", "Do sự thay đổi của xã hội, ngày càng có nhiều người coi trọng tính tự chủ của cá nhân."),
            ("이에 따라 기업에서도 유연근무제를 실시하는 등 직장 내 자율성을 높이고자 노력하고 있다.", "Theo đó, các doanh nghiệp cũng đang nỗ lực nâng cao tính tự chủ tại nơi làm việc, chẳng hạn như triển khai chế độ làm việc linh hoạt."),
            ("직장에서 개인의 자율성이 보장되면 직장 내 문화가 유연해져 개인이 창의성을 발휘할 수 있는 근무 환경이 만들어진다.", "Khi tính tự chủ của cá nhân được đảm bảo tại nơi làm việc, văn hóa công sở trở nên linh hoạt hơn, từ đó tạo ra môi trường làm việc để mỗi cá nhân phát huy khả năng sáng tạo."),
            ("또한 개인이 자신에게 적합한 근무 여건을 조성하여 일할 수 있어 일과 삶의 균형이 생긴다.", "Ngoài ra, mỗi cá nhân có thể làm việc trong điều kiện phù hợp với bản thân, nhờ đó hình thành sự cân bằng giữa công việc và cuộc sống."),
            ("이것이 구성원의 업무 효율을 높이는 데 기여하여 조직의 목표를 달성하는 데에 도움이 된다.", "Điều này góp phần nâng cao hiệu suất công việc của các thành viên, qua đó giúp tổ chức đạt được mục tiêu của mình."),
            ("그러나 직장 내 사람들이 개인의 자율성만 중시하면 부작용이 발생할 수 있다.", "Tuy nhiên, nếu những người trong môi trường công sở chỉ coi trọng tính tự chủ cá nhân thì có thể phát sinh những tác dụng phụ."),
            ("먼저, 개인이 공동의 목표보다는 자신의 입장만을 생각하다 보면 자율성이 이기주의로 변질될 수 있다.", "Trước hết, nếu mỗi cá nhân chỉ nghĩ đến lập trường của bản thân thay vì mục tiêu chung thì tính tự chủ có thể biến chất thành chủ nghĩa ích kỷ."),
            ("이러한 상황이 계속되면 책임자와 팀원 간 갈등, 세대 간 갈등이 발생할 수도 있다.", "Nếu tình trạng này tiếp diễn, xung đột giữa người phụ trách và các thành viên trong nhóm, cũng như xung đột giữa các thế hệ, có thể phát sinh."),
            ("또한 업무의 자율성이 높아져 개별적으로 일할 수 있는 환경이 익숙해지면 소통이 부재하여 합의점을 찾기 어렵고 협력을 통한 성과를 내기 어려울 수 있다.", "Ngoài ra, khi tính tự chủ trong công việc tăng lên và mọi người trở nên quen thuộc với môi trường có thể làm việc độc lập, việc giao tiếp có thể bị thiếu hụt, khiến họ khó tìm được tiếng nói chung và khó đạt được thành quả thông qua hợp tác."),
            ("이러한 문제를 해결하기 위해서는 직장 내 개개인이 자율성을 가지면서도 업무를 수행할 때는 최대한 동료와 협업하고 서로를 배려하는 마음을 가질 필요가 있다.", "Để giải quyết những vấn đề này, mỗi cá nhân tại nơi làm việc cần có tính tự chủ nhưng đồng thời cũng cần hợp tác tối đa với đồng nghiệp và biết quan tâm, nhường nhịn lẫn nhau khi thực hiện công việc."),
            ("또한 조직은 구성원의 자율성을 높이면서 조직의 목표를 성취하는 데 도움이 되는 방안을 고민해야 한다.", "Ngoài ra, tổ chức cần suy nghĩ về những phương án vừa nâng cao tính tự chủ của các thành viên, vừa giúp đạt được mục tiêu của tổ chức."),
            ("나아가 효율적인 의사소통 방안을 마련하여 구성원 간 원활한 협력이 가능하도록 해야 할 것이다.", "Hơn nữa, cần xây dựng những phương thức giao tiếp hiệu quả để sự hợp tác giữa các thành viên có thể diễn ra một cách thuận lợi."),
        ]),
    },
    "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả": {
        "title": "Nguyên nhân, tác hại của tin giả và biện pháp ngăn chặn",
        "kr_vi": make_pairs([
            ("정보 통신 기술의 발달과 소셜 미디어의 대중화로 인해 이 시대에는 누구나 쉽게 정보를 생산하고 불특정 다수와 공유할 수 있게 되었다.", "Nhờ sự phát triển của công nghệ thông tin và truyền thông cùng với sự phổ biến của mạng xã hội, trong thời đại ngày nay, bất kỳ ai cũng có thể dễ dàng tạo ra thông tin và chia sẻ thông tin đó với đông đảo người không xác định."),
            ("이는 정보를 생산하고 유통하는 매체가 신문이나 방송과 같은 전통적 미디어에서 디지털 미디어 플랫폼으로 확장되면서 가능해진 것이다.", "Điều này trở nên khả thi khi các phương tiện sản xuất và phân phối thông tin được mở rộng từ những phương tiện truyền thông truyền thống như báo chí, phát thanh và truyền hình sang các nền tảng truyền thông kỹ thuật số."),
            ("나아가 그 과정에서 경제적 가치를 창출하는 것 역시 가능해지면서 다양한 문제가 양산되고 있다.", "Hơn nữa, trong quá trình đó, việc tạo ra giá trị kinh tế cũng trở nên khả thi, kéo theo nhiều vấn đề khác nhau được sản sinh hàng loạt."),
            ("사람들의 이목을 끌기 위한 가짜 뉴스의 등장도 그 문제 중 하나이다.", "Sự xuất hiện của tin giả nhằm thu hút sự chú ý của mọi người cũng là một trong những vấn đề đó."),
            ("가짜 뉴스는 정보 수용자로 하여금 잘못된 지식과 선입견, 편협한 사고를 형성하게 한다.", "Tin giả khiến người tiếp nhận thông tin hình thành những kiến thức sai lệch, định kiến và lối suy nghĩ phiến diện."),
            ("가짜 뉴스의 소재가 되는 개인이나 기업, 단체의 경우 이미지 타격과 경제적 피해는 물론이고 사회적으로 재기가 어려울 정도로 명예가 훼손되기도 한다.", "Đối với các cá nhân, doanh nghiệp hoặc tổ chức trở thành đối tượng của tin giả, không chỉ hình ảnh bị tổn hại và thiệt hại kinh tế phát sinh mà danh dự của họ đôi khi còn bị tổn hại nghiêm trọng đến mức khó có thể khôi phục vị thế trong xã hội."),
            ("또한 가짜 뉴스는 혐오를 확산하고 사회적 불안을 야기하며 사회 구성원들의 통합을 방해한다.", "Ngoài ra, tin giả còn lan truyền sự thù ghét, gây ra bất ổn xã hội và cản trở sự đoàn kết giữa các thành viên trong xã hội."),
            ("나아가 정치 및 외교적 문제로 심화될 가능성도 있기 때문에 심각한 사회 문제라 말할 수 있다.", "Hơn nữa, vì tin giả còn có khả năng phát triển thành những vấn đề chính trị và ngoại giao nên có thể nói đây là một vấn đề xã hội nghiêm trọng."),
            ("가짜 뉴스를 근절하기 위해서는 우선 제도적으로 가짜 뉴스의 생산과 유통이 불법적 행위임을 규정하고, 가짜 뉴스 단속을 위한 기구를 만들어 가짜 뉴스가 확산되지 않도록 규제를 강화해야 한다.", "Để loại bỏ tin giả, trước tiên cần quy định về mặt thể chế rằng việc sản xuất và phát tán tin giả là hành vi bất hợp pháp, đồng thời thành lập cơ quan giám sát và tăng cường quy định để tin giả không lan rộng."),
            ("또한 각종 캠페인이나 교육을 통해 가짜 뉴스의 위험성과 위법성을 알리는 것 역시 필요하다.", "Ngoài ra, cũng cần thông qua các chiến dịch và hoạt động giáo dục để nâng cao nhận thức về mức độ nguy hiểm cũng như tính bất hợp pháp của tin giả."),
            ("나아가 정보의 진위를 판단하는 기술을 개발해 가짜 뉴스가 정보 수용자에게 전달되는 것을 방지하는 것도 좋은 방법일 것이다.", "Hơn nữa, phát triển công nghệ có thể xác định tính xác thực của thông tin để ngăn tin giả truyền đến người tiếp nhận cũng sẽ là một biện pháp tốt."),
        ]),
    },
    "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số": {
        "title": "Thực trạng, nguyên nhân và giải pháp khắc phục tình trạng số hóa gây bất bình đẳng",
        "kr_vi": make_pairs([
            ("과학 기술이 빠르게 발달하면서 과거와는 달리 일상생활에서 디지털 기술의 활용이 일반화되고 있다.", "Cùng với sự phát triển nhanh chóng của khoa học kỹ thuật, khác với trước đây, việc ứng dụng công nghệ kỹ thuật số trong đời sống hằng ngày đang dần trở nên phổ biến."),
            ("식당에서는 대면을 하지 않아도 키오스크로 음식을 주문할 수 있게 되었고 관공서나 금융 기관을 직접 방문하지 않아도 컴퓨터나 스마트폰으로 서비스를 이용할 수 있게 되었다.", "Tại các nhà hàng, mọi người đã có thể gọi món bằng máy kiosk mà không cần tiếp xúc trực tiếp với nhân viên; không cần đến trực tiếp cơ quan hành chính hoặc tổ chức tài chính vẫn có thể sử dụng dịch vụ qua máy tính hoặc điện thoại thông minh."),
            ("또한 병원의 진료 예약이나 공연, 기차표 등의 예매도 인터넷으로 손쉽게 할 수 있다.", "Ngoài ra, việc đặt lịch khám bệnh, đặt vé biểu diễn hoặc vé tàu cũng có thể dễ dàng thực hiện qua Internet."),
            ("그러나 이러한 편의를 모든 사람들이 동일하게 누리는 것은 아니다.", "Tuy nhiên, không phải tất cả mọi người đều được hưởng những tiện ích này một cách bình đẳng."),
            ("고령층의 경우 디지털 기기가 익숙하지 않아서 금융·의료 서비스를 이용하는 데에 어려움이 따른다.", "Đối với người cao tuổi, do không quen sử dụng các thiết bị kỹ thuật số nên họ gặp khó khăn khi sử dụng dịch vụ tài chính và y tế."),
            ("그리고 경제적인 여건이 되지 않아 디지털 기기를 구입하거나 사용하는 것이 부담이 되는 사람들도 있을 것이다.", "Ngoài ra, cũng có những người do điều kiện kinh tế không cho phép nên việc mua hoặc sử dụng thiết bị kỹ thuật số trở thành một gánh nặng."),
            ("또한 디지털 인프라가 부족한 지역에서 거주하는 사람들은 온라인으로 제공 받을 수 있는 서비스가 제한적이다.", "Bên cạnh đó, những người sống ở khu vực thiếu cơ sở hạ tầng kỹ thuật số bị hạn chế trong việc tiếp cận các dịch vụ được cung cấp trực tuyến."),
            ("이러한 문제를 해결하기 위해서는 개인과 사회 모두가 노력해야 한다.", "Để giải quyết những vấn đề này, cả cá nhân và xã hội đều cần nỗ lực."),
            ("개인의 경우 처음에는 익숙하지 않더라도 변화하는 시대에 뒤처지지 않게 디지털 기기의 사용법을 익히도록 해야 한다.", "Đối với mỗi cá nhân, dù ban đầu chưa quen, vẫn cần học cách sử dụng các thiết bị kỹ thuật số để không bị tụt hậu trước sự thay đổi của thời đại."),
            ("이를 위해서 정부에서는 디지털 소외 계층을 위한 지원 정책을 마련해서 모든 국민들이 일상에서 디지털 기술을 활용할 수 있게 하여 소외되는 사람들이 없도록 해야 한다.", "Để làm được điều này, chính phủ cần xây dựng các chính sách hỗ trợ dành cho những nhóm người bị gạt ra bên lề trong xã hội số, giúp tất cả người dân có thể ứng dụng công nghệ kỹ thuật số trong cuộc sống hằng ngày, qua đó không để bất kỳ ai bị bỏ lại phía sau."),
            ("그리고 디지털 인프라를 확충하여 지역과 계층에 무관하게 많은 사람들이 디지털 기술 발달의 혜택을 고르게 누릴 수 있도록 해야 한다.", "Ngoài ra, cần mở rộng cơ sở hạ tầng kỹ thuật số để đông đảo mọi người được hưởng lợi ích từ sự phát triển công nghệ kỹ thuật số một cách bình đẳng, không phân biệt khu vực hay tầng lớp xã hội."),
        ]),
    },
    "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường": {
        "title": "Nguyên nhân ô nhiễm môi trường: đồ dùng một lần và công nghiệp hóa, đô thị hóa",
        "kr_vi": make_pairs([
            ("환경오염 문제는 어제오늘만의 일이 아니다.", "Vấn đề ô nhiễm môi trường không phải là chuyện mới xảy ra ngày một ngày hai."),
            ("그러나 날이 갈수록 그 문제가 더욱 심각해지고 있다.", "Tuy nhiên, vấn đề đó đang ngày càng trở nên nghiêm trọng hơn."),
            ("그 이유로는 일회용품 사용이 증가한 것을 들 수 있다.", "Một trong những nguyên nhân có thể kể đến là việc sử dụng đồ dùng một lần ngày càng gia tăng."),
            ("이는 인간이 환경보호보다는 편리함만 추구했기 때문이다.", "Đó là bởi con người chỉ theo đuổi sự tiện lợi thay vì bảo vệ môi trường."),
            ("생활 속에서 편리하게 사용하는 비닐봉지, 일회용 컵 등은 음식물과는 달리 시간이 지나도 잘 썩지 않는다.", "Những vật dụng tiện lợi trong đời sống như túi ni-lông và cốc dùng một lần, khác với thức ăn, không dễ phân hủy dù thời gian trôi qua."),
            ("그래서 많은 양이 쌓이게 되어 환경을 오염시키는 것이다.", "Vì vậy, chúng tích tụ với số lượng lớn và gây ô nhiễm môi trường."),
            ("또한 급격한 산업화, 도시화 때문이다.", "Một nguyên nhân khác là quá trình công nghiệp hóa và đô thị hóa diễn ra nhanh chóng."),
            ("예를 들어 산업 시설 및 주거 단지가 만들어지면서 수많은 숲이 사라지고 생활 쓰레기와 산업 폐수가 바다를 오염시켰다.", "Ví dụ, khi các cơ sở công nghiệp và khu dân cư được xây dựng, nhiều cánh rừng đã biến mất, còn rác thải sinh hoạt và nước thải công nghiệp làm ô nhiễm biển."),
            ("즉 개발이 환경오염을 심화시키고 있는 것이다.", "Nói cách khác, quá trình phát triển đang làm trầm trọng thêm tình trạng ô nhiễm môi trường."),
        ]),
    },
    "Bài luyện bổ sung – Sự thờ ơ của con người hiện đại": {
        "title": "Nguyên nhân khiến con người hiện đại ít quan tâm đến người khác",
        "kr_vi": make_pairs([
            ("현대인들은 다른 사람에게 그리 관심을 가지지 않는 경향이 있다.", "Người hiện đại có xu hướng không mấy quan tâm đến người khác."),
            ("이러한 무관심의 원인으로는 먼저 개인주의의 심화를 들 수 있다.", "Trước tiên, có thể kể đến sự gia tăng của chủ nghĩa cá nhân như một nguyên nhân dẫn đến sự thờ ơ này."),
            ("공동의 가치보다는 개인의 성공을 중요하게 생각하면서 다른 사람의 일에 큰 관심을 갖지 않게 된 것이다.", "Do coi trọng thành công cá nhân hơn những giá trị chung nên con người đã trở nên ít quan tâm đến chuyện của người khác."),
            ("또한 많은 사람들이 타인에 대한 믿음을 잃었기 때문이다.", "Ngoài ra, đó còn là bởi vì nhiều người đã mất niềm tin vào người khác."),
            ("이는 갈수록 자신의 목적을 이루기 위한 수단으로 사람을 대하는 사람들이 많아진 탓이다.", "Điều này là do ngày càng có nhiều người đối xử với người khác như một phương tiện để đạt được mục đích của bản thân."),
        ]),
    },

    "Đề mẫu số 6 – Du lịch: lý do, lợi ích và lưu ý": {
        "title": "Tính cần thiết của du lịch và những điều cần chú ý",
        "kr_vi": make_pairs([
            ("누구나 한 번쯤 여행을 떠나고 싶다는 생각을 해본 적이 있을 것이다.", "Có lẽ ai cũng đã từng ít nhất một lần nghĩ rằng mình muốn đi du lịch."),
            ("반복되는 일상생활이 무료하게 느껴질 때, 바쁜 업무와 복잡한 인간관계로 인해 몸과 마음이 지치고 힘들 때 우리는 여행을 떠나고 싶어 한다.", "Khi cảm thấy cuộc sống thường nhật lặp đi lặp lại thật nhàm chán, hoặc khi cơ thể và tinh thần trở nên mệt mỏi vì công việc bận rộn và những mối quan hệ phức tạp, chúng ta thường muốn đi du lịch."),
            ("휴식과 기분전환을 위해 여행이 필요해진 것이다.", "Đó là bởi vì chúng ta cần đi du lịch để nghỉ ngơi và thay đổi tâm trạng."),
            ("이뿐만이 아니다.", "Không chỉ có vậy."),
            ("새로운 경험을 해보고 싶을 때, 다른 문화와 세계에 대한 호기심이 생길 때도 여행은 그러한 욕구를 만족시킬 수 있는 좋은 방법이 된다.", "Khi muốn có những trải nghiệm mới hoặc khi nảy sinh sự tò mò về những nền văn hóa và thế giới khác, du lịch cũng trở thành một phương pháp tốt có thể đáp ứng những mong muốn đó."),
            ("여행을 통해 우리가 얻을 수 있는 효과도 다양하다.", "Những lợi ích mà chúng ta có thể đạt được thông qua du lịch cũng rất đa dạng."),
            ("먼저 여행을 하면 스트레스를 해소하고 마음의 여유를 찾을 수 있다.", "Trước tiên, khi đi du lịch, chúng ta có thể giải tỏa căng thẳng và tìm lại sự thư thái trong tâm hồn."),
            ("잠깐이라도 일상생활에서 벗어날 수 있기 때문이다.", "Bởi vì chúng ta có thể thoát khỏi cuộc sống thường nhật, dù chỉ trong một khoảng thời gian ngắn."),
            ("또한 자기 자신과 삶에 대해 깊이 생각해볼 수 있다.", "Ngoài ra, chúng ta có thể suy nghĩ sâu sắc hơn về bản thân và cuộc sống của mình."),
            ("평소 바쁘게 살다 보면 그러한 시간을 가지기가 어려울 때가 많지만 여행을 떠나 다양한 사람을 만나거나 낯선 환경 속에서 혼자만의 시간을 가지게 되면 좀 더 객관적으로 자신을 되돌아보게 된다.", "Trong cuộc sống thường ngày, khi luôn bận rộn, chúng ta thường khó có được khoảng thời gian như vậy. Tuy nhiên, khi đi du lịch, được gặp gỡ nhiều người khác nhau hoặc có khoảng thời gian riêng trong một môi trường xa lạ, chúng ta sẽ có thể nhìn nhận lại bản thân một cách khách quan hơn."),
            ("따라서 여행할 때는 열린 마음을 가져야 한다.", "Vì vậy, khi đi du lịch, chúng ta cần có một tâm thế cởi mở."),
            ("그렇지 않으면 새로운 경험과 생각을 할 수 있는 기회를 놓칠 수 있다.", "Nếu không, chúng ta có thể bỏ lỡ cơ hội có được những trải nghiệm và suy nghĩ mới mẻ."),
            ("또 안전과 건강에 주의해야 한다.", "Ngoài ra, chúng ta cần chú ý đến vấn đề an toàn và sức khỏe."),
            ("환경의 변화로 질병에 걸리거나 사고로 다치기라도 하면 여행을 충분히 즐길 수 없기 때문이다.", "Bởi vì nếu mắc bệnh do sự thay đổi của môi trường hoặc chẳng may bị thương do tai nạn thì chúng ta sẽ không thể tận hưởng chuyến du lịch một cách trọn vẹn."),
            ("그러므로 여행을 할 때는 마음으로 새로운 문화를 충분히 즐기되 안전과 건강에도 신경을 써야 할 것이다.", "Vì vậy, khi đi du lịch, chúng ta nên tận hưởng trọn vẹn những nền văn hóa mới bằng cả tâm hồn, đồng thời cũng phải chú ý đến vấn đề an toàn và sức khỏe."),
        ]),
    },
    "Đề mẫu số 7 – Du lịch: lợi ích và thái độ cần có": {
        "title": "Du lịch giúp giải tỏa căng thẳng, tích lũy kinh nghiệm và mở rộng hiểu biết",
        "kr_vi": make_pairs([
            ("요즈음 SNS나 책을 보면 '여행'을 주제로 한 이야기가 눈에 띄게 많아졌다.", "Dạo gần đây, khi xem mạng xã hội hoặc sách, chúng ta có thể dễ dàng nhận thấy những câu chuyện lấy chủ đề “du lịch” xuất hiện ngày càng nhiều."),
            ("많은 업무, 복잡한 인간관계 등에 지친 사람들이 피로감을 해소하기 위해 여행에 관심을 많이 가지게 된 것이다.", "Đó là bởi vì những người mệt mỏi vì công việc bận rộn, các mối quan hệ phức tạp và những điều tương tự ngày càng quan tâm nhiều hơn đến du lịch để giải tỏa cảm giác mệt mỏi."),
            ("실제로 여행은 스트레스를 해소하고 기분전환을 하게 해 준다.", "Trên thực tế, du lịch giúp chúng ta giải tỏa căng thẳng và thay đổi tâm trạng."),
            ("잠깐이나마 여행을 떠나면 반복되는 일상에서 벗어나서 새로운 경험을 하거나 휴식을 취할 수 있기 때문이다.", "Bởi vì chỉ cần đi du lịch dù trong một khoảng thời gian ngắn, chúng ta cũng có thể thoát khỏi cuộc sống thường nhật lặp đi lặp lại, trải nghiệm những điều mới mẻ hoặc nghỉ ngơi thư giãn."),
            ("이로써 다시 일상을 살아갈 힘을 얻게 되는 것이다.", "Nhờ đó, chúng ta có được năng lượng để tiếp tục cuộc sống thường ngày."),
            ("또한 우리는 여행을 통해 풍부한 경험을 쌓을 수 있다.", "Ngoài ra, chúng ta có thể tích lũy nhiều kinh nghiệm phong phú thông qua du lịch."),
            ("가령 해외여행을 떠나면 세계 각지에서 온 사람들을 만나 대화할 기회도 생기고 다른 나라의 음식이나 문화도 접해볼 수 있다.", "Chẳng hạn, khi đi du lịch nước ngoài, chúng ta có cơ hội gặp gỡ và trò chuyện với những người đến từ khắp nơi trên thế giới, đồng thời cũng có thể tiếp xúc với ẩm thực và văn hóa của các quốc gia khác."),
            ("이러한 경험은 생각의 폭을 넓혀 주고 다양한 문화를 이해하는 데에도 도움을 준다.", "Những trải nghiệm này giúp mở rộng tư duy và cũng hỗ trợ chúng ta trong việc hiểu biết các nền văn hóa đa dạng."),
            ("물론 여행 중에 예상하지 못한 일이 생겨서 힘들 때도 있지만 잘 대처하면 그것이 경험으로 쌓여 자신감도 생기게 된다.", "Tất nhiên, đôi khi trong chuyến du lịch cũng xảy ra những chuyện ngoài dự kiến khiến chúng ta gặp khó khăn. Tuy nhiên, nếu xử lý tốt thì những trải nghiệm đó sẽ được tích lũy thành kinh nghiệm và giúp chúng ta có thêm sự tự tin."),
            ("이렇듯 여행에는 장점이 많기 때문에 우리에게 꼭 필요한 것이라고 할 수 있다.", "Như vậy, vì du lịch có nhiều ưu điểm nên có thể nói rằng đây là điều thực sự cần thiết đối với chúng ta."),
            ("따라서 여행할 때는 열린 태도를 가지는 것이 중요하다.", "Vì vậy, khi đi du lịch, việc có thái độ cởi mở là rất quan trọng."),
            ("현지 사람들의 삶의 방식과 문화를 있는 그대로 받아들이는 마음이 필요하다.", "Chúng ta cần có tinh thần đón nhận nguyên vẹn lối sống và văn hóa của người dân địa phương."),
            ("비판하거나 거부하면 즐거운 여행을 할 수 없다.", "Nếu chỉ trích hoặc từ chối chấp nhận những điều đó thì chúng ta không thể có một chuyến du lịch vui vẻ."),
            ("그리고 현지 문화와 관습을 잘 알아보고 실수하지 않도록 조심해야 한다.", "Ngoài ra, chúng ta cần tìm hiểu kỹ văn hóa và phong tục địa phương, đồng thời cẩn thận để không mắc sai lầm."),
            ("그렇지 않으면 현지인들에게 오해를 살 수 있고 반대로 피해를 끼칠 수도 있다.", "Nếu không, chúng ta có thể khiến người dân địa phương hiểu lầm, thậm chí ngược lại còn có thể gây phiền toái hoặc thiệt hại cho họ."),
        ]),
    },
    "Đề mẫu số 8 – Tư duy sáng tạo": {
        "title": "Tầm quan trọng, tác dụng và phương pháp rèn luyện tư duy sáng tạo",
        "kr_vi": make_pairs([
            ("현대 사회에서 창의적인 사고 능력은 인재가 갖추어야 할 필수 조건이라고 할 수 있다.", "Trong xã hội hiện đại, năng lực tư duy sáng tạo có thể được xem là một điều kiện thiết yếu mà nhân tài cần phải có."),
            ("정보화 사회에서는 지식과 정보가 산업 발달의 가장 중요한 요소이기 때문에 남들과 똑같은 지식이나 아이디어만으로는 성공하기 어렵기 때문이다.", "Bởi vì trong xã hội thông tin, kiến thức và thông tin là những yếu tố quan trọng nhất đối với sự phát triển của ngành công nghiệp, nên chỉ với kiến thức hay ý tưởng giống người khác thì rất khó thành công."),
            ("예를 들면 기업의 경우 창의적인 사고를 통해 새로운 제품과 서비스를 제공하지 못하면 소비자들을 만족시키지 못해 경쟁에서 뒤처질 수 있다.", "Ví dụ, đối với doanh nghiệp, nếu không thể cung cấp những sản phẩm và dịch vụ mới thông qua tư duy sáng tạo thì sẽ không thể làm hài lòng người tiêu dùng và có thể bị tụt hậu trong cuộc cạnh tranh."),
            ("또한 창의적인 사고 능력은 문제를 효과적으로 해결하는 데에도 도움이 된다.", "Ngoài ra, năng lực tư duy sáng tạo cũng giúp giải quyết vấn đề một cách hiệu quả."),
            ("창의적인 사고 능력이 있으면 보다 다양한 관점에서 문제에 접근할 수 있기 때문이다.", "Bởi vì nếu có năng lực tư duy sáng tạo, chúng ta có thể tiếp cận vấn đề từ nhiều góc độ đa dạng hơn."),
            ("그뿐만 아니라 창의적인 사고로 새로운 제품을 만들면 우리 생활은 더욱 편리해질 수 있다.", "Không chỉ vậy, nếu tạo ra những sản phẩm mới bằng tư duy sáng tạo thì cuộc sống của chúng ta có thể trở nên tiện lợi hơn."),
            ("가령 스티브 잡스가 발전시킨 스마트폰은 우리의 생활을 크게 바꾸어 놓았다.", "Chẳng hạn, điện thoại thông minh được Steve Jobs phát triển đã làm thay đổi đáng kể cuộc sống của chúng ta."),
            ("이처럼 창의적인 사고는 다양한 분야에서 새로운 방식으로 세상을 바꾸고 있다.", "Như vậy, tư duy sáng tạo đang thay đổi thế giới theo những phương thức mới trong nhiều lĩnh vực khác nhau."),
            ("그러므로 창의적인 사고를 하기 위해서는 먼저 고정관념을 깨는 것이 중요하다.", "Vì vậy, để có tư duy sáng tạo, trước tiên việc phá bỏ những định kiến và lối suy nghĩ cố hữu là rất quan trọng."),
            ("가령 무선 이어폰은 상상하기 힘들었지만 출시된 후로 큰 인기를 얻고 있다.", "Chẳng hạn, trước đây thật khó tưởng tượng ra tai nghe không dây, nhưng kể từ khi được ra mắt, sản phẩm này đã nhận được sự yêu thích rất lớn."),
            ("이러한 의미에서 고정관념에서 벗어나 무엇이든지 새롭게 보려는 노력을 하지 않으면 안 된다.", "Theo ý nghĩa đó, chúng ta nhất định phải nỗ lực thoát khỏi những lối suy nghĩ cố hữu và thử nhìn nhận mọi thứ theo một cách mới mẻ."),
            ("또한 평소 사물을 자세히 관찰하고 떠오르는 생각이 있을 때마다 메모하는 습관을 기르는 것도 도움이 될 것이다.", "Ngoài ra, việc hình thành thói quen quan sát sự vật một cách kỹ lưỡng trong cuộc sống hằng ngày và ghi chép lại mỗi khi nảy ra ý tưởng cũng sẽ rất hữu ích."),
        ]),
    },
    "Đề mẫu số 9 – Lời xin lỗi": {
        "title": "Tầm quan trọng của lời xin lỗi và cách xin lỗi đúng đắn",
        "kr_vi": make_pairs([
            ("누구나 살다 보면 실수나 잘못을 하기 마련이다.", "Ai cũng khó tránh khỏi việc mắc sai lầm hoặc làm điều gì đó không đúng trong cuộc sống."),
            ("그러나 잘못을 인정하고 사과를 하는 사람이 있는가 하면 자존심 때문에 사과를 하지 않는 사람도 있다.", "Tuy nhiên, có người thừa nhận lỗi lầm và xin lỗi, nhưng cũng có người vì lòng tự trọng mà không chịu xin lỗi."),
            ("그러나 의도했든 의도하지 않았든 잘못을 했다면 책임을 져야 한다.", "Tuy nhiên, dù cố ý hay vô ý, nếu đã làm sai thì đều phải chịu trách nhiệm."),
            ("사소한 일로 화를 냈을 때, 친구에 대해 나쁜 말을 했을 때 등 자신의 잘못된 행동으로 인해 상처를 받거나 피해를 입은 사람이 있을 때는 반드시 사과해야 한다.", "Khi nổi giận vì những chuyện nhỏ nhặt, khi nói những lời không hay về bạn bè, hoặc khi có người bị tổn thương hay chịu thiệt hại do hành động sai trái của mình gây ra, nhất định phải xin lỗi."),
            ("물론 사과를 한다고 해서 반드시 용서를 받을 수 있는 것은 아니다.", "Tất nhiên, không phải cứ xin lỗi thì nhất định sẽ được tha thứ."),
            ("그렇다고 해서 자신의 잘못에 대해 모르는 척하거나 사과를 하지 않는다면 관계는 더 나빠진다.", "Tuy nhiên, nếu vì thế mà giả vờ như không biết lỗi lầm của mình hoặc không chịu xin lỗi thì mối quan hệ sẽ càng trở nên tồi tệ hơn."),
            ("사과는 이러한 부정적인 가능성을 긍정적으로 바꿀 수 있는 좋은 기회이다.", "Lời xin lỗi là một cơ hội tốt để biến những khả năng tiêu cực như vậy thành điều tích cực."),
            ("진심으로 사과한다면 관계가 회복되기도 하고 때로는 이전보다 더 가까워지기도 한다.", "Nếu chân thành xin lỗi, mối quan hệ có thể được khôi phục, đôi khi còn trở nên thân thiết hơn trước."),
            ("사과를 계기로 서로 배려하고 신뢰하는 마음도 더 깊어질 것이다.", "Thông qua lời xin lỗi, sự quan tâm và lòng tin dành cho nhau cũng sẽ trở nên sâu sắc hơn."),
            ("따라서 사과를 할 때는 먼저 변명하지 않고 자신의 잘못에 대해 인정하는 태도가 중요하다.", "Vì vậy, khi xin lỗi, trước tiên thái độ thừa nhận lỗi lầm của bản thân mà không viện cớ là điều rất quan trọng."),
            ("그런 잘못을 반복하지 않겠다는 다짐도 보여줘야 한다.", "Cũng cần thể hiện quyết tâm sẽ không lặp lại sai lầm đó."),
            ("또 사과하기에 적절한 때를 놓치지 않도록 주의해야 한다.", "Ngoài ra, cần chú ý không bỏ lỡ thời điểm thích hợp để xin lỗi."),
            ("고민하는 시간이 너무 길어지면 그 문제에 대해 다시 말하기가 어려워지고 반대로 그 시간이 너무 짧으면 신중하지 못하다는 인상을 줄 수 있기 때문이다.", "Bởi vì nếu mất quá nhiều thời gian đắn đo thì sẽ khó mở lời lại về vấn đề đó; ngược lại, nếu thời gian suy nghĩ quá ngắn thì có thể tạo ấn tượng rằng mình chưa suy nghĩ thấu đáo."),
        ]),
    },
    "Đề mẫu số 10 – Tính hai mặt của từ mới": {
        "title": "신조어의 양면성 – Tính hai mặt của từ mới, từ lóng và từ thịnh hành",
        "kr_vi": make_pairs([
            ("인터넷이 발달함에 따라 줄임말, 유행어와 같은 신조어가 많이 생기고 있다.", "Cùng với sự phát triển của Internet, ngày càng có nhiều từ mới xuất hiện, chẳng hạn như từ viết tắt và từ thịnh hành."),
            ("이러한 신조어를 사용하면 좋은 점이 많아 신조어를 사용하는 사람도 갈수록 늘고 있다.", "Vì việc sử dụng những từ mới này có nhiều ưu điểm nên số người sử dụng chúng cũng ngày càng tăng."),
            ("먼저 신조어를 사용하면 쉽고 빠르게 소통할 수 있다.", "Trước tiên, nếu sử dụng từ mới thì có thể giao tiếp một cách dễ dàng và nhanh chóng."),
            ("가령 '아르바이트'를 '알바'로 줄여 쓰면 훨씬 간편하다.", "Ví dụ, nếu rút gọn từ '아르바이트' (việc làm thêm) thành '알바' thì sẽ tiện lợi hơn nhiều."),
            ("또한 친근감을 줄 수 있다.", "Ngoài ra, chúng còn có thể tạo cảm giác gần gũi."),
            ("같은 유행어를 안다는 사실이 관계를 더욱 가깝게 만들어 주는데다가 유행어에 담긴 재치나 유머가 대화 분위기를 더욱 부드럽게 해 주기 때문이다.", "Bởi vì việc biết cùng một từ thịnh hành không chỉ giúp mối quan hệ trở nên thân thiết hơn mà sự dí dỏm và tính hài hước chứa đựng trong những từ đó còn giúp bầu không khí trò chuyện trở nên thoải mái hơn."),
            ("반면 신조어를 사용하면 세대 간의 원활한 대화를 방해할 수 있다.", "Ngược lại, việc sử dụng từ mới có thể cản trở giao tiếp suôn sẻ giữa các thế hệ."),
            ("연령이 높아질수록 인터넷 사용률이 떨어져 신조어를 잘 모를 때가 많기 때문이다.", "Bởi vì tuổi càng cao thì tỷ lệ sử dụng Internet càng giảm, do đó người lớn tuổi thường không biết nhiều về các từ mới."),
            ("또한 사회적으로 신조어 사용이 흔한 일이 되면서 때와 장소에 맞지 않게 신조어를 사용하는 사람들이 늘고 있는 것도 문제이다.", "Ngoài ra, việc sử dụng từ mới đã trở nên phổ biến trong xã hội, khiến số người sử dụng chúng không phù hợp với thời gian và địa điểm cũng ngày càng tăng. Đây cũng là một vấn đề."),
            ("그뿐만 아니라 신조어를 자주 사용하다 보니 국어 문법이나 철자법을 틀리는 경우도 많아지고 있다.", "Không chỉ vậy, do thường xuyên sử dụng từ mới nên những trường hợp mắc lỗi ngữ pháp tiếng Hàn hoặc chính tả cũng đang ngày càng tăng."),
            ("따라서 우리는 무분별하게 신조어를 사용하지 않도록 해야 한다.", "Vì vậy, chúng ta cần tránh sử dụng từ mới một cách thiếu suy nghĩ, tùy tiện."),
            ("예의를 갖추어야 하는 자리에서는 신조어 사용을 피해야 한다.", "Ở những nơi cần giữ phép lịch sự, chúng ta nên tránh sử dụng từ mới."),
            ("또한 신조어를 비판적으로 받아들일 필요가 있다.", "Ngoài ra, cần tiếp nhận các từ mới một cách có chọn lọc và mang tính phê phán."),
            ("신조어에는 사회에서 소외된 사람들에 대한 편견이 담겨 있는 경우도 있기 때문이다.", "Bởi vì trong một số từ mới cũng có chứa những định kiến đối với những người bị gạt ra ngoài lề xã hội."),
            ("그러한 말을 가벼운 농담거리로 삼아 편견을 확산시키지 않도록 조심해야 할 것이다.", "Chúng ta cần cẩn thận để không biến những từ ngữ như vậy thành trò đùa vô thưởng vô phạt rồi làm lan rộng những định kiến đó."),
        ]),
    },
    "Đề mẫu số 11 – Giáo dục ngoại ngữ sớm": {
        "title": "조기 외국어 교육의 양면성 – Tính hai mặt của giáo dục ngoại ngữ sớm",
        "kr_vi": make_pairs([
            ("세계화 시대가 되면서 외국어 능력의 중요성이 갈수록 커지고 있다.", "Cùng với việc bước vào thời đại toàn cầu hóa, tầm quan trọng của năng lực ngoại ngữ ngày càng tăng lên."),
            ("이로 인해 조기 외국어 교육을 하는 가정도 늘고 있다.", "Do đó, số gia đình cho con học ngoại ngữ từ sớm cũng đang ngày càng tăng."),
            ("부모들은 외국어 교육을 일찍 시작하면 아이가 외국어를 더 유창하게 구사할 수 있게 될 것이라고 생각한다.", "Cha mẹ cho rằng nếu bắt đầu giáo dục ngoại ngữ sớm thì trẻ sẽ có thể sử dụng ngoại ngữ thành thạo hơn."),
            ("언어 공부는 이른 나이에 시작할수록 더욱 효과적이라고 알려져 있기 때문이다.", "Bởi vì người ta cho rằng việc học ngôn ngữ càng bắt đầu ở độ tuổi nhỏ thì càng hiệu quả."),
            ("실제로 성인이 되어 외국어를 배우면 원어민과 같은 발음과 억양으로 말을 하기가 쉽지 않다.", "Trên thực tế, khi đã trưởng thành mới học ngoại ngữ thì không dễ nói với cách phát âm và ngữ điệu giống như người bản xứ."),
            ("반면에 단점도 있다.", "Ngược lại, việc này cũng có những nhược điểm."),
            ("조기 외국어 교육은 오히려 아이의 언어 능력을 떨어뜨릴 수 있다.", "Việc giáo dục ngoại ngữ sớm ngược lại có thể làm giảm năng lực ngôn ngữ của trẻ."),
            ("아이가 모국어도 잘하지 못하는 상황에서 외국어까지 공부하게 되면 심한 스트레스를 받기 때문이다.", "Bởi vì khi trẻ còn chưa thành thạo tiếng mẹ đẻ mà đã phải học thêm cả ngoại ngữ thì trẻ có thể phải chịu áp lực rất lớn."),
            ("그래서 학습에 흥미를 잃는 것은 물론이고 모국어 습득에도 문제가 생길 수 있다.", "Vì vậy, trẻ không chỉ mất hứng thú học tập mà còn có thể gặp vấn đề trong việc tiếp thu tiếng mẹ đẻ."),
            ("또한 조기 외국어 교육을 하는 가정이 많아지면 사회적으로 사교육비 문제가 커질 수 있다.", "Ngoài ra, nếu số gia đình cho con học ngoại ngữ sớm tăng lên thì vấn đề chi phí giáo dục tư nhân trong xã hội có thể trở nên nghiêm trọng hơn."),
            ("아이가 경쟁에서 뒤처질 것을 걱정해 무리해서라도 학원에 보내려고 하는 부모가 많아질 것이기 때문이다.", "Bởi vì sẽ ngày càng có nhiều cha mẹ lo lắng con mình bị tụt hậu trong cạnh tranh nên dù phải cố gắng quá sức cũng muốn gửi con đến các trung tâm học thêm."),
            ("이러한 점을 고려할 때, 나는 조기 외국어 교육에 반대한다.", "Xét đến những điểm trên, tôi phản đối việc giáo dục ngoại ngữ từ quá sớm."),
            ("일찍부터 아이에게 학습에 대한 부담감을 줄 필요는 없다고 보기 때문이다.", "Bởi vì tôi cho rằng không cần thiết phải tạo áp lực học tập cho trẻ ngay từ khi còn nhỏ."),
            ("물론 어린 나이에 외국어를 배우면 실력이 더 좋아질지도 모른다.", "Tất nhiên, nếu học ngoại ngữ từ khi còn nhỏ thì năng lực ngoại ngữ có thể sẽ tốt hơn."),
            ("그러나 중요한 것은 시기가 아니라 노력이므로 동기가 생겼을 때 아이가 스스로 공부해도 결코 늦지 않다.", "Tuy nhiên, điều quan trọng không phải là thời điểm mà là sự nỗ lực. Vì vậy, khi có động lực, dù trẻ tự mình bắt đầu học thì cũng tuyệt đối không phải là quá muộn."),
            ("어릴 때는 그 대신 놀이나 운동 등을 통해 잠재적인 능력을 찾고 키우는 것이 바람직하다.", "Thay vào đó, khi còn nhỏ, việc tìm kiếm và phát triển những năng lực tiềm ẩn thông qua vui chơi, thể thao và các hoạt động khác là điều nên làm."),
        ]),
    },
    "Đề mẫu số 12 – Văn hóa đại chúng": {
        "title": "대중문화의 발달과 영향 – Sự phát triển và ảnh hưởng của văn hóa đại chúng",
        "kr_vi": make_pairs([
            ("현대 사회에서는 미디어의 발달로 대중문화가 쉽게 생산되고 확산된다.", "Trong xã hội hiện đại, nhờ sự phát triển của truyền thông, văn hóa đại chúng dễ dàng được sản xuất và lan truyền."),
            ("스마트폰만 있으면 인터넷을 통해 언제 어디서든지 영화를 보고 음악을 들을 수 있으며 콘텐츠 제작에 직접 참여할 수도 있다.", "Chỉ cần có điện thoại thông minh, chúng ta có thể xem phim, nghe nhạc mọi lúc mọi nơi thông qua Internet, thậm chí còn có thể trực tiếp tham gia sản xuất nội dung."),
            ("덕분에 누구나 즐길 수 있고 누구나 대중문화의 주인공이 될 수도 있는 시대가 된 것이다.", "Nhờ đó, chúng ta đã bước vào thời đại mà bất kỳ ai cũng có thể thưởng thức và cũng có thể trở thành nhân vật chính trong văn hóa đại chúng."),
            ("그래서 사람들은 더 다양한 문화를 접하고 대중문화를 통해 교류하며 좋아하는 것들을 공유하게 되었다.", "Vì vậy, mọi người có thể tiếp xúc với nhiều nền văn hóa đa dạng hơn, giao lưu thông qua văn hóa đại chúng và chia sẻ những điều mình yêu thích."),
            ("그러나 대중문화의 발달이 사회에 긍정적인 영향만 미치는 것은 아니다.", "Tuy nhiên, sự phát triển của văn hóa đại chúng không chỉ mang lại những ảnh hưởng tích cực cho xã hội."),
            ("대중문화 콘텐츠를 제작하는 사람들이 사람들의 관심을 끌어 높은 수익을 얻기 위해 드라마, 노랫말 등에 자극적인 내용을 담는 경우가 늘고 있기 때문이다.", "Bởi vì ngày càng có nhiều trường hợp những người sản xuất nội dung văn hóa đại chúng đưa những nội dung gây kích thích vào phim truyền hình, lời bài hát... nhằm thu hút sự chú ý của mọi người và thu được lợi nhuận cao."),
            ("즉 대중문화에는 폭력적이고 선정적인 내용이 많이 포함되어 있을 수 있다.", "Nói cách khác, văn hóa đại chúng có thể chứa đựng nhiều nội dung mang tính bạo lực và khêu gợi."),
            ("이는 성장하는 아이들에게 특히 나쁜 영향을 미친다.", "Điều này đặc biệt gây ảnh hưởng xấu đến trẻ em đang trong giai đoạn trưởng thành."),
            ("따라서 대중문화의 장점을 살리면서 단점을 최소화하기 위해 대중문화를 비판적으로 수용할 줄 알아야 한다.", "Vì vậy, để phát huy những ưu điểm và giảm thiểu những nhược điểm của văn hóa đại chúng, chúng ta cần biết cách tiếp nhận văn hóa đại chúng một cách có chọn lọc và mang tính phê phán."),
            ("대중문화의 질 높은 콘텐츠와 질 낮은 콘텐츠를 구별하고 질 낮은 콘텐츠는 가능하면 피하려고 노력할 필요가 있다.", "Cần phân biệt nội dung văn hóa đại chúng có chất lượng cao với nội dung có chất lượng thấp, đồng thời cố gắng tránh những nội dung kém chất lượng nếu có thể."),
            ("또한 상업성이 강한 대중문화는 유행을 확산시키고 소비를 조장하는 경향이 있기 때문에 우리는 그에 휩쓸리지 않도록 경계해야 한다.", "Ngoài ra, văn hóa đại chúng mang tính thương mại cao có xu hướng lan truyền các trào lưu và thúc đẩy tiêu dùng, vì vậy chúng ta cần cảnh giác để không bị cuốn theo những điều đó."),
        ]),
    },
}

# Nạp các đề người dùng tự tạo từ SQLite; dữ liệu được lưu độc lập với mã nguồn.
for saved_exam in get_user_exams():
    key = saved_exam["exam_key"]
    if key not in EXAM_DATA:
        EXAM_DATA[key] = {
            "title": saved_exam["title"],
            "kr_vi": make_pairs(saved_exam["pairs"]),
        }

for exam in EXAM_DATA.values():
    exam["vi_kr"] = [
        {"id": q["id"], "source": q["target"], "target": q["source"]}
        for q in exam["kr_vi"]
    ]

st.info(f"Ngân hàng hiện có {len(EXAM_DATA)} chủ đề và {sum(len(v['kr_vi']) for v in EXAM_DATA.values())} câu Hàn–Việt; mỗi câu đều luyện được theo cả hai chiều.")

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

EXTRA_VOCAB.extend([
    ("자율성", "TOPIK 5", "Tính tự chủ, quyền tự quyết", "직장에서 개인의 자율성이 보장되어야 한다.", "Tính tự chủ của cá nhân cần được đảm bảo tại nơi làm việc.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("유연근무제", "TOPIK 5", "Chế độ làm việc linh hoạt", "기업에서는 유연근무제를 실시하고 있다.", "Các doanh nghiệp đang triển khai chế độ làm việc linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("근무 여건", "TOPIK 4-5", "Điều kiện làm việc", "자신에게 적합한 근무 여건을 조성해야 한다.", "Cần tạo điều kiện làm việc phù hợp với bản thân.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("부작용", "TOPIK 5", "Tác dụng phụ, hệ quả tiêu cực", "개인의 자율성만 중시하면 부작용이 발생할 수 있다.", "Nếu chỉ coi trọng tính tự chủ cá nhân thì có thể phát sinh hệ quả tiêu cực.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("이기주의", "TOPIK 5", "Chủ nghĩa ích kỷ", "자율성이 이기주의로 변질될 수 있다.", "Tính tự chủ có thể biến chất thành chủ nghĩa ích kỷ.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("가짜 뉴스", "TOPIK 4-5", "Tin giả", "가짜 뉴스는 심각한 사회 문제이다.", "Tin giả là một vấn đề xã hội nghiêm trọng.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("대중화", "TOPIK 5", "Sự phổ biến rộng rãi", "소셜 미디어의 대중화로 정보 공유가 쉬워졌다.", "Nhờ mạng xã hội phổ biến rộng rãi, việc chia sẻ thông tin trở nên dễ dàng.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("불특정 다수", "TOPIK 5-6", "Đông đảo người không xác định", "불특정 다수와 정보를 공유할 수 있다.", "Có thể chia sẻ thông tin với đông đảo người không xác định.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("유통하다", "TOPIK 5", "Lưu thông, phân phối", "가짜 뉴스의 생산과 유통을 규제해야 한다.", "Cần quản lý việc sản xuất và phát tán tin giả.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("근절하다", "TOPIK 5", "Loại trừ, diệt trừ tận gốc", "가짜 뉴스를 근절하기 위한 대책이 필요하다.", "Cần có biện pháp loại bỏ tin giả tận gốc.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("선입견", "TOPIK 5", "Định kiến", "잘못된 정보는 선입견을 형성하게 한다.", "Thông tin sai lệch khiến con người hình thành định kiến.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("명예가 훼손되다", "TOPIK 5-6", "Danh dự bị tổn hại", "가짜 뉴스로 개인의 명예가 훼손될 수 있다.", "Danh dự của cá nhân có thể bị tổn hại bởi tin giả.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("디지털 소외", "TOPIK 5", "Tình trạng bị gạt ra bên lề trong xã hội số", "디지털 소외 계층을 위한 지원 정책이 필요하다.", "Cần có chính sách hỗ trợ những nhóm người bị gạt ra bên lề trong xã hội số.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("키오스크", "TOPIK 3-4", "Máy kiosk tự phục vụ", "키오스크로 음식을 주문할 수 있다.", "Có thể gọi món bằng máy kiosk.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("고령층", "TOPIK 4", "Người cao tuổi", "고령층은 디지털 기기 사용에 어려움을 겪을 수 있다.", "Người cao tuổi có thể gặp khó khăn khi sử dụng thiết bị kỹ thuật số.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("디지털 인프라", "TOPIK 5", "Cơ sở hạ tầng kỹ thuật số", "디지털 인프라를 확충해야 한다.", "Cần mở rộng cơ sở hạ tầng kỹ thuật số.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("일회용품", "TOPIK 3-4", "Đồ dùng một lần", "일회용품 사용을 줄여야 한다.", "Cần giảm việc sử dụng đồ dùng một lần.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("산업화", "TOPIK 4-5", "Công nghiệp hóa", "급격한 산업화가 환경에 영향을 미쳤다.", "Quá trình công nghiệp hóa nhanh chóng đã ảnh hưởng đến môi trường.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("도시화", "TOPIK 4-5", "Đô thị hóa", "도시화로 인해 숲이 사라지고 있다.", "Rừng đang biến mất do quá trình đô thị hóa.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("폐수", "TOPIK 4-5", "Nước thải", "산업 폐수가 바다를 오염시켰다.", "Nước thải công nghiệp đã làm ô nhiễm biển.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("개인주의", "TOPIK 5", "Chủ nghĩa cá nhân", "개인주의가 심화되면서 무관심이 커지고 있다.", "Sự thờ ơ gia tăng khi chủ nghĩa cá nhân ngày càng sâu sắc.", "Bài luyện bổ sung – Sự thờ ơ của con người hiện đại"),
    ("무관심", "TOPIK 4-5", "Sự thờ ơ, không quan tâm", "타인에 대한 무관심이 사회 문제로 이어질 수 있다.", "Sự thờ ơ với người khác có thể dẫn đến vấn đề xã hội.", "Bài luyện bổ sung – Sự thờ ơ của con người hiện đại"),
])


# BỔ SUNG CHUYÊN SÂU TỪ VỰNG CHO TOPIC 3–6
# Các ví dụ được lấy trực tiếp hoặc phát triển sát nội dung bài mẫu tương ứng.
EXTRA_VOCAB.extend([
    # Topic 3 – Năng lực hợp tác
    ("협업 능력", "TOPIK 5", "Năng lực hợp tác, khả năng phối hợp làm việc", "오늘날 많은 기업에서는 인재의 조건 중 하나로 협업 능력을 손꼽는다.", "Ngày nay, nhiều doanh nghiệp xem năng lực hợp tác là một trong những tiêu chí cần có ở nhân tài.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("손꼽다", "TOPIK 5", "Kể đến, xem là một trong những điều tiêu biểu/quan trọng", "많은 기업에서는 협업 능력을 중요한 조건으로 손꼽는다.", "Nhiều doanh nghiệp xem năng lực hợp tác là một tiêu chí quan trọng.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("분야를 맡다", "TOPIK 4-5", "Đảm nhận lĩnh vực/phần việc", "각자 잘하는 분야를 맡아서 일을 나누어 하는 것이 효율적이다.", "Mỗi người đảm nhận lĩnh vực mình làm tốt và phân chia công việc sẽ hiệu quả hơn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("일을 나누어 하다", "TOPIK 3-4", "Phân chia công việc để cùng làm", "일을 나누어 하면 처리 속도가 빨라질 수 있다.", "Nếu phân chia công việc thì tốc độ xử lý có thể nhanh hơn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("처리 속도", "TOPIK 4-5", "Tốc độ xử lý", "협업을 하면 일을 처리하는 속도가 빨라진다.", "Nếu hợp tác thì tốc độ xử lý công việc sẽ nhanh hơn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("성과를 얻다", "TOPIK 4-5", "Đạt được thành quả/kết quả", "서로 협력하면 더 좋은 성과를 얻을 수 있다.", "Nếu hợp tác với nhau thì có thể đạt được thành quả tốt hơn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("부족함을 채워 주다", "TOPIK 4-5", "Bù đắp thiếu sót cho nhau", "팀원들은 서로의 부족함을 채워 줄 수 있다.", "Các thành viên có thể bù đắp những thiếu sót cho nhau.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("자극을 주고받다", "TOPIK 5", "Tạo động lực/khích lệ lẫn nhau", "동료들과 자극을 주고받으면서 함께 성장할 수 있다.", "Có thể cùng trưởng thành khi tạo động lực cho nhau với đồng nghiệp.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("시너지 효과", "TOPIK 5-6", "Hiệu ứng cộng hưởng", "서로의 능력을 결합하면 시너지 효과가 생긴다.", "Nếu kết hợp năng lực của nhau thì sẽ tạo ra hiệu ứng cộng hưởng.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("의견 차이", "TOPIK 4-5", "Sự khác biệt/bất đồng ý kiến", "사람마다 생각이 다르므로 의견 차이는 생길 수밖에 없다.", "Vì mỗi người có suy nghĩ khác nhau nên bất đồng ý kiến là điều không thể tránh khỏi.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("고집하다", "TOPIK 4-5", "Khăng khăng, cố chấp giữ ý kiến", "자신의 의견만 옳다고 고집하면 협업이 어려워진다.", "Nếu khăng khăng cho rằng chỉ ý kiến của mình đúng thì việc hợp tác sẽ trở nên khó khăn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("팀워크", "TOPIK 4-5", "Tinh thần/khả năng phối hợp nhóm", "의견 충돌은 팀워크에도 악영향을 미칠 수 있다.", "Xung đột ý kiến cũng có thể gây ảnh hưởng tiêu cực đến tinh thần làm việc nhóm.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("악영향을 미치다", "TOPIK 5", "Gây ảnh hưởng xấu/tiêu cực", "갈등은 팀워크와 업무 효율성에 악영향을 미친다.", "Mâu thuẫn gây ảnh hưởng tiêu cực đến tinh thần nhóm và hiệu quả công việc.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("책임 의식", "TOPIK 5", "Ý thức trách nhiệm", "맡은 일에 책임 의식을 가지고 최선을 다해야 한다.", "Cần có ý thức trách nhiệm với công việc được giao và cố gắng hết sức.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("일을 미루다", "TOPIK 3-4", "Trì hoãn/đùn đẩy công việc", "다른 사람에게 일을 미루어서는 안 된다.", "Không được đùn đẩy công việc cho người khác.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("마감 날짜를 지키다", "TOPIK 4", "Tuân thủ thời hạn hoàn thành", "팀원들은 업무의 마감 날짜를 지켜야 한다.", "Các thành viên trong nhóm phải tuân thủ thời hạn công việc.", "Đề mẫu 3 – Năng lực hợp tác"),

    # Topic 4 – Năng lực đồng cảm
    ("공감 능력", "TOPIK 5", "Năng lực đồng cảm", "공감 능력은 원만한 인간관계를 맺는 데 중요하다.", "Năng lực đồng cảm quan trọng trong việc xây dựng các mối quan hệ hài hòa.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("타인의 감정", "TOPIK 4", "Cảm xúc của người khác", "타인의 감정에 관심을 가질 필요가 있다.", "Cần quan tâm đến cảm xúc của người khác.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("무관심하다", "TOPIK 4-5", "Thờ ơ, không quan tâm", "타인의 감정에 무관심한 사람이 늘고 있다.", "Số người thờ ơ với cảm xúc của người khác đang tăng lên.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("원만한 인간관계", "TOPIK 4-5", "Mối quan hệ giữa người với người hài hòa", "공감 능력은 원만한 인간관계를 맺는 데 도움이 된다.", "Năng lực đồng cảm giúp xây dựng các mối quan hệ hài hòa.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("믿고 의지하다", "TOPIK 4-5", "Tin tưởng và dựa dẫm vào nhau", "서로 믿고 의지하는 관계를 형성해야 한다.", "Cần hình thành mối quan hệ tin tưởng và dựa dẫm vào nhau.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("어려운 상황에 처하다", "TOPIK 4-5", "Rơi vào hoàn cảnh khó khăn", "어려운 상황에 처한 사람을 도와야 한다.", "Cần giúp đỡ những người đang rơi vào hoàn cảnh khó khăn.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("나서서 돕다", "TOPIK 4-5", "Chủ động đứng ra giúp đỡ", "상대방의 어려움을 이해하면 자신의 일처럼 나서서 돕게 된다.", "Nếu hiểu được khó khăn của đối phương thì sẽ chủ động giúp đỡ như việc của chính mình.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("자기중심적으로 행동하다", "TOPIK 5", "Hành động theo hướng lấy bản thân làm trung tâm", "공감 능력이 부족하면 자기중심적으로 행동하기 쉽다.", "Nếu thiếu năng lực đồng cảm thì dễ hành động theo hướng lấy bản thân làm trung tâm.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("감정을 읽다", "TOPIK 4-5", "Đọc/nhận biết cảm xúc", "다른 사람의 감정을 잘 읽는 능력이 필요하다.", "Cần có khả năng nhận biết tốt cảm xúc của người khác.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("타인의 아픔", "TOPIK 4", "Nỗi đau của người khác", "타인의 아픔을 이해하고 배려해야 한다.", "Cần thấu hiểu và quan tâm đến nỗi đau của người khác.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("폭력성", "TOPIK 5", "Tính bạo lực, khuynh hướng bạo lực", "타인의 아픔을 느끼지 못하면 폭력성이 증가할 수 있다.", "Nếu không cảm nhận được nỗi đau của người khác thì tính bạo lực có thể gia tăng.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("집단 따돌림", "TOPIK 4-5", "Bắt nạt/tẩy chay tập thể", "공감 능력 부족은 학교 폭력이나 집단 따돌림으로 이어질 수 있다.", "Thiếu năng lực đồng cảm có thể dẫn đến bạo lực học đường hoặc bắt nạt tập thể.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("입장에서 생각하다", "TOPIK 4-5", "Suy nghĩ từ lập trường/vị trí của ai đó", "상대방의 입장에서 생각해 보는 연습이 필요하다.", "Cần luyện tập suy nghĩ từ lập trường của đối phương.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("상상해 보다", "TOPIK 3-4", "Thử tưởng tượng", "같은 일이 자신에게 생긴다면 어떨지 상상해 보아야 한다.", "Cần thử tưởng tượng nếu chuyện tương tự xảy ra với bản thân thì sẽ thế nào.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("간접적으로 느끼다", "TOPIK 4-5", "Cảm nhận một cách gián tiếp", "예술 작품을 통해 인물의 감정을 간접적으로 느낄 수 있다.", "Có thể cảm nhận gián tiếp cảm xúc của nhân vật thông qua tác phẩm nghệ thuật.", "Bài luyện bổ sung – Năng lực đồng cảm"),

    # Topic 5 – Văn hóa truyền thống
    ("전통문화", "TOPIK 4", "Văn hóa truyền thống", "나라마다 고유한 전통문화가 있다.", "Mỗi quốc gia đều có nền văn hóa truyền thống riêng.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("고유하다", "TOPIK 5", "Mang tính riêng biệt, đặc trưng vốn có", "각 나라는 고유한 문화를 가지고 있다.", "Mỗi quốc gia đều có nền văn hóa mang nét đặc trưng riêng.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("세계화", "TOPIK 5", "Toàn cầu hóa", "세계화의 영향으로 생활 모습이 비슷해지고 있다.", "Dưới ảnh hưởng của toàn cầu hóa, lối sống đang trở nên giống nhau.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("산업화", "TOPIK 4-5", "Công nghiệp hóa", "세계화와 산업화로 전통문화가 잊혀지고 있다.", "Do toàn cầu hóa và công nghiệp hóa, văn hóa truyền thống đang bị lãng quên.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("잊혀지다", "TOPIK 4-5", "Bị lãng quên", "전통문화가 점점 잊혀지고 있다.", "Văn hóa truyền thống đang dần bị lãng quên.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("조상들의 지혜", "TOPIK 4-5", "Trí tuệ/kinh nghiệm khôn ngoan của tổ tiên", "전통문화에는 조상들의 지혜가 담겨 있다.", "Trong văn hóa truyền thống có chứa đựng trí tuệ của tổ tiên.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("담겨 있다", "TOPIK 4-5", "Được chứa đựng, hàm chứa", "전통 예절에는 공동체 생활의 지혜가 담겨 있다.", "Trong lễ nghi truyền thống hàm chứa trí tuệ về đời sống cộng đồng.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("어른을 공경하다", "TOPIK 4", "Kính trọng người lớn tuổi", "어른을 공경하는 예절은 중요한 전통문화이다.", "Lễ nghi kính trọng người lớn tuổi là một nét văn hóa truyền thống quan trọng.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("예절 문화", "TOPIK 4-5", "Văn hóa lễ nghi/phép tắc ứng xử", "예절 문화는 함께 살아가는 지혜를 보여 준다.", "Văn hóa lễ nghi thể hiện trí tuệ trong việc chung sống với nhau.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("예술적 가치", "TOPIK 5", "Giá trị nghệ thuật", "전통문화에는 예술적 가치가 높은 것이 많다.", "Trong văn hóa truyền thống có nhiều thứ mang giá trị nghệ thuật cao.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("보존하다", "TOPIK 4-5", "Bảo tồn, gìn giữ", "가치 있는 전통문화를 보존해야 한다.", "Cần bảo tồn những nền văn hóa truyền thống có giá trị.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("계승하다", "TOPIK 5", "Kế thừa, tiếp nối", "전통문화를 현대적으로 계승할 방법을 찾아야 한다.", "Cần tìm phương pháp kế thừa văn hóa truyền thống theo hướng hiện đại.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("편견", "TOPIK 4-5", "Định kiến", "전통문화에 대한 편견을 버릴 필요가 있다.", "Cần từ bỏ định kiến về văn hóa truyền thống.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("쓸모가 없다", "TOPIK 3-4", "Không có ích, vô dụng", "전통문화가 오늘날에는 쓸모가 없다고 생각하는 사람도 있다.", "Cũng có người cho rằng văn hóa truyền thống ngày nay không còn có ích.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("기호", "TOPIK 5", "Sở thích, thị hiếu", "현대인의 기호에 맞게 전통문화를 바꿀 수 있다.", "Có thể thay đổi văn hóa truyền thống sao cho phù hợp với thị hiếu của người hiện đại.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("변형하다", "TOPIK 5", "Biến đổi, cải biến hình thức", "전통문화를 현대인의 기호에 맞게 변형할 수 있다.", "Có thể cải biến văn hóa truyền thống cho phù hợp với thị hiếu người hiện đại.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("가치를 떨어뜨리다", "TOPIK 5", "Làm giảm giá trị", "전통문화의 가치를 떨어뜨리지 않도록 주의해야 한다.", "Cần chú ý để không làm giảm giá trị của văn hóa truyền thống.", "Đề mẫu 4 – Văn hóa truyền thống"),

    # Topic 6 – Tính tự chủ cá nhân tại nơi làm việc
    ("자율성", "TOPIK 5", "Tính tự chủ, quyền tự quyết", "직장에서 개인의 자율성이 보장되어야 한다.", "Tính tự chủ của cá nhân cần được đảm bảo tại nơi làm việc.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("중시하다", "TOPIK 4-5", "Coi trọng, đề cao", "최근 개인의 자율성을 중시하는 사람들이 많아졌다.", "Gần đây, số người coi trọng tính tự chủ cá nhân đã tăng lên.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("유연근무제", "TOPIK 5", "Chế độ làm việc linh hoạt", "기업에서는 유연근무제를 실시하고 있다.", "Các doanh nghiệp đang triển khai chế độ làm việc linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("실시하다", "TOPIK 4", "Thực hiện, triển khai (chính sách/chế độ)", "기업은 유연근무제를 실시할 수 있다.", "Doanh nghiệp có thể triển khai chế độ làm việc linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("보장되다", "TOPIK 4-5", "Được đảm bảo", "직장 내 개인의 자율성이 보장되어야 한다.", "Tính tự chủ của cá nhân tại nơi làm việc cần được đảm bảo.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("직장 내 문화", "TOPIK 4-5", "Văn hóa trong môi trường công sở", "자율성이 보장되면 직장 내 문화가 유연해진다.", "Nếu tính tự chủ được đảm bảo thì văn hóa công sở sẽ trở nên linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("창의성을 발휘하다", "TOPIK 5", "Phát huy khả năng sáng tạo", "자율적인 근무 환경에서는 창의성을 발휘하기 쉽다.", "Trong môi trường làm việc tự chủ, việc phát huy khả năng sáng tạo sẽ dễ dàng hơn.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("근무 환경", "TOPIK 4", "Môi trường làm việc", "창의성을 발휘할 수 있는 근무 환경을 만들어야 한다.", "Cần tạo ra môi trường làm việc để có thể phát huy khả năng sáng tạo.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("일과 삶의 균형", "TOPIK 5", "Sự cân bằng giữa công việc và cuộc sống", "자율적인 근무는 일과 삶의 균형에 도움이 된다.", "Cách làm việc tự chủ có ích cho sự cân bằng giữa công việc và cuộc sống.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("업무 효율", "TOPIK 4-5", "Hiệu suất/hiệu quả công việc", "자율성은 구성원의 업무 효율을 높일 수 있다.", "Tính tự chủ có thể nâng cao hiệu suất công việc của các thành viên.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("공동의 목표", "TOPIK 4-5", "Mục tiêu chung", "개인의 입장보다 공동의 목표를 생각해야 한다.", "Cần nghĩ đến mục tiêu chung thay vì chỉ nghĩ đến lập trường cá nhân.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("이기주의", "TOPIK 5", "Chủ nghĩa ích kỷ", "자율성이 지나치면 이기주의로 변질될 수 있다.", "Nếu tính tự chủ đi quá mức thì có thể biến chất thành chủ nghĩa ích kỷ.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("변질되다", "TOPIK 5", "Biến chất, chuyển thành trạng thái tiêu cực", "자율성이 이기주의로 변질되지 않도록 해야 한다.", "Cần tránh để tính tự chủ biến chất thành chủ nghĩa ích kỷ.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("합의점을 찾다", "TOPIK 5", "Tìm điểm thống nhất/điểm chung", "충분히 소통해야 합의점을 찾을 수 있다.", "Cần trao đổi đầy đủ mới có thể tìm được điểm thống nhất.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("배려하는 마음", "TOPIK 4-5", "Tấm lòng biết quan tâm, nghĩ cho người khác", "동료를 배려하는 마음을 가져야 한다.", "Cần có tấm lòng biết quan tâm đến đồng nghiệp.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("의사소통 방안", "TOPIK 5", "Phương án giao tiếp/trao đổi thông tin", "효율적인 의사소통 방안을 마련해야 한다.", "Cần xây dựng phương án giao tiếp hiệu quả.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
])


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

EXTRA_GRAMMAR.extend([
    ("-고자 노력하다", "Nỗ lực để thực hiện mục tiêu nào đó.", "기업은 직장 내 자율성을 높이고자 노력하고 있다.", "Doanh nghiệp đang nỗ lực nâng cao tính tự chủ tại nơi làm việc.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-으로 변질되다", "Biến chất thành, chuyển thành trạng thái tiêu cực.", "자율성이 이기주의로 변질될 수 있다.", "Tính tự chủ có thể biến chất thành chủ nghĩa ích kỷ.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-는 데 기여하다", "Góp phần vào việc ...; văn viết trang trọng.", "업무 효율을 높이는 데 기여한다.", "Góp phần nâng cao hiệu suất công việc.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-로 하여금 -게 하다", "Khiến/ làm cho ai đó thực hiện hoặc rơi vào trạng thái nào đó.", "가짜 뉴스는 정보 수용자로 하여금 편협한 사고를 형성하게 한다.", "Tin giả khiến người tiếp nhận thông tin hình thành lối suy nghĩ phiến diện.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("-은/는 물론이고", "Không chỉ ... mà còn ...; nhấn mạnh sự bổ sung.", "경제적 피해는 물론이고 명예도 훼손된다.", "Không chỉ thiệt hại kinh tế mà danh dự cũng bị tổn hại.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("-지 않도록", "Để không ...; diễn đạt mục đích ngăn chặn.", "가짜 뉴스가 확산되지 않도록 규제를 강화해야 한다.", "Cần tăng cường quy định để tin giả không lan rộng.", "Đề bổ sung – Vấn đề và giải pháp loại bỏ tin giả"),
    ("-에 무관하게", "Không phụ thuộc vào, không phân biệt ...", "지역과 계층에 무관하게 혜택을 누릴 수 있어야 한다.", "Mọi người cần được hưởng lợi ích không phân biệt khu vực và tầng lớp.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("-는 데 어려움이 따르다", "Gặp khó khăn trong việc ...", "디지털 기기를 사용하는 데 어려움이 따른다.", "Gặp khó khăn trong việc sử dụng thiết bị kỹ thuật số.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("-에 뒤처지다", "Tụt hậu, bị bỏ lại phía sau so với ...", "변화하는 시대에 뒤처지지 않도록 노력해야 한다.", "Cần nỗ lực để không bị tụt hậu trước thời đại đang thay đổi.", "Đề bổ sung – Tình trạng bị gạt ra bên lề trong xã hội số"),
    ("-보다는", "Thay vì ... thì ...; nêu sự đối lập/ưu tiên.", "환경보호보다는 편리함만 추구했다.", "Chỉ theo đuổi sự tiện lợi thay vì bảo vệ môi trường.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("-을/를 들 수 있다", "Có thể kể đến ...; dùng để nêu ví dụ/nguyên nhân.", "그 이유로는 일회용품 사용 증가를 들 수 있다.", "Có thể kể đến việc gia tăng sử dụng đồ dùng một lần như một nguyên nhân.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("-기 때문이다", "Bởi vì ...; nêu nguyên nhân.", "환경보호보다 편리함을 추구했기 때문이다.", "Bởi vì con người theo đuổi sự tiện lợi hơn là bảo vệ môi trường.", "Bài luyện bổ sung – Nguyên nhân ô nhiễm môi trường"),
    ("-는 경향이 있다", "Có xu hướng ...", "현대인들은 다른 사람에게 관심을 가지지 않는 경향이 있다.", "Người hiện đại có xu hướng không quan tâm đến người khác.", "Bài luyện bổ sung – Sự thờ ơ của con người hiện đại"),
    ("-에 대한 믿음을 잃다", "Mất niềm tin vào ...", "많은 사람들이 타인에 대한 믿음을 잃었다.", "Nhiều người đã mất niềm tin vào người khác.", "Bài luyện bổ sung – Sự thờ ơ của con người hiện đại"),
])


# BỔ SUNG ĐẦY ĐỦ BIỂU HIỆN VÀ NGỮ PHÁP CÂU 54 CHO TOPIC 3–6
EXTRA_GRAMMAR.extend([
    # Topic 3 – Năng lực hợp tác
    ("- 중 하나로 손꼽히다", "Được xem/kể là một trong những ...; cách diễn đạt trang trọng khi nêu tiêu chí hoặc giá trị.", "협업 능력은 인재가 갖추어야 할 조건 중 하나로 손꼽힌다.", "Năng lực hợp tác được xem là một trong những điều kiện mà nhân tài cần có.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-기 때문에", "Bởi vì ... nên ...; nêu nguyên nhân trực tiếp, phù hợp văn viết TOPIK.", "사람마다 능력이 다르기 때문에 일을 나누어 하는 것이 효율적이다.", "Bởi vì năng lực mỗi người khác nhau nên phân chia công việc sẽ hiệu quả.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-는 것보다", "So với việc ...; dùng để đối chiếu hai cách làm hoặc hai trạng thái.", "혼자 일하는 것보다 함께 협력하는 것이 더 효율적이다.", "Hợp tác cùng nhau hiệu quả hơn so với làm việc một mình.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-ㄹ/을 수 있다", "Có thể ...; diễn đạt khả năng hoặc kết quả có thể đạt được.", "서로 협력하면 더 좋은 성과를 얻을 수 있다.", "Nếu hợp tác với nhau thì có thể đạt được thành quả tốt hơn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-기란 결코 쉽지 않다", "Việc ... tuyệt nhiên không dễ; nhấn mạnh mức độ khó khăn trong văn viết.", "효율적으로 협업을 하기란 결코 쉽지 않다.", "Để hợp tác một cách hiệu quả tuyệt nhiên không phải điều dễ dàng.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-ㄹ/을 수밖에 없다", "Không thể không ..., tất yếu phải ...; diễn đạt điều khó tránh khỏi.", "사람마다 생각이 다르므로 의견 차이는 생길 수밖에 없다.", "Vì mỗi người có suy nghĩ khác nhau nên bất đồng ý kiến là điều không thể tránh khỏi.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-다고 고집하다", "Khăng khăng cho rằng ...; diễn tả thái độ cố chấp với quan điểm cá nhân.", "자신의 의견만 옳다고 고집하면 협업이 어려워진다.", "Nếu khăng khăng cho rằng chỉ ý kiến của mình đúng thì việc hợp tác sẽ trở nên khó khăn.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-도록 주의해야 하다", "Cần chú ý để không/để ...; dùng khi đưa ra lời khuyên hoặc biện pháp phòng tránh.", "팀 전체에 피해를 주는 일이 없도록 주의해야 한다.", "Cần chú ý để không gây thiệt hại cho toàn bộ nhóm.", "Đề mẫu 3 – Năng lực hợp tác"),
    ("-을/를 대신하다", "Làm thay/thay thế cho ...; thường dùng khi nói về phân công hoặc trách nhiệm.", "한 사람이 맡은 일을 하지 못하면 다른 팀원이 대신해야 한다.", "Nếu một người không thể làm phần việc được giao thì thành viên khác phải làm thay.", "Đề mẫu 3 – Năng lực hợp tác"),

    # Topic 4 – Năng lực đồng cảm
    ("-다는 점에서 중요하다", "Quan trọng ở điểm ...; nêu căn cứ/khía cạnh làm nổi bật tầm quan trọng.", "공감 능력은 원만한 인간관계를 맺게 해 준다는 점에서 중요하다.", "Năng lực đồng cảm quan trọng ở chỗ nó giúp xây dựng các mối quan hệ hài hòa.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-다면", "Nếu ... thì ...; giả định một tình huống để nêu kết quả.", "친구가 슬퍼할 때 공감해 주지 못한다면 서로 믿기 어려울 것이다.", "Nếu không thể đồng cảm khi bạn buồn thì sẽ khó tin tưởng lẫn nhau.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-는 데 어려움을 겪다", "Gặp khó khăn trong việc ...; nêu trở ngại trong hành động hoặc năng lực.", "공감 능력이 부족하면 다른 사람과 관계를 맺는 데 어려움을 겪을 수 있다.", "Nếu thiếu năng lực đồng cảm thì có thể gặp khó khăn trong việc xây dựng quan hệ với người khác.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-기 때문에 -게 되다", "Vì ... nên đi đến/khiến cho ...; kết hợp nguyên nhân với sự thay đổi hành vi/kết quả.", "상대방의 어려움을 느낄 수 있기 때문에 자신의 일처럼 돕게 된다.", "Vì có thể cảm nhận khó khăn của đối phương nên chúng ta sẽ giúp đỡ như việc của chính mình.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-로 인해", "Do/bởi ...; cụm danh từ chỉ nguyên nhân, thường dùng trong văn viết.", "공감 능력 부족으로 다른 사람의 감정을 잘 읽지 못한다.", "Do thiếu năng lực đồng cảm nên không thể hiểu rõ cảm xúc của người khác.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-게 되다", "Trở nên/dần dẫn đến việc ...; diễn đạt sự thay đổi hoặc kết quả phát sinh.", "자기중심적으로 행동하게 될 수 있다.", "Có thể trở nên hành động theo hướng lấy bản thân làm trung tâm.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-뿐만 아니라", "Không chỉ ... mà còn ...; mở rộng thêm tác động hoặc lợi ích cùng chiều.", "공감 능력은 인간관계뿐만 아니라 사회생활에도 중요하다.", "Năng lực đồng cảm quan trọng không chỉ trong quan hệ con người mà còn trong đời sống xã hội.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-는다면 어떤 느낌이 들지", "Nếu ... thì sẽ có cảm giác thế nào; cấu trúc đặt mình vào hoàn cảnh giả định của người khác.", "같은 일이 자신에게 생긴다면 어떤 느낌이 들지 상상해 보아야 한다.", "Cần tưởng tượng xem bản thân sẽ cảm thấy thế nào nếu chuyện tương tự xảy ra với mình.", "Bài luyện bổ sung – Năng lực đồng cảm"),
    ("-(으)ㅁ으로써", "Thông qua/bằng việc ...; danh từ hóa hành động để nêu phương thức đạt kết quả.", "작품 속 인물의 감정을 간접적으로 느낌으로써 공감 능력을 키울 수 있다.", "Thông qua việc gián tiếp cảm nhận cảm xúc của nhân vật trong tác phẩm, ta có thể nâng cao năng lực đồng cảm.", "Bài luyện bổ sung – Năng lực đồng cảm"),

    # Topic 5 – Văn hóa truyền thống
    ("-마다", "Mỗi ... đều ...; biểu thị sự phân bố đồng đều theo từng đối tượng.", "나라마다 고유한 전통문화가 있다.", "Mỗi quốc gia đều có nền văn hóa truyền thống mang nét đặc trưng riêng.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-의 영향으로", "Dưới/do ảnh hưởng của ...; nêu nguyên nhân tác động.", "세계화와 산업화의 영향으로 생활 모습이 비슷해지고 있다.", "Dưới ảnh hưởng của toàn cầu hóa và công nghiệp hóa, lối sống đang trở nên giống nhau.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-아/어지다", "Trở nên ...; diễn tả sự thay đổi trạng thái.", "각국의 생활 모습이 점점 비슷해지고 있다.", "Lối sống của các quốc gia đang dần trở nên giống nhau.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-에는 ...이/가 담겨 있다", "Trong ... có chứa đựng/hàm chứa ...; dùng để nói về giá trị tinh thần, tri thức hoặc ý nghĩa.", "전통문화에는 조상들의 지혜가 담겨 있다.", "Trong văn hóa truyền thống có chứa đựng trí tuệ của tổ tiên.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-아무리 -아/어도", "Dù ... đến đâu thì cũng ...; nhấn mạnh kết quả không thay đổi trước mức độ cao.", "세월이 아무리 흘러도 전통 예술의 가치는 쉽게 사라지지 않는다.", "Dù thời gian có trôi qua bao lâu thì giá trị nghệ thuật truyền thống cũng không dễ biến mất.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-ㄹ/을 가치가 있다", "Có giá trị/đáng để ...; dùng để đánh giá ý nghĩa của một đối tượng.", "전통문화는 보존할 가치가 있다.", "Văn hóa truyền thống có giá trị đáng được bảo tồn.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-에도 원인이 있다", "Nguyên nhân cũng nằm ở ...; bổ sung một nguyên nhân khác.", "전통문화가 사라지는 데에는 현대인의 생활 방식 변화에도 원인이 있다.", "Nguyên nhân khiến văn hóa truyền thống mai một cũng nằm ở sự thay đổi lối sống của người hiện đại.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-에 맞게", "Phù hợp với/theo đúng ...; diễn đạt sự điều chỉnh theo đối tượng hoặc điều kiện.", "현대인의 기호에 맞게 전통문화를 변형할 수 있다.", "Có thể cải biến văn hóa truyền thống sao cho phù hợp với thị hiếu người hiện đại.", "Đề mẫu 4 – Văn hóa truyền thống"),
    ("-지 않도록 주의하다", "Chú ý để không ...; diễn đạt biện pháp ngăn ngừa kết quả không mong muốn.", "전통문화의 가치가 떨어지지 않도록 주의해야 한다.", "Cần chú ý để giá trị văn hóa truyền thống không bị giảm sút.", "Đề mẫu 4 – Văn hóa truyền thống"),

    # Topic 6 – Tính tự chủ cá nhân tại nơi làm việc
    ("-에 따라", "Theo/cùng với ...; diễn đạt sự thay đổi tương ứng với một điều kiện hoặc xu hướng.", "사회 변화에 따라 개인의 자율성을 중시하는 사람이 많아졌다.", "Cùng với sự thay đổi của xã hội, số người coi trọng tính tự chủ cá nhân đã tăng lên.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-는 등", "Chẳng hạn như ..., và những việc tương tự; đưa ví dụ tiêu biểu.", "기업에서는 유연근무제를 실시하는 등 자율성을 높이고 있다.", "Các doanh nghiệp đang nâng cao tính tự chủ, chẳng hạn như triển khai chế độ làm việc linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-면", "Nếu/khi ... thì ...; diễn đạt điều kiện và kết quả.", "개인의 자율성이 보장되면 근무 환경이 유연해진다.", "Khi tính tự chủ cá nhân được đảm bảo thì môi trường làm việc trở nên linh hoạt.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-아/어져", "Trở nên ... rồi dẫn đến ...; nối sự thay đổi trạng thái với kết quả tiếp theo.", "직장 문화가 유연해져 창의성을 발휘하기 쉬워진다.", "Văn hóa công sở trở nên linh hoạt, nhờ đó việc phát huy sáng tạo trở nên dễ dàng hơn.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-는 데 기여하다", "Góp phần vào việc ...; diễn đạt đóng góp tích cực, thường dùng trong văn viết.", "자율성은 업무 효율을 높이는 데 기여한다.", "Tính tự chủ góp phần nâng cao hiệu suất công việc.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-다 보면", "Nếu cứ .../trong quá trình ... thì dần sẽ ...; nêu hệ quả tích lũy.", "자신의 입장만 생각하다 보면 자율성이 이기주의로 변질될 수 있다.", "Nếu cứ chỉ nghĩ đến lập trường của bản thân thì tính tự chủ có thể biến chất thành chủ nghĩa ích kỷ.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-아/어지다", "Trở nên ...; mô tả sự biến đổi trạng thái hoặc mức độ.", "업무의 자율성이 높아지면 소통이 줄어들 수 있다.", "Khi tính tự chủ trong công việc tăng lên thì giao tiếp có thể giảm đi.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-기 어렵다", "Khó ...; nêu trở ngại trong việc thực hiện hành động.", "소통이 부족하면 합의점을 찾기 어렵다.", "Nếu thiếu giao tiếp thì sẽ khó tìm được điểm thống nhất.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-면서도", "Vừa ... nhưng đồng thời vẫn ...; kết hợp hai đặc điểm/hành động có phần đối lập.", "개인은 자율성을 가지면서도 동료와 협업해야 한다.", "Cá nhân cần có tính tự chủ nhưng đồng thời vẫn phải hợp tác với đồng nghiệp.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-도록 하다", "Khiến/đảm bảo để ...; dùng để nêu yêu cầu hoặc biện pháp hướng đến kết quả.", "구성원 간 원활한 협력이 가능하도록 해야 한다.", "Cần đảm bảo để sự hợp tác giữa các thành viên có thể diễn ra thuận lợi.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
    ("-나아가", "Hơn nữa, xa hơn nữa; từ ý trước mở rộng sang giải pháp hoặc hệ quả ở mức cao hơn.", "나아가 효율적인 의사소통 방안을 마련해야 한다.", "Hơn nữa, cần xây dựng phương án giao tiếp hiệu quả.", "Đề bổ sung – Tính tự chủ cá nhân tại nơi làm việc"),
])


for grammar, usage, example, example_meaning, exam in EXTRA_GRAMMAR:
    TOPIK_54_GRAMMAR.append({"grammar": grammar, "usage": usage, "example": example,
                             "example_meaning": example_meaning, "exam": exam})


# ---------------- Tự động tạo kho học tập cho đề người dùng nhập ----------------
# Phân tích ngoại tuyến bằng từ điển/biểu hiện và mẫu ngữ pháp có sẵn; không gọi API.
AUTO_VOCAB_LEXICON = [
    ("기여하다", "TOPIK 4", "Đóng góp", "지역 경제 발전에 기여하다.", "Đóng góp vào sự phát triển kinh tế địa phương."),
    ("향상시키다", "TOPIK 4", "Nâng cao, cải thiện", "개인의 능력을 향상시킬 수 있다.", "Có thể nâng cao năng lực cá nhân."),
    ("개선하다", "TOPIK 4", "Cải thiện, khắc phục", "문제점을 개선하기 위한 노력이 필요하다.", "Cần nỗ lực để cải thiện các vấn đề."),
    ("증가하다", "TOPIK 3", "Gia tăng", "이용자가 꾸준히 증가하고 있다.", "Số người sử dụng đang tăng đều đặn."),
    ("감소하다", "TOPIK 4", "Giảm sút", "환경오염을 감소시켜야 한다.", "Cần giảm ô nhiễm môi trường."),
    ("발생하다", "TOPIK 3", "Phát sinh, xảy ra", "예상하지 못한 문제가 발생할 수 있다.", "Vấn đề không lường trước có thể phát sinh."),
    ("해결하다", "TOPIK 3", "Giải quyết", "근본적인 원인을 해결해야 한다.", "Cần giải quyết nguyên nhân căn bản."),
    ("활용하다", "TOPIK 4", "Tận dụng, ứng dụng", "기술을 올바르게 활용해야 한다.", "Cần ứng dụng công nghệ đúng cách."),
    ("확대되다", "TOPIK 4", "Được mở rộng, gia tăng quy mô", "참여 기회가 확대되고 있다.", "Cơ hội tham gia đang được mở rộng."),
    ("확산되다", "TOPIK 5", "Lan rộng, phổ biến rộng rãi", "잘못된 정보가 빠르게 확산될 수 있다.", "Thông tin sai lệch có thể lan rộng nhanh chóng."),
    ("초래하다", "TOPIK 5-6", "Gây ra, dẫn đến (thường kết quả tiêu cực)", "지나친 경쟁은 부작용을 초래할 수 있다.", "Cạnh tranh quá mức có thể gây ra tác dụng phụ."),
    ("야기하다", "TOPIK 5-6", "Gây nên, dẫn đến", "사회적 갈등을 야기할 수 있다.", "Có thể gây nên mâu thuẫn xã hội."),
    ("심화되다", "TOPIK 5", "Trở nên sâu sắc/nghiêm trọng hơn", "세대 간 갈등이 심화되고 있다.", "Mâu thuẫn giữa các thế hệ đang trở nên nghiêm trọng hơn."),
    ("완화하다", "TOPIK 5", "Làm dịu, giảm nhẹ", "갈등을 완화하기 위한 대화가 필요하다.", "Cần đối thoại để làm dịu mâu thuẫn."),
    ("촉진하다", "TOPIK 5", "Thúc đẩy", "창의적인 활동은 성장을 촉진한다.", "Hoạt động sáng tạo thúc đẩy sự phát triển."),
    ("저해하다", "TOPIK 6", "Cản trở, gây trở ngại", "과도한 규제는 발전을 저해할 수 있다.", "Quy định quá mức có thể cản trở sự phát triển."),
    ("강화하다", "TOPIK 4-5", "Tăng cường, củng cố", "안전 교육을 강화해야 한다.", "Cần tăng cường giáo dục an toàn."),
    ("보장하다", "TOPIK 4-5", "Đảm bảo", "모든 사람의 권리를 보장해야 한다.", "Cần đảm bảo quyền lợi của tất cả mọi người."),
    ("존중하다", "TOPIK 3-4", "Tôn trọng", "서로의 의견을 존중해야 한다.", "Cần tôn trọng ý kiến của nhau."),
    ("인식하다", "TOPIK 4", "Nhận thức, nhận ra", "문제의 심각성을 인식해야 한다.", "Cần nhận thức được mức độ nghiêm trọng của vấn đề."),
    ("인식 개선", "TOPIK 5", "Cải thiện nhận thức", "사회적 인식 개선이 필요하다.", "Cần cải thiện nhận thức xã hội."),
    ("부작용", "TOPIK 4-5", "Tác dụng phụ, hệ quả tiêu cực", "새로운 제도의 부작용을 살펴야 한다.", "Cần xem xét những hệ quả tiêu cực của chế độ mới."),
    ("불평등", "TOPIK 5", "Bất bình đẳng", "교육 기회의 불평등을 줄여야 한다.", "Cần giảm bất bình đẳng về cơ hội giáo dục."),
    ("격차", "TOPIK 4-5", "Khoảng cách, chênh lệch", "정보 격차를 해소할 필요가 있다.", "Cần thu hẹp khoảng cách thông tin."),
    ("취약 계층", "TOPIK 5", "Tầng lớp/yếu thế dễ bị tổn thương", "취약 계층을 위한 지원이 확대되어야 한다.", "Cần mở rộng hỗ trợ dành cho nhóm yếu thế."),
    ("지속 가능하다", "TOPIK 5", "Bền vững, có thể duy trì lâu dài", "지속 가능한 발전을 추구해야 한다.", "Cần theo đuổi sự phát triển bền vững."),
    ("효율성", "TOPIK 5", "Tính hiệu quả", "업무의 효율성을 높일 수 있다.", "Có thể nâng cao hiệu quả công việc."),
    ("불가피하다", "TOPIK 5-6", "Không thể tránh khỏi", "사회 변화에 따른 갈등은 불가피할 수 있다.", "Mâu thuẫn do thay đổi xã hội có thể là điều không thể tránh khỏi."),
    ("대응하다", "TOPIK 4-5", "Ứng phó, đối phó", "변화에 적극적으로 대응해야 한다.", "Cần chủ động ứng phó với sự thay đổi."),
    ("마련하다", "TOPIK 4-5", "Chuẩn bị, xây dựng (biện pháp/chính sách)", "실질적인 대책을 마련해야 한다.", "Cần xây dựng biện pháp thiết thực."),
    ("실천하다", "TOPIK 3-4", "Thực hành, thực hiện", "작은 일부터 실천하는 태도가 중요하다.", "Thái độ bắt đầu thực hiện từ những việc nhỏ rất quan trọng."),
    ("참여하다", "TOPIK 3", "Tham gia", "지역 사회 활동에 참여할 수 있다.", "Có thể tham gia hoạt động cộng đồng địa phương."),
    ("의존하다", "TOPIK 4-5", "Phụ thuộc, dựa dẫm", "기술에 지나치게 의존해서는 안 된다.", "Không nên phụ thuộc quá mức vào công nghệ."),
    ("갈등", "TOPIK 4", "Mâu thuẫn, xung đột", "세대 간 갈등을 줄여야 한다.", "Cần giảm mâu thuẫn giữa các thế hệ."),
    ("책임감", "TOPIK 4", "Tinh thần trách nhiệm", "공동체 의식과 책임감을 길러야 한다.", "Cần bồi dưỡng ý thức cộng đồng và tinh thần trách nhiệm."),
    ("경쟁력", "TOPIK 4-5", "Năng lực cạnh tranh", "국가의 경쟁력을 높이는 데 도움이 된다.", "Có ích trong việc nâng cao năng lực cạnh tranh quốc gia."),
    ("창의성", "TOPIK 4-5", "Tính sáng tạo", "창의성을 발휘할 기회를 제공해야 한다.", "Cần tạo cơ hội để phát huy tính sáng tạo."),
    ("자율성", "TOPIK 5", "Tính tự chủ", "개인의 자율성을 보장해야 한다.", "Cần đảm bảo tính tự chủ của cá nhân."),
    ("만족도", "TOPIK 4", "Mức độ hài lòng", "서비스 만족도를 높일 수 있다.", "Có thể nâng cao mức độ hài lòng với dịch vụ."),
    ("삶의 질", "TOPIK 4-5", "Chất lượng cuộc sống", "궁극적으로 삶의 질을 높일 수 있다.", "Cuối cùng có thể nâng cao chất lượng cuộc sống."),
    ("공공의 이익", "TOPIK 5", "Lợi ích công cộng", "개인의 이익보다 공공의 이익을 고려해야 한다.", "Cần cân nhắc lợi ích công cộng hơn lợi ích cá nhân."),
]

AUTO_Q54_EXPRESSIONS = [
    ("긍정적인 영향을 미치다", "Tạo ảnh hưởng tích cực", "이러한 변화는 지역 사회에 긍정적인 영향을 미친다.", "Sự thay đổi này tạo ảnh hưởng tích cực đến cộng đồng địa phương."),
    ("부정적인 영향을 미치다", "Gây ảnh hưởng tiêu cực", "지나친 사용은 건강에 부정적인 영향을 미칠 수 있다.", "Việc sử dụng quá mức có thể gây ảnh hưởng tiêu cực đến sức khỏe."),
    ("중요한 역할을 하다", "Đóng vai trò quan trọng", "교육은 사회 발전에 중요한 역할을 한다.", "Giáo dục đóng vai trò quan trọng trong sự phát triển xã hội."),
    ("문제점을 개선하다", "Cải thiện những điểm bất cập", "제도의 문제점을 개선할 필요가 있다.", "Cần cải thiện những điểm bất cập của chế độ."),
    ("문제를 해결하다", "Giải quyết vấn đề", "근본적인 원인을 파악해 문제를 해결해야 한다.", "Cần xác định nguyên nhân căn bản để giải quyết vấn đề."),
    ("대책을 마련하다", "Xây dựng biện pháp đối phó", "정부는 실효성 있는 대책을 마련해야 한다.", "Chính phủ cần xây dựng biện pháp có hiệu quả thực tế."),
    ("관심을 기울이다", "Quan tâm, chú ý đến", "사회적 약자에게 더 많은 관심을 기울여야 한다.", "Cần quan tâm nhiều hơn đến những người yếu thế trong xã hội."),
    ("인식을 개선하다", "Cải thiện nhận thức", "꾸준한 교육을 통해 사회적 인식을 개선할 수 있다.", "Có thể cải thiện nhận thức xã hội thông qua giáo dục thường xuyên."),
    ("균형을 이루다", "Đạt được sự cân bằng", "개인의 자유와 공동체의 질서가 균형을 이루어야 한다.", "Tự do cá nhân và trật tự cộng đồng cần đạt được sự cân bằng."),
    ("장점을 극대화하다", "Phát huy tối đa ưu điểm", "새로운 제도의 장점을 극대화해야 한다.", "Cần phát huy tối đa ưu điểm của chế độ mới."),
    ("부작용을 최소화하다", "Giảm thiểu tác dụng phụ", "부작용을 최소화하기 위한 관리가 필요하다.", "Cần quản lý để giảm thiểu tác dụng phụ."),
    ("지속적인 노력이 필요하다", "Cần nỗ lực liên tục", "문제를 근본적으로 해결하려면 지속적인 노력이 필요하다.", "Muốn giải quyết vấn đề từ căn bản thì cần nỗ lực liên tục."),
]

AUTO_Q54_GRAMMAR = [
    ("-기 때문에", "Bởi vì..., do...; nêu nguyên nhân rõ ràng.", "정보가 부족하기 때문에 잘못된 판단을 할 수 있다.", "Vì thiếu thông tin nên có thể đưa ra phán đoán sai lầm.", r"기 때문에|기 때문이다"),
    ("-(으)로 인해", "Do/bởi..., thường dùng trong văn viết để nêu nguyên nhân.", "기술의 발달로 인해 생활이 편리해졌다.", "Do sự phát triển của công nghệ, cuộc sống đã trở nên tiện lợi.", r"로 인해|으로 인해"),
    ("-는 반면(에)", "Trong khi/trái lại; đối chiếu hai mặt hoặc hai đặc điểm.", "편리성이 높아지는 반면 개인정보 유출 위험도 커진다.", "Trong khi tính tiện lợi tăng lên thì nguy cơ rò rỉ thông tin cá nhân cũng lớn hơn.", r"는 반면|은 반면|ㄴ 반면"),
    ("-(으)ㄹ 뿐만 아니라", "Không chỉ... mà còn...; bổ sung ý cùng chiều.", "경제적 이익을 얻을 뿐만 아니라 일자리도 창출할 수 있다.", "Không chỉ thu được lợi ích kinh tế mà còn có thể tạo ra việc làm.", r"뿐만 아니라"),
    ("-에 따라", "Tùy theo/cùng với; diễn tả sự thay đổi tương ứng.", "사회 변화에 따라 새로운 문제가 나타난다.", "Cùng với sự thay đổi xã hội, những vấn đề mới xuất hiện.", r"에 따라"),
    ("-는 데 도움이 되다", "Có ích trong việc...; nêu tác dụng hỗ trợ.", "경험을 쌓는 데 도움이 된다.", "Có ích trong việc tích lũy kinh nghiệm.", r"는 데 도움이 되|는 데 도움을 주"),
    ("-는 데 기여하다", "Góp phần vào việc...; dùng trong văn viết học thuật.", "지역 경제를 활성화하는 데 기여한다.", "Góp phần thúc đẩy kinh tế địa phương.", r"는 데 기여하"),
    ("-(으)ㄹ 수밖에 없다", "Đành phải/không thể không...; kết quả tất yếu.", "문제를 해결하기 위해 협력할 수밖에 없다.", "Để giải quyết vấn đề thì không còn cách nào khác ngoài hợp tác.", r"수밖에 없"),
    ("-도록 하다", "Đảm bảo/khiến cho...; nêu biện pháp hoặc yêu cầu.", "모두가 안전하게 이용할 수 있도록 해야 한다.", "Cần đảm bảo để mọi người có thể sử dụng an toàn.", r"도록 하"),
    ("-지 않도록", "Để không...; nêu biện pháp phòng ngừa.", "같은 문제가 반복되지 않도록 노력해야 한다.", "Cần nỗ lực để vấn đề tương tự không lặp lại.", r"지 않도록"),
    ("-(으)ㄴ/는다면", "Nếu giả sử... thì...; nêu điều kiện giả định.", "이러한 노력이 계속된다면 상황이 나아질 것이다.", "Nếu nỗ lực này tiếp tục thì tình hình sẽ tốt lên.", r"다면|는다면|ㄴ다면"),
    ("-기 위해(서)", "Để..., nhằm mục đích...; nêu mục đích hành động.", "문제를 예방하기 위해 교육을 강화해야 한다.", "Để phòng ngừa vấn đề, cần tăng cường giáo dục.", r"기 위해"),
    ("-는 경향이 있다", "Có xu hướng...; mô tả khuynh hướng chung.", "사람들은 편리한 방법을 선택하는 경향이 있다.", "Mọi người có xu hướng lựa chọn phương pháp tiện lợi.", r"는 경향이 있"),
    ("-게 되다", "Trở nên/dẫn đến việc...; diễn tả sự thay đổi hoặc kết quả.", "사람들이 정보를 쉽게 얻을 수 있게 되었다.", "Mọi người đã có thể tiếp nhận thông tin một cách dễ dàng.", r"게 되"),
    ("-(으)ㄹ수록", "Càng... càng...; biểu thị mức độ tăng tương ứng.", "경쟁이 치열해질수록 스트레스도 커진다.", "Cạnh tranh càng khốc liệt thì căng thẳng cũng càng lớn.", r"수록"),
    ("-아/어야 하다", "Phải/cần...; nêu nghĩa vụ hoặc sự cần thiết.", "개인정보를 안전하게 관리해야 한다.", "Cần quản lý thông tin cá nhân một cách an toàn.", r"아야 하|어야 하|해야 하"),
]


def _auto_term_present(term, text):
    """Nhận diện cả dạng từ điển và một số dạng chia phổ biến trong câu."""
    if term in text:
        return True
    if term.endswith("하다"):
        stem = re.escape(term[:-2])
        endings = r"(?:하다|한다|했다|하며|하여|해|해야|할|하는|한|함|하기|하면|해서|합니다|합니다만|하게|하여야|해야 한다)"
        return re.search(stem + endings, text) is not None
    if term.endswith("되다"):
        stem = re.escape(term[:-2])
        endings = r"(?:되다|된다|되었다|되며|되어|돼|되어야|될|되는|되고|됩니다|됨)"
        return re.search(stem + endings, text) is not None
    return False


def _auto_exam_study_data(exam_title, pairs):
    korean_sentences = [str(pair[0]) for pair in pairs if isinstance(pair, (list, tuple)) and len(pair) >= 2]
    corpus = " ".join(korean_sentences)
    if not corpus.strip():
        return [], [], []
    vocab = []
    seen_vocab = set()
    # Ưu tiên từ trong kho hiện có, vì các mục này đã có cấp độ và nghĩa được biên soạn.
    for item in TOPIK_VOCAB:
        word = str(item.get("word", "")).strip()
        if word and _auto_term_present(word, corpus) and word not in seen_vocab:
            vocab.append({"word": word, "level": item.get("level", "TOPIK 3-6"),
                          "meaning": item.get("meaning", "Xem ngữ cảnh trong câu ví dụ."),
                          "example": next((x for x in korean_sentences if word in x), item.get("example", "")),
                          "example_meaning": item.get("example_meaning", ""), "exam": exam_title})
            seen_vocab.add(word)
    for word, level, meaning, example, example_meaning in AUTO_VOCAB_LEXICON:
        if _auto_term_present(word, corpus) and word not in seen_vocab:
            actual_example = next((x for x in korean_sentences if _auto_term_present(word, x)), example)
            vocab.append({"word": word, "level": level, "meaning": meaning, "example": actual_example,
                          "example_meaning": example_meaning, "exam": exam_title})
            seen_vocab.add(word)
    expressions = []
    for phrase, meaning, example, example_meaning in AUTO_Q54_EXPRESSIONS:
        phrase_core = phrase[:-1] if phrase.endswith("다") else phrase
        if phrase in corpus or phrase_core in corpus:
            actual_example = next((x for x in korean_sentences if phrase in x or phrase_core in x), example)
            expressions.append({"grammar": phrase, "usage": meaning, "example": actual_example,
                                "example_meaning": example_meaning, "exam": exam_title})
    grammar = []
    seen_grammar = set()
    for label, usage, example, example_meaning, pattern in AUTO_Q54_GRAMMAR:
        if re.search(pattern, corpus) and label not in seen_grammar:
            actual_example = next((x for x in korean_sentences if re.search(pattern, x)), example)
            grammar.append({"grammar": label, "usage": usage, "example": actual_example,
                            "example_meaning": example_meaning, "exam": exam_title})
            seen_grammar.add(label)
    return vocab, expressions, grammar


def refresh_auto_study_banks():
    """Tạo/cập nhật mục học tự động cho tất cả đề tự thêm; giữ nguyên mục học gốc."""
    with get_saved_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS auto_exam_study (
            exam_key TEXT PRIMARY KEY,
            vocab_json TEXT NOT NULL,
            expressions_json TEXT NOT NULL,
            grammar_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        rows = conn.execute("SELECT exam_key, title, pairs_json FROM user_exams ORDER BY id").fetchall()
        for row in rows:
            try:
                pairs = json.loads(row["pairs_json"])
            except (TypeError, json.JSONDecodeError):
                pairs = []
            vocab, expressions, grammar = _auto_exam_study_data(row["title"], pairs)
            conn.execute("""INSERT INTO auto_exam_study
                (exam_key, vocab_json, expressions_json, grammar_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(exam_key) DO UPDATE SET
                vocab_json=excluded.vocab_json,
                expressions_json=excluded.expressions_json,
                grammar_json=excluded.grammar_json,
                updated_at=excluded.updated_at""",
                (row["exam_key"], json.dumps(vocab, ensure_ascii=False),
                 json.dumps(expressions, ensure_ascii=False), json.dumps(grammar, ensure_ascii=False),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        study_rows = conn.execute("SELECT vocab_json, expressions_json, grammar_json FROM auto_exam_study").fetchall()
    existing_vocab = {(x.get("word"), x.get("exam")) for x in TOPIK_VOCAB}
    existing_grammar = {(x.get("grammar"), x.get("exam"), x.get("example")) for x in TOPIK_54_GRAMMAR}
    for row in study_rows:
        for item in json.loads(row["vocab_json"] or "[]"):
            key = (item.get("word"), item.get("exam"))
            if key not in existing_vocab:
                TOPIK_VOCAB.append(item); existing_vocab.add(key)
        for field in ("expressions_json", "grammar_json"):
            for item in json.loads(row[field] or "[]"):
                key = (item.get("grammar"), item.get("exam"), item.get("example"))
                if key not in existing_grammar:
                    TOPIK_54_GRAMMAR.append(item); existing_grammar.add(key)


refresh_auto_study_banks()


# ------------------------- Kho từ vựng/ngữ pháp tự nhập bằng JSON -------------------------
def init_custom_study_table() -> None:
    with get_saved_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS custom_study_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            exam TEXT NOT NULL,
            korean TEXT NOT NULL,
            vietnamese TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT '',
            example_kr TEXT NOT NULL DEFAULT '',
            example_vi TEXT NOT NULL DEFAULT '',
            alternatives_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            UNIQUE(item_type, exam, korean, example_kr)
        )""")


def import_study_json(payload: Any) -> int:
    """Nhập bổ sung từ vựng/biểu hiện/ngữ pháp; không ghi đè mục đã có."""
    records = payload if isinstance(payload, list) else [payload]
    added = 0
    init_custom_study_table()
    with get_saved_db() as conn:
        for record in records:
            if not isinstance(record, dict):
                continue
            exam = str(record.get("title") or record.get("exam") or "Dữ liệu tự bổ sung").strip()
            if not exam:
                exam = "Dữ liệu tự bổ sung"
            groups = (
                ("vocab", record.get("vocabulary", record.get("vocab", []))),
                ("expression", record.get("expressions", [])),
                ("grammar", record.get("grammar", [])),
            )
            for item_type, items in groups:
                if isinstance(items, dict):
                    items = [items]
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    korean = str(item.get("korean") or item.get("word") or item.get("pattern") or item.get("grammar") or "").strip()
                    vietnamese = str(item.get("vietnamese") or item.get("meaning") or item.get("usage") or "").strip()
                    example_kr = str(item.get("example_kr") or item.get("example") or "").strip()
                    example_vi = str(item.get("example_vi") or item.get("example_meaning") or item.get("example_vietnamese") or "").strip()
                    level = str(item.get("level") or "").strip()
                    alternatives = item.get("alternatives", item.get("accepted_answers", []))
                    if isinstance(alternatives, str):
                        alternatives = [x.strip() for x in re.split(r"[;/|]", alternatives) if x.strip()]
                    if not isinstance(alternatives, list):
                        alternatives = []
                    alternatives_json = json.dumps([str(x).strip() for x in alternatives if str(x).strip()], ensure_ascii=False)
                    if not korean or not vietnamese:
                        continue
                    cur = conn.execute("""INSERT OR IGNORE INTO custom_study_items
                        (item_type, exam, korean, vietnamese, level, example_kr, example_vi, alternatives_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (item_type, exam, korean, vietnamese, level, example_kr, example_vi,
                         alternatives_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    added += cur.rowcount
    return added


def get_custom_study_items(item_type: str | None = None):
    init_custom_study_table()
    with get_saved_db() as conn:
        if item_type:
            rows = conn.execute("SELECT * FROM custom_study_items WHERE item_type=? ORDER BY exam, id", (item_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM custom_study_items ORDER BY exam, id").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["alternatives"] = json.loads(item.pop("alternatives_json") or "[]")
        except (TypeError, json.JSONDecodeError):
            item["alternatives"] = []
        result.append(item)
    return result


def export_custom_study_items() -> str:
    items = get_custom_study_items()
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        exam = item["exam"]
        grouped.setdefault(exam, {"title": exam, "vocabulary": [], "expressions": [], "grammar": []})
        target_key = {"vocab": "vocabulary", "expression": "expressions", "grammar": "grammar"}.get(item["item_type"])
        if not target_key:
            continue
        obj = {"korean": item["korean"], "vietnamese": item["vietnamese"]}
        if item["level"]:
            obj["level"] = item["level"]
        if item["example_kr"]:
            obj["example_kr"] = item["example_kr"]
        if item["example_vi"]:
            obj["example_vi"] = item["example_vi"]
        if item["alternatives"]:
            obj["alternatives"] = item["alternatives"]
        grouped[exam][target_key].append(obj)
    return json.dumps(list(grouped.values()), ensure_ascii=False, indent=2)


# Các đề bài TOPIK II người học đã gửi nhưng chưa có đầy đủ bài mẫu song ngữ trong ngân hàng câu.
# Được lưu riêng để không tự tạo hoặc thay thế nội dung gốc của người học.
PROMPT_BANK = {
    "Làm việc tại nhà (재택 근무)": [
        ("재택 근무의 장점은 무엇인가?", "Làm việc tại nhà có những ưu điểm gì?"),
        ("재택 근무의 문제점은 무엇인가?", "Làm việc tại nhà có những vấn đề/bất cập gì?"),
        ("재택 근무의 문제를 해결하기 위한 방법에는 어떤 것이 있는가?", "Có những phương pháp nào để giải quyết các vấn đề của hình thức làm việc tại nhà?"),
    ],
    "Trí tuệ nhân tạo (인공지능)": [
        ("인공지능의 긍정적인 영향은 무엇인가?", "Những ảnh hưởng tích cực của trí tuệ nhân tạo là gì?"),
        ("인공지능의 부정적인 영향은 무엇인가?", "Những ảnh hưởng tiêu cực của trí tuệ nhân tạo là gì?"),
        ("인공지능을 올바르게 사용하는 방법은 무엇인가?", "Phương pháp sử dụng trí tuệ nhân tạo đúng đắn là gì?"),
    ],
    "Chữa lành vết thương lòng (마음의 상처)": [
        ("언제 마음의 상처를 받는가?", "Khi nào chúng ta bị tổn thương tinh thần?"),
        ("어떤 사람들이 마음의 상처를 잘 회복하지 못하는가?", "Những người như thế nào thường khó hồi phục vết thương lòng?"),
        ("마음의 상처를 잘 회복하기 위해 어떤 노력이 필요한가?", "Cần nỗ lực như thế nào để hồi phục tốt những tổn thương tinh thần?"),
    ],
    "Động viên và khích lệ (격려와 응원)": [
        ("사람들은 언제 격려와 응원을 하는가?", "Mọi người thường động viên và khích lệ khi nào?"),
        ("도움이 되지 않는 격려와 응원은 어떤 것인가?", "Những lời động viên, khích lệ không có ích là những lời như thế nào?"),
        ("상대방에게 올바르게 격려와 응원을 하려면 어떻게 해야 하는가?", "Cần làm thế nào để động viên và khích lệ người khác một cách phù hợp?"),
    ],
    "Phân biệt đối xử (차별)": [
        ("차별에는 어떤 유형이 있는가?", "Có những loại hình phân biệt đối xử nào?"),
        ("차별로 인해 어떤 사회적 문제가 발생하는가?", "Những vấn đề xã hội nào phát sinh do phân biệt đối xử?"),
        ("차별 문제를 해결하기 위해 어떤 노력이 필요한가?", "Cần có những nỗ lực nào để giải quyết vấn đề phân biệt đối xử?"),
    ],
    "Lựa chọn nghề nghiệp và trải nghiệm nghề nghiệp (진로 선택)": [
        ("청소년들은 진로 선택 과정에 어떤 어려움을 겪을까?", "Thanh thiếu niên gặp những khó khăn gì trong quá trình lựa chọn nghề nghiệp?"),
        ("직업 체험 교육은 청소년들에게 어떤 도움을 줄까?", "Giáo dục trải nghiệm nghề nghiệp mang lại những lợi ích gì cho thanh thiếu niên?"),
        ("학교는 의미 있는 직업 체험 교육을 하기 위해 어떻게 해야 할까?", "Nhà trường cần làm gì để tổ chức hoạt động giáo dục trải nghiệm nghề nghiệp có ý nghĩa?"),
    ],
    "Truyền thông đại chúng và thanh thiếu niên (대중 매체)": [
        ("청소년이 대중 매체를 통해 얻을 수 있는 것은 무엇인가?", "Thanh thiếu niên có thể nhận được những gì thông qua phương tiện truyền thông đại chúng?"),
        ("대중 매체가 청소년의 가치관에 미치는 부정적인 영향은 무엇인가?", "Phương tiện truyền thông đại chúng gây ra những ảnh hưởng tiêu cực nào đối với hệ giá trị của thanh thiếu niên?"),
        ("청소년이 대중 매체를 대할 때 가져야 할 바람직한 태도는 무엇인가?", "Thanh thiếu niên cần có thái độ phù hợp như thế nào khi tiếp nhận phương tiện truyền thông đại chúng?"),
    ],
    "Ảnh hưởng của thời tiết (날씨가 사람들의 생활에 미치는 영향)": [
        ("날씨는 사람들의 건강에 어떤 영향을 미치는가?", "Thời tiết ảnh hưởng như thế nào đến sức khỏe con người?"),
        ("날씨는 사람들의 경제 활동에 어떤 영향을 미치는가?", "Thời tiết ảnh hưởng như thế nào đến hoạt động kinh tế của con người?"),
        ("사람들은 날씨 변화에 어떻게 대처해야 하는가?", "Con người cần ứng phó với sự thay đổi của thời tiết như thế nào?"),
    ],
}


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
    st.markdown("### 📖 Bản dịch tham khảo")
    st.write(result.get("revised_translation", "Chưa có bản dịch tham khảo."))
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

    alternatives = result.get("other_valid_translations", [])
    if alternatives:
        st.markdown("**Các cách dịch khác có thể chấp nhận:**")
        for alt in alternatives:
            st.write(f"• {alt}")

    vocab = result.get("vocabulary_notes", [])
    if vocab:
        st.markdown("### Từ vựng cần ghi nhớ")
        for item in vocab:
            st.write(
                f"**{item.get('korean', '')}** — {item.get('meaning', '')}. "
                f"{item.get('note', '')}"
            )

    grammar = result.get("grammar_notes", [])
    if grammar:
        st.markdown("### Ngữ pháp cần ghi nhớ")
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
MENU_SAVED = "⭐ Sổ câu đã lưu"
MENU_ADD_EXAM = "➕ Tự thêm đề TOPIK"
MENU_PRACTICE_VOCAB = "🧠 Kiểm tra từ vựng Việt → Hàn"
MENU_PRACTICE_EXAMPLE = "📝 Luyện dịch ví dụ Hàn → Việt"
MENU_IMPORT_STUDY = "📥 Nhập/xuất kho học tập JSON"

menu = st.sidebar.radio(
    "📂 Chọn chế độ",
    [MENU_K2V, MENU_V2K, MENU_VOCAB, MENU_GRAMMAR, MENU_PRACTICE_VOCAB,
     MENU_PRACTICE_EXAMPLE, MENU_IMPORT_STUDY, "📑 Kho đề bài TOPIK đã gửi",
     "🧑‍🎓 Chấm câu tự nhập", MENU_SAVED, MENU_ADD_EXAM],
)

if "question_index_k2v" not in st.session_state:
    st.session_state.question_index_k2v = 0
if "question_index_v2k" not in st.session_state:
    st.session_state.question_index_v2k = 0

def render_full_exam_reference(exam: Dict[str, Any], exam_slug: str) -> None:
    """Ẩn bản dịch toàn bài mặc định; chỉ hiện khi người học chủ động bấm nút."""
    state_key = f"show_full_reference_{exam_slug}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    is_visible = st.session_state[state_key]
    button_label = "🙈 Ẩn bản dịch toàn bài" if is_visible else "👁️ Xem bản dịch toàn bài (không hiện khi luyện dịch)"
    if st.button(button_label, key=f"toggle_full_reference_{exam_slug}", use_container_width=True):
        st.session_state[state_key] = not is_visible
        st.rerun()

    if st.session_state[state_key]:
        with st.container(border=True):
            st.markdown("### 📖 Bản dịch tham khảo toàn bài")
            st.caption("Bản dịch được hiển thị theo từng câu Hàn – Việt để bạn nắm mạch nội dung tổng thể.")
            for number, pair in enumerate(exam["kr_vi"], start=1):
                st.markdown(f"**Câu {number}.** {pair['source']}")
                pronunciation_player(pair["source"], f"full_reference_{exam_slug}_{number}")
                st.write(pair["target"])
                if number < len(exam["kr_vi"]):
                    st.divider()


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
    render_full_exam_reference(exam, exam_slug)
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

def _normalize_study_answer(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[\s\u3000]+", "", value)
    value = re.sub(r"[.,!?;:，。！？、·()\[\]{}]", "", value)
    return value


def _combined_vocab_bank():
    bank = []
    for item in TOPIK_VOCAB:
        bank.append({
            "korean": item.get("word", ""), "vietnamese": item.get("meaning", ""),
            "level": item.get("level", ""), "example_kr": item.get("example", ""),
            "example_vi": item.get("example_meaning", ""), "exam": item.get("exam", "Từ vựng có sẵn"),
            "alternatives": item.get("alternatives", []),
        })
    for item in get_custom_study_items("vocab"):
        bank.append({**item, "exam": item.get("exam", "Dữ liệu tự bổ sung")})
    unique = {}
    for item in bank:
        key = (_normalize_study_answer(item.get("korean")), item.get("exam"), item.get("vietnamese"))
        if key[0] and key not in unique:
            unique[key] = item
    return list(unique.values())


def _combined_example_bank():
    bank = []
    for item in TOPIK_54_GRAMMAR:
        if item.get("example") and item.get("example_meaning"):
            bank.append({"korean": item["example"], "vietnamese": item["example_meaning"],
                         "label": item.get("grammar", "Biểu hiện/ngữ pháp"),
                         "exam": item.get("exam", "Ngữ pháp có sẵn")})
    for item in get_custom_study_items():
        if item.get("item_type") in ("expression", "grammar") and item.get("example_kr") and item.get("example_vi"):
            bank.append({"korean": item["example_kr"], "vietnamese": item["example_vi"],
                         "label": item.get("korean", "Ví dụ"), "exam": item.get("exam", "Dữ liệu tự bổ sung")})
    unique = {}
    for item in bank:
        key = (_normalize_study_answer(item["korean"]), item["exam"])
        if key[0] and key not in unique:
            unique[key] = item
    return list(unique.values())


def show_vocab_recall_quiz():
    st.subheader(MENU_PRACTICE_VOCAB)
    bank = _combined_vocab_bank()
    if not bank:
        st.info("Chưa có từ vựng để luyện.")
        return
    exam_options = ["Tất cả các đề"] + sorted({x.get("exam", "") for x in bank if x.get("exam")})
    exam_filter = st.selectbox("Lọc theo đề", exam_options, key="recall_vocab_exam")
    level_options = sorted({x.get("level", "") for x in bank if x.get("level")})
    level_filter = st.multiselect("Lọc cấp độ", level_options, default=level_options, key="recall_vocab_level")
    selected = [x for x in bank if (exam_filter == "Tất cả các đề" or x.get("exam") == exam_filter)
                and (not x.get("level") or not level_filter or x.get("level") in level_filter)]
    if not selected:
        st.warning("Không có từ phù hợp với bộ lọc.")
        return
    state_key = "vocab_recall_index"
    st.session_state.setdefault(state_key, 0)
    idx = st.session_state[state_key] % len(selected)
    item = selected[idx]
    st.caption(f"{idx + 1}/{len(selected)} · {item.get('exam', '')} · {item.get('level', 'Không ghi cấp độ')}")
    st.info(f"**Nghĩa tiếng Việt:** {item['vietnamese']}")
    answer = st.text_input("Nhập từ/cụm từ tiếng Hàn", key=f"vocab_recall_answer_{idx}_{item['korean']}")
    result_key = f"vocab_recall_result_{idx}_{item['korean']}"
    if st.button("Kiểm tra từ vựng", type="primary", key=f"check_vocab_recall_{idx}_{item['korean']}"):
        accepted = [item["korean"]] + list(item.get("alternatives", []))
        correct = any(_normalize_study_answer(answer) == _normalize_study_answer(x) for x in accepted if x)
        st.session_state[result_key] = {"correct": correct, "answer": answer.strip()}
    result = st.session_state.get(result_key)
    if result:
        if result["correct"]:
            st.success("Chính xác! Bạn đã nhớ đúng từ vựng.")
        else:
            st.warning("Chưa chính xác. Hãy xem đáp án và thử ghi nhớ lại.")
        st.markdown(f"**Đáp án:** {item['korean']}")
        pronunciation_player(item["korean"], f"recall_vocab_audio_{idx}")
        if item.get("example_kr"):
            st.markdown(f"**Ví dụ:** {item['example_kr']}")
            if item.get("example_vi"):
                st.write(item["example_vi"])
            pronunciation_player(item["example_kr"], f"recall_vocab_example_{idx}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ Từ tiếp theo", key=f"next_vocab_recall_{idx}"):
            st.session_state[state_key] = (idx + 1) % len(selected)
            st.rerun()
    with col2:
        if st.button("🔀 Trộn và bắt đầu lại", key="shuffle_vocab_recall"):
            st.session_state[state_key] = 0
            st.rerun()


def show_example_translation_quiz():
    st.subheader(MENU_PRACTICE_EXAMPLE)
    bank = _combined_example_bank()
    if not bank:
        st.info("Chưa có câu ví dụ song ngữ. Hãy nhập dữ liệu JSON có example_kr và example_vi.")
        return
    exam_options = ["Tất cả các đề"] + sorted({x.get("exam", "") for x in bank if x.get("exam")})
    exam_filter = st.selectbox("Lọc theo đề", exam_options, key="example_quiz_exam")
    selected = [x for x in bank if exam_filter == "Tất cả các đề" or x.get("exam") == exam_filter]
    state_key = "example_translation_index"
    st.session_state.setdefault(state_key, 0)
    idx = st.session_state[state_key] % len(selected)
    item = selected[idx]
    st.caption(f"{idx + 1}/{len(selected)} · {item.get('exam', '')} · {item.get('label', '')}")
    st.info(f"**Câu tiếng Hàn:**\n\n{item['korean']}")
    pronunciation_player(item["korean"], f"example_quiz_audio_{idx}")
    answer = st.text_area("Tự dịch câu này sang tiếng Việt", key=f"example_quiz_answer_{idx}_{item['korean']}", height=110)
    result_key = f"example_quiz_result_{idx}_{item['korean']}"
    if st.button("📊 Kiểm tra bản dịch", type="primary", key=f"check_example_quiz_{idx}_{item['korean']}"):
        if not answer.strip():
            st.warning("Bạn hãy nhập bản dịch trước khi kiểm tra.")
        else:
            with st.spinner("Đang đối chiếu bản dịch với đáp án tham khảo..."):
                st.session_state[result_key] = evaluate_translation("kr_vi", item["korean"], answer.strip(), item["vietnamese"], "offline")
    result = st.session_state.get(result_key)
    if result:
        render_evaluation(result, "kr_vi")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➡️ Câu tiếp theo", key=f"next_example_quiz_{idx}"):
            st.session_state[state_key] = (idx + 1) % len(selected)
            st.rerun()
    with col2:
        if st.button("🔄 Bắt đầu lại", key="reset_example_quiz"):
            st.session_state[state_key] = 0
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

elif menu == MENU_PRACTICE_VOCAB:
    show_vocab_recall_quiz()

elif menu == MENU_PRACTICE_EXAMPLE:
    show_example_translation_quiz()

elif menu == MENU_IMPORT_STUDY:
    st.subheader(MENU_IMPORT_STUDY)
    st.caption("Nhập bổ sung từ vựng, biểu hiện và ngữ pháp từ JSON. Dữ liệu cũ được giữ nguyên; mục trùng hoàn toàn sẽ tự động bỏ qua.")
    st.markdown("**Định dạng hỗ trợ:** mỗi đề có `title`, `vocabulary`, `expressions`, `grammar`; mỗi mục cần tiếng Hàn và nghĩa tiếng Việt. Câu ví dụ dùng `example_kr` và `example_vi`.")
    uploaded_study_json = st.file_uploader("Chọn file dữ liệu học tập JSON", type=["json"], key="custom_study_json_upload")
    if uploaded_study_json is not None and st.button("📥 Nhập bổ sung dữ liệu", type="primary", key="import_custom_study_json"):
        try:
            payload = json.loads(uploaded_study_json.getvalue().decode("utf-8-sig"))
            count = import_study_json(payload)
            st.success(f"Đã thêm {count} mục mới. Các mục trùng dữ liệu được tự động bỏ qua.")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể nhập JSON: {exc}")
    custom_items = get_custom_study_items()
    st.metric("Số mục tự nhập đã lưu", len(custom_items))
    if custom_items:
        st.download_button("⬇️ Xuất toàn bộ kho dữ liệu tự nhập (JSON)",
                           data=export_custom_study_items(), file_name="kho_tu_vung_bieu_hien_ngu_phap_TOPIK.json",
                           mime="application/json", use_container_width=True)
        for item in custom_items:
            with st.expander(f"{item['exam']} · {item['korean']} ({item['item_type']})"):
                st.write(item["vietnamese"])
                if item.get("example_kr"):
                    st.markdown(f"**Ví dụ:** {item['example_kr']}")
                    st.write(item.get("example_vi", ""))

elif menu == "📑 Kho đề bài TOPIK đã gửi":
    st.subheader("📑 Kho đề bài TOPIK II đã gửi")
    st.caption("Các đề có đủ bài song ngữ nằm trong hai mục luyện dịch. Mục này lưu riêng những đề bài hiện mới có câu hỏi, chưa có đầy đủ bài mẫu song ngữ để đưa vào luyện dịch từng câu.")
    for topic, questions in PROMPT_BANK.items():
        with st.expander(topic):
            for korean, vietnamese in questions:
                st.markdown(f"**{korean}**")
                st.write(vietnamese)
                pronunciation_player(korean, "prompt_" + str(abs(hash(korean))))

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

    save_col, compare_col = st.columns(2)
    with save_col:
        if st.button("⭐ Lưu câu nguồn + bản dịch tham khảo", key="save_custom_translation", use_container_width=True):
            if not source.strip():
                st.warning("Bạn cần nhập câu nguồn trước khi lưu.")
            elif not reference.strip():
                st.warning("Bạn cần nhập bản dịch tham khảo để lưu cùng câu nguồn.")
            else:
                save_custom_translation(direction, source, reference)
                st.success("Đã lưu câu nguồn và bản dịch tham khảo vào Sổ câu đã lưu.")
    with compare_col:
        compare_clicked = st.button("📊 Đối chiếu câu tự nhập", type="primary", use_container_width=True)
    if compare_clicked:
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

elif menu == MENU_ADD_EXAM:
    st.subheader("➕ Tự tạo và quản lý đề TOPIK")
    st.caption("Mỗi đề cần có tên và ít nhất một cặp câu Hàn–Việt. Các đề tự tạo được lưu trong SQLite, không làm thay đổi đề gốc.")

    with st.expander("🆕 Tạo một đề mới", expanded=True):
        with st.form("create_user_exam_form", clear_on_submit=True):
            new_title = st.text_input("Tên chủ đề / tên đề", placeholder="Ví dụ: Tầm quan trọng của việc đọc sách")
            first_korean = st.text_area("Câu tiếng Hàn đầu tiên", height=90, placeholder="현대 사회에서 독서는 중요한 역할을 한다.")
            first_vietnamese = st.text_area("Bản dịch tiếng Việt", height=90, placeholder="Trong xã hội hiện đại, việc đọc sách đóng vai trò quan trọng.")
            create_clicked = st.form_submit_button("💾 Tạo và lưu đề", type="primary", use_container_width=True)
        if create_clicked:
            try:
                created_key = create_user_exam(new_title, first_korean, first_vietnamese)
                st.success(f"Đã tạo {created_key}. Bạn có thể tiếp tục thêm câu ở phần quản lý bên dưới.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("#### 📚 Các đề do bạn tự thêm")
    user_exam_records = get_user_exams()
    if not user_exam_records:
        st.info("Bạn chưa tạo đề nào. Hãy tạo đề đầu tiên ở phía trên.")
    else:
        st.caption(f"Hiện có {len(user_exam_records)} đề tự tạo. Sau khi lưu, đề sẽ xuất hiện tự động trong hai mục luyện dịch.")
        for saved_exam in user_exam_records:
            exam_id = saved_exam["id"]
            with st.expander(f"{saved_exam['exam_key']} · {len(saved_exam['pairs'])} câu"):
                st.caption(f"Cập nhật lần cuối: {saved_exam['updated_at']}")
                with st.form(f"add_pair_form_{exam_id}", clear_on_submit=True):
                    add_kr = st.text_area("Thêm câu tiếng Hàn", height=80, key=f"add_kr_{exam_id}")
                    add_vi = st.text_area("Thêm bản dịch tiếng Việt", height=80, key=f"add_vi_{exam_id}")
                    add_clicked = st.form_submit_button("➕ Thêm câu vào đề này", use_container_width=True)
                if add_clicked:
                    try:
                        add_pair_to_user_exam(exam_id, add_kr, add_vi)
                        st.success("Đã thêm câu vào đề.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

                for pair_index, pair in enumerate(saved_exam["pairs"]):
                    with st.container(border=True):
                        st.markdown(f"**Câu {pair_index + 1}**")
                        with st.form(f"edit_pair_form_{exam_id}_{pair_index}"):
                            edited_kr = st.text_area("Câu tiếng Hàn", value=pair[0], height=75, key=f"edit_kr_{exam_id}_{pair_index}")
                            edited_vi = st.text_area("Bản dịch tiếng Việt", value=pair[1], height=75, key=f"edit_vi_{exam_id}_{pair_index}")
                            edit_col, remove_col = st.columns(2)
                            with edit_col:
                                edit_clicked = st.form_submit_button("💾 Lưu chỉnh sửa", use_container_width=True)
                            with remove_col:
                                remove_clicked = st.form_submit_button("🗑️ Xóa cặp câu", use_container_width=True)
                        if edit_clicked:
                            try:
                                update_pair_in_user_exam(exam_id, pair_index, edited_kr, edited_vi)
                                st.success("Đã cập nhật câu.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
                        if remove_clicked:
                            delete_pair_from_user_exam(exam_id, pair_index)
                            st.rerun()

                col_export, col_delete = st.columns(2)
                with col_export:
                    one_exam_json = json.dumps({"title": saved_exam["title"], "pairs": saved_exam["pairs"]}, ensure_ascii=False, indent=2)
                    st.download_button(
                        "⬇️ Xuất đề này (JSON)", data=one_exam_json,
                        file_name=f"de_TOPIK_tu_them_{exam_id}.json", mime="application/json",
                        key=f"export_user_exam_{exam_id}", use_container_width=True,
                    )
                with col_delete:
                    if st.button("🗑️ Xóa toàn bộ đề này", key=f"delete_exam_{exam_id}", use_container_width=True):
                        delete_user_exam(exam_id)
                        st.rerun()

    st.divider()
    st.markdown("#### 📥 Nhập đề từ bản sao lưu JSON")
    st.caption("Sau khi nhập, ứng dụng tự phân tích câu tiếng Hàn để bổ sung từ vựng TOPIK 3–6, biểu hiện và ngữ pháp câu 54 theo từng đề. Phân loại dùng từ điển/quy tắc ngoại tuyến nên cấp độ từ vựng mang tính tham khảo.")
    uploaded_exam_backup = st.file_uploader("Chọn tệp JSON đã xuất từ app", type=["json"], key="user_exam_backup")
    if uploaded_exam_backup is not None and st.button("Nhập các đề trong tệp", key="import_user_exam_backup"):
        try:
            backup = json.loads(uploaded_exam_backup.getvalue().decode("utf-8"))
            records = backup if isinstance(backup, list) else [backup]
            restored = import_user_exams(records)
            st.success(f"Đã nhập {restored} đề mới. Những đề trùng tên được bỏ qua.")
            st.info("Kho từ vựng, biểu hiện và ngữ pháp sẽ được tự động cập nhật theo nội dung từng đề khi ứng dụng tải lại.")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể nhập tệp JSON: {exc}")

elif menu == MENU_SAVED:
    st.subheader("⭐ Sổ câu dịch đã lưu")
    st.caption("Lưu và xem lại câu nguồn cùng bản dịch tham khảo ở cả hai chiều Hàn–Việt và Việt–Hàn.")
    saved_items = get_custom_translations()
    st.metric("Tổng số câu đã lưu", len(saved_items))
    if saved_items:
        export_data = json.dumps(saved_items, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Tải bản sao lưu các câu đã lưu (JSON)",
            data=export_data,
            file_name="so_cau_dich_TOPIK_da_luu.json",
            mime="application/json",
            use_container_width=True,
        )
    uploaded_backup = st.file_uploader("Khôi phục câu đã lưu từ file JSON", type=["json"], key="saved_translation_backup")
    if uploaded_backup is not None and st.button("📥 Nhập dữ liệu từ bản sao lưu", key="import_saved_translations"):
        try:
            backup_records = json.loads(uploaded_backup.getvalue().decode("utf-8"))
            if not isinstance(backup_records, list):
                raise ValueError("Tệp JSON cần chứa danh sách các câu đã lưu.")
            restored = import_custom_translations(backup_records)
            st.success(f"Đã khôi phục {restored} câu hợp lệ.")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể đọc bản sao lưu: {exc}")

    if not saved_items:
        st.info("Chưa có câu nào được lưu. Hãy vào mục Luyện dịch với câu tự chọn, nhập câu nguồn và bản dịch tham khảo rồi nhấn nút Lưu.")
    else:
        filter_direction = st.selectbox("Lọc chiều dịch", ["Tất cả", "Hàn ➡️ Việt", "Việt ➡️ Hàn"], key="saved_translation_filter")
        for item in saved_items:
            label = "Hàn ➡️ Việt" if item["direction"] == "kr_vi" else "Việt ➡️ Hàn"
            if filter_direction != "Tất cả" and filter_direction != label:
                continue
            with st.expander(f"{label} · {item['created_at']} · {item['source'][:55]}"):
                st.markdown("**Câu nguồn:**")
                st.write(item["source"])
                st.markdown("**Bản dịch tham khảo:**")
                st.write(item["translation"])
                if item["direction"] == "kr_vi":
                    pronunciation_player(item["source"], f"saved_source_{item['id']}")
                else:
                    pronunciation_player(item["translation"], f"saved_translation_{item['id']}")
                if st.button("🗑️ Xóa câu này", key=f"delete_saved_{item['id']}"):
                    delete_custom_translation(item["id"])
                    st.success("Đã xóa câu khỏi sổ lưu.")
                    st.rerun()

st.divider()
st.caption(
    "Ứng dụng không sử dụng API trả phí. Điểm đối chiếu từ khóa chỉ mang tính tham khảo; "
    "các cách dịch đồng nghĩa có thể không được nhận diện tự động. Hãy kiểm tra bản dịch theo ngữ cảnh."
)
