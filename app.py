"""週報・月報作成アプリ - Activity Tracker"""
import streamlit as st
import sqlite3
import json
from datetime import date, timedelta
from pathlib import Path

# ページ設定
st.set_page_config(
    page_title="Activity Tracker",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# データベースパス
DB_PATH = Path(__file__).parent / "data" / "activities.db"

# カテゴリ定義
CATEGORIES = {
    "meeting": "🤝 ミーティング・コミュニケーション",
    "development": "💻 開発・実装",
    "investigation": "🔍 調査・分析",
    "document": "📄 ドキュメント作成",
    "review": "👀 レビュー",
    "learning": "📚 学習・研修",
    "support": "🙋 サポート・問い合わせ対応",
    "operation": "🔧 運用・保守",
    "other": "📌 その他",
}

# カテゴリ別の詳細入力ヒント（思い出す質問）
CATEGORY_HINTS = {
    "meeting": "💡 誰と？何について話した？決まったこと・次のアクションは？",
    "development": "💡 何を実装した？どこまで進んだ？残タスク・課題は？",
    "investigation": "💡 何を調べた？結果・わかったことは？次どうする？",
    "document": "💡 何のドキュメント？完成度は？誰に共有した？",
    "review": "💡 何をレビューした？指摘・フィードバックは？",
    "learning": "💡 何を学んだ？どう活かせそう？",
    "support": "💡 誰から何の問い合わせ？どう対応した？解決した？",
    "operation": "💡 何の作業？完了した？気づいたことは？",
    "other": "💡 何をした？誰と？結果は？",
}

# 工程→カテゴリのマッピング（1列目のアンダースコア右の値で判定）
PROCESS_TO_CATEGORY = {
    # 開発系
    "開発Design": "investigation",
    "開発Build": "development",
    # 保守系
    "保守問合せ対応": "support",
    "保守その他": "operation",
    "国分業務障害対応": "support",
    # 会議系
    "グループ定例社内打合せ": "meeting",
    "情報交換外出": "meeting",
    # その他
    "卸研ＳＭＴＳ等": "other",
    "ウェビナー社外勉強会部内勉強会": "learning",
    "教育サポート": "other",
    "それ以外すべて": "other",
    # 汎用（旧形式・手入力対応）
    "開発": "development",
    "会議・打合せ": "meeting",
    "運用・保守": "operation",
    "調査": "investigation",
    "レビュー": "review",
    "学習": "learning",
    "サポート": "support",
}


def extract_process_from_code(code: str) -> str:
    """工程コード（D11101_国分業務_...._工程名）から工程名を抽出"""
    if "_" in code:
        return code.split("_")[-1].strip()
    return code.strip()


def init_database():
    """データベースの初期化"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_activity(activity_date: date, category: str, title: str, description: str = "", source: str = "manual"):
    """活動を追加"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO activities (date, category, title, description, source)
        VALUES (?, ?, ?, ?, ?)
    """, (activity_date.isoformat(), category, title, description, source))

    conn.commit()
    conn.close()


def get_activities(start_date: date, end_date: date):
    """期間内の活動を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, date, category, title, description, source, created_at
        FROM activities
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, created_at DESC
    """, (start_date.isoformat(), end_date.isoformat()))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "date": row[1],
            "category": row[2],
            "title": row[3],
            "description": row[4],
            "source": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def delete_activity(activity_id: int):
    """活動を削除"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    conn.commit()
    conn.close()


def update_activity(activity_id: int, activity_date: date, category: str, title: str, description: str = ""):
    """活動を更新"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE activities
        SET date = ?, category = ?, title = ?, description = ?
        WHERE id = ?
    """, (activity_date.isoformat(), category, title, description, activity_id))
    conn.commit()
    conn.close()


def get_activity_by_id(activity_id: int):
    """IDで活動を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, date, category, title, description
        FROM activities WHERE id = ?
    """, (activity_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "date": row[1],
            "category": row[2],
            "title": row[3],
            "description": row[4],
        }
    return None


def get_all_activities():
    """全ての活動を取得（エクスポート用）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, category, title, description, source
        FROM activities
        ORDER BY date DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "date": row[0],
            "category": row[1],
            "title": row[2],
            "description": row[3],
            "source": row[4],
        }
        for row in rows
    ]


def import_activities(activities: list):
    """活動をインポート（既存データはクリアして上書き）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM activities")
    for act in activities:
        cursor.execute("""
            INSERT INTO activities (date, category, title, description, source)
            VALUES (?, ?, ?, ?, ?)
        """, (act["date"], act["category"], act["title"], act.get("description", ""), act.get("source", "manual")))
    conn.commit()
    conn.close()
    return len(activities)


def generate_report(activities: list, report_type: str = "weekly"):
    """レポート用のテキストを生成"""
    if not activities:
        return "該当期間の活動がありません。"

    # カテゴリ別にグループ化
    grouped = {}
    for activity in activities:
        cat = activity["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(activity)

    # レポート生成
    lines = []
    period = "今週" if report_type == "weekly" else "今月"
    lines.append(f"【{period}の活動サマリー】\n")

    for cat_key, cat_label in CATEGORIES.items():
        if cat_key in grouped:
            lines.append(f"\n{cat_label}（{len(grouped[cat_key])}件）")
            for act in grouped[cat_key]:
                lines.append(f"  - {act['date']} {act['title']}")
                if act['description']:
                    lines.append(f"    　{act['description']}")

    return "\n".join(lines)


# データベース初期化
init_database()

# カスタムCSS
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1E3A5F; }
    .sub-header { font-size: 1rem; color: #666; margin-bottom: 1rem; }
    .activity-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #4CAF50;
    }
    .category-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        background: #e3f2fd;
    }
</style>
""", unsafe_allow_html=True)

# サイドバー
with st.sidebar:
    st.markdown("### 📝 Activity Tracker")
    st.markdown("---")

    page = st.radio(
        "メニュー",
        ["📥 活動を記録", "📋 活動一覧", "📊 レポート生成", "💾 データ管理"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("完全無料・ローカル保存")

# メインコンテンツ
st.markdown('<p class="main-header">📝 Activity Tracker</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">週報・月報作成のための活動記録ツール</p>', unsafe_allow_html=True)

if page == "📥 活動を記録":
    tab1, tab2 = st.tabs(["📝 1件ずつ登録", "📋 一括登録"])

    with tab1:
        st.markdown("### 新しい活動を記録")

        with st.form("add_activity_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 2])

            with col1:
                activity_date = st.date_input("日付", value=date.today())
                category = st.selectbox(
                    "カテゴリ",
                    options=list(CATEGORIES.keys()),
                    format_func=lambda x: CATEGORIES[x]
                )

            with col2:
                title = st.text_input("タイトル", placeholder="例: 週次定例ミーティング")
                description = st.text_area(
                    "詳細（任意）",
                    placeholder="例: プロジェクトの進捗確認、来週のタスク割り振り",
                    height=100
                )

            submitted = st.form_submit_button("📥 記録する", type="primary", use_container_width=True)

            if submitted:
                if title:
                    add_activity(activity_date, category, title, description)
                    st.success(f"✅ 「{title}」を記録しました！")
                    st.rerun()
                else:
                    st.warning("タイトルを入力してください")

    with tab2:
        st.markdown("### 一括登録")
        st.caption("工数管理表から「工程」と「作業内容」をまとめてコピペできます")

        bulk_date = st.date_input("日付", value=date.today(), key="bulk_date")

        st.markdown("##### 貼り付け形式")
        paste_format = st.radio(
            "形式を選択",
            ["work_only", "process_work"],
            format_func=lambda x: "作業内容のみ" if x == "work_only" else "工程 + 作業内容（タブ区切り）",
            horizontal=True,
            label_visibility="collapsed"
        )

        if paste_format == "work_only":
            bulk_category = st.selectbox(
                "カテゴリ（全件共通）",
                options=list(CATEGORIES.keys()),
                format_func=lambda x: CATEGORIES[x],
                key="bulk_category"
            )
            bulk_text = st.text_area(
                "作業内容（1行に1件）",
                placeholder="【Databricks】Oracle参照マスタ　資料集め\nFPT社定例\nAIエージェント作成　確認",
                height=200,
                key="bulk_text"
            )
        else:
            st.info("💡 スプレッドシートから「項目コード」「工程」「作業内容」の3列を選択してコピペ")
            bulk_text = st.text_area(
                "項目コード [TAB] 工程 [TAB] 作業内容",
                placeholder="D12102国分業務データ活用_開発Build\t開発\t【Databricks】Oracle参照マスタ　資料集め\nD92201国分業務その他社内会議_グループ定例社内打合せ\t会議・打合せ\tFPT社定例",
                height=200,
                key="bulk_text_with_process"
            )

        if st.button("📥 一括登録", type="primary", use_container_width=True):
            if bulk_text.strip():
                lines = [line.strip() for line in bulk_text.strip().split("\n") if line.strip()]
                count = 0
                for line in lines:
                    if paste_format == "process_work" and "\t" in line:
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            process = extract_process_from_code(parts[0].strip())
                            title = parts[2].strip()
                        elif len(parts) == 2:
                            process = extract_process_from_code(parts[0].strip())
                            title = parts[1].strip()
                        else:
                            process = ""
                            title = line
                        category = PROCESS_TO_CATEGORY.get(process, "other")
                    else:
                        title = line
                        category = bulk_category if paste_format == "work_only" else "other"

                    if title:
                        add_activity(bulk_date, category, title, "", "bulk")
                        count += 1
                st.success(f"✅ {count}件の活動を登録しました！")
                st.rerun()
            else:
                st.warning("作業内容を入力してください")

    # 最近の活動を表示
    st.markdown("---")
    st.markdown("### 最近の記録（直近7日）")

    recent = get_activities(date.today() - timedelta(days=7), date.today())

    if recent:
        for act in recent[:10]:
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.caption(act["date"])
                with col2:
                    st.markdown(f"**{CATEGORIES.get(act['category'], '📌')}** {act['title']}")
                    if act["description"]:
                        st.caption(act["description"])
                with col3:
                    if st.button("🗑️", key=f"del_{act['id']}", help="削除"):
                        delete_activity(act["id"])
                        st.rerun()
    else:
        st.info("まだ記録がありません。上のフォームから活動を記録しましょう！")

elif page == "📋 活動一覧":
    st.markdown("### 活動一覧")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("終了日", value=date.today())

    activities = get_activities(start_date, end_date)

    if activities:
        st.markdown(f"**{len(activities)}件** の活動が見つかりました")

        # カテゴリでフィルタ
        selected_cats = st.multiselect(
            "カテゴリでフィルタ",
            options=list(CATEGORIES.keys()),
            format_func=lambda x: CATEGORIES[x],
            default=list(CATEGORIES.keys())
        )

        filtered = [a for a in activities if a["category"] in selected_cats]

        # 詳細未入力のものを上部に表示するオプション
        no_desc = [a for a in filtered if not a["description"]]
        has_desc = [a for a in filtered if a["description"]]

        if no_desc:
            st.markdown(f"##### 📝 詳細未入力（{len(no_desc)}件）")
            st.caption("Enterで保存。思い出しながら書いてみてください。")

            for act in no_desc:
                with st.container():
                    col1, col2, col3 = st.columns([2, 5, 1])
                    with col1:
                        st.markdown(f"**{act['date']}**")
                        st.caption(CATEGORIES.get(act['category'], '📌'))
                    with col2:
                        st.markdown(f"**{act['title']}**")
                        hint = CATEGORY_HINTS.get(act['category'], "💡 何をした？")
                        st.caption(hint)
                        new_desc = st.text_area(
                            "詳細",
                            value="",
                            key=f"quick_desc_{act['id']}",
                            placeholder="思い出して書く...",
                            height=80,
                            label_visibility="collapsed"
                        )
                        if new_desc:
                            update_activity(act['id'], date.fromisoformat(act['date']), act['category'], act['title'], new_desc)
                            st.rerun()
                    with col3:
                        if st.button("✏️", key=f"edit_{act['id']}", help="全項目編集"):
                            st.session_state.editing_id = act['id']
                            st.rerun()
                    st.markdown("---")

        if has_desc:
            st.markdown(f"##### ✅ 詳細入力済み（{len(has_desc)}件）")

            for act in has_desc:
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(f"""
                    <div class="activity-card">
                        <span class="category-badge">{CATEGORIES.get(act['category'], '📌')}</span>
                        <strong>{act['date']}</strong> - {act['title']}
                        <br><small>{act['description']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("✏️", key=f"edit_{act['id']}", help="編集"):
                        st.session_state.editing_id = act['id']
                        st.rerun()

        # 編集モード
        if "editing_id" in st.session_state and st.session_state.editing_id:
            edit_act = get_activity_by_id(st.session_state.editing_id)
            if edit_act:
                st.markdown("---")
                st.markdown("### ✏️ 活動を編集")

                with st.form("edit_activity_form"):
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        edit_date = st.date_input(
                            "日付",
                            value=date.fromisoformat(edit_act["date"])
                        )
                        cat_keys = list(CATEGORIES.keys())
                        edit_category = st.selectbox(
                            "カテゴリ",
                            options=cat_keys,
                            index=cat_keys.index(edit_act["category"]) if edit_act["category"] in cat_keys else 0,
                            format_func=lambda x: CATEGORIES[x]
                        )

                    with col2:
                        edit_title = st.text_input("タイトル", value=edit_act["title"])
                        edit_description = st.text_area(
                            "詳細（任意）",
                            value=edit_act["description"] or "",
                            height=100
                        )

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        save_btn = st.form_submit_button("💾 保存", type="primary", use_container_width=True)
                    with col2:
                        cancel_btn = st.form_submit_button("キャンセル", use_container_width=True)
                    with col3:
                        delete_btn = st.form_submit_button("🗑️ 削除", use_container_width=True)

                    if save_btn:
                        if edit_title:
                            update_activity(st.session_state.editing_id, edit_date, edit_category, edit_title, edit_description)
                            st.success("✅ 更新しました！")
                            st.session_state.editing_id = None
                            st.rerun()
                        else:
                            st.warning("タイトルを入力してください")

                    if cancel_btn:
                        st.session_state.editing_id = None
                        st.rerun()

                    if delete_btn:
                        delete_activity(st.session_state.editing_id)
                        st.session_state.editing_id = None
                        st.rerun()
    else:
        st.info("該当期間の活動はありません")

elif page == "📊 レポート生成":
    st.markdown("### レポート生成")

    report_type = st.radio(
        "レポート種類",
        ["weekly", "monthly"],
        format_func=lambda x: "📅 週報" if x == "weekly" else "📆 月報",
        horizontal=True
    )

    # 期間を自動計算
    today = date.today()
    if report_type == "weekly":
        start = today - timedelta(days=today.weekday())  # 今週の月曜
        end = today
        period_label = f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')}"
    else:
        start = today.replace(day=1)  # 今月1日
        end = today
        period_label = f"{start.strftime('%Y年%m月')}"

    st.info(f"対象期間: **{period_label}**")

    activities = get_activities(start, end)

    if activities:
        report_text = generate_report(activities, report_type)

        st.markdown("#### 📄 生成されたレポート")
        st.text_area("", value=report_text, height=400, label_visibility="collapsed")

        # コピー用
        st.download_button(
            "📋 テキストファイルとしてダウンロード",
            report_text,
            f"report_{report_type}_{today.isoformat()}.txt",
            "text/plain",
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("#### 📊 統計")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総活動数", f"{len(activities)}件")
        with col2:
            categories_used = len(set(a["category"] for a in activities))
            st.metric("カテゴリ数", f"{categories_used}種類")
        with col3:
            days_active = len(set(a["date"] for a in activities))
            st.metric("活動日数", f"{days_active}日")
    else:
        st.warning("該当期間の活動がありません。先に活動を記録してください。")

elif page == "💾 データ管理":
    st.markdown("### データ管理")
    st.caption("データのエクスポート・インポートでバックアップを管理できます")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📤 エクスポート")
        st.markdown("全ての活動データをJSONファイルとしてダウンロードします。")

        all_activities = get_all_activities()

        if all_activities:
            export_data = {
                "exported_at": date.today().isoformat(),
                "count": len(all_activities),
                "activities": all_activities
            }
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

            st.download_button(
                f"📥 ダウンロード（{len(all_activities)}件）",
                json_str,
                f"activity_backup_{date.today().isoformat()}.json",
                "application/json",
                use_container_width=True,
                type="primary"
            )
            st.success(f"✅ {len(all_activities)}件のデータをエクスポートできます")
        else:
            st.info("エクスポートするデータがありません")

    with col2:
        st.markdown("#### 📥 インポート")
        st.markdown("JSONファイルからデータを復元します。")
        st.warning("⚠️ インポートすると現在のデータは上書きされます")

        uploaded_file = st.file_uploader(
            "JSONファイルを選択",
            type=["json"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            try:
                import_data = json.loads(uploaded_file.read().decode("utf-8"))
                activities_to_import = import_data.get("activities", [])

                st.info(f"📄 {len(activities_to_import)}件のデータが見つかりました")

                if st.button("🔄 インポート実行", type="primary", use_container_width=True):
                    count = import_activities(activities_to_import)
                    st.success(f"✅ {count}件のデータをインポートしました！")
                    st.rerun()

            except json.JSONDecodeError:
                st.error("❌ JSONファイルの形式が正しくありません")
            except Exception as e:
                st.error(f"❌ エラー: {e}")

    st.markdown("---")
    st.markdown("#### 💡 使い方")
    st.markdown("""
    1. **作業終了時**: 「エクスポート」でJSONをダウンロードして保存
    2. **次回作業開始時**: 保存したJSONを「インポート」でアップロード
    3. データが復元され、続きから記録できます
    """)
