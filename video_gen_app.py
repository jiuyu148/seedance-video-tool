"""
Seedance 2.0 视频生成 - 图形界面版
使用方法：pip install streamlit volcengine-python-sdk[ark]
运行：streamlit run video_gen_app.py
"""

import streamlit as st
import os
import time
import json
import datetime
from volcengine.base.ark import Ark

st.set_page_config(page_title="Seedance 2.0 视频生成", page_icon="🎬")

# --- 历史记录存储（保存在脚本同目录下）---
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_history.json")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def add_record(record):
    history = load_history()
    history.insert(0, record)
    save_history(history)

if "history" not in st.session_state:
    st.session_state["history"] = load_history()

# 启动时加载最新成功记录作为预览
if "latest_video" not in st.session_state:
    history = load_history()
    for rec in history:
        if rec.get("status") != "failed" and rec.get("video_url"):
            st.session_state["latest_video"] = rec
            break

st.title("🎬 Seedance 2.0 视频生成工具")

# --- Tab 切换：生成 vs 历史归档 ---
tab1, tab2 = st.tabs(["✨ 生成视频", f"📦 历史归档 ({len(st.session_state['history'])})"])

# --- 最新视频预览（持久显示最新生成的视频）---
if "latest_video" in st.session_state and st.session_state["latest_video"]:
    lv = st.session_state["latest_video"]
    st.markdown("---")
    st.subheader("🎞️ 最新生成的视频")
    col_prev, col_prev2 = st.columns([1, 2])
    with col_prev:
        st.markdown(f"**⏱️ {lv.get('created_at', '')}**")
        st.markdown(f"**🎬 {lv.get('ratio', '-')} · {lv.get('duration', '-')}秒 · {lv.get('resolution', '-')}**")
    with col_prev2:
        st.video(lv["video_url"])
        st.markdown(f"📥 [下载链接]({lv['video_url']})")
    st.markdown("---")

# ========================
# Tab1: 生成视频
# ========================
with tab1:
    # --- 接收从历史归档传来的数据 ---
    if st.session_state.get("load_record"):
        rec = st.session_state["load_record"]
        st.session_state.ref_images = rec.get("reference_images", [""]) or [""]
        st.session_state.prompt_template = rec.get("prompt", "")
        ref_vid = rec.get("reference_video", "")
        st.session_state["_load_ref_video"] = ref_vid if ref_vid else ""
        del st.session_state["load_record"]
        st.success("✅ 已载入历史记录，请检查参数后点击「开始生成」！")

    # --- 提示词优化框架 ---
    st.sidebar.header("📝 提示词优化框架")
    with st.sidebar.expander("💡 Seedance 2.0 提示词规范"):
        st.markdown("""
        **【三段式结构】**

        **1. 全局基础设定**
        - 锁定角色、环境与核心资产
        - 必须使用 @图N 声明映射关系
        - 首尾帧控制

        **2. 时间片分镜脚本**
        - 控制时间层（0-3s, 3-10s）
        - 动作 + 单一运镜
        - @图N 之后必须紧跟指代词

        **3. 画质、风格与约束**
        - 画质增强（4K、高清）
        - 防崩坏约束（面部不变形、无穿模）

        **【运镜限制】**
        - 同一时间切片只允许 1 种运镜方式
        - 禁止同时推拉摇移
        """)

    # --- API Key 配置 ---
    st.sidebar.header("⚙️ 配置")
    api_key = st.sidebar.text_input(
        "ARK API Key",
        type="password",
        value="",  # 留空，部署后请在网页侧边栏填写你的 ARK API Key
        help="在火山引擎控制台获取"
    )
    model_choice = st.sidebar.selectbox("选择模型", [
        "doubao-seedance-2-0-fast-260128",
        "doubao-seedance-2-0-260128"
    ], index=0)

    # --- 参数配置 ---
    st.header("📋 生成参数")

    col1, col2, col3 = st.columns(3)
    with col1:
        ratio = st.selectbox("视频比例", ["1:1", "16:9", "9:16", "4:3", "3:4"], index=0)
    with col2:
        duration = st.selectbox("视频时长", list(range(1, 16)), index=3)
    with col3:
        resolution = st.selectbox("分辨率", ["480p", "720p", "1080p"], index=0)

    generate_audio = st.checkbox("🎵 生成音频", value=True)
    watermark = st.checkbox("💧 添加水印", value=False)

    # --- 参考素材（多图支持）---
    st.header("🖼️ 参考素材")

    if 'ref_images' not in st.session_state:
        st.session_state.ref_images = [""]

    st.markdown("**参考图片（可添加多张，点击➕添加）**")

    ref_image_urls = []
    for i in range(len(st.session_state.ref_images)):
        col_num, col_input, col_del = st.columns([1, 5, 1])
        with col_num:
            st.markdown(f"`@图{i+1}`")
        with col_input:
            img_input = st.text_input(
                f"图片{i+1}链接",
                value=st.session_state.ref_images[i],
                placeholder="https://example.com/image.jpg",
                key=f"img_{i}",
                label_visibility="collapsed"
            )
            ref_image_urls.append(img_input)
        with col_del:
            if len(st.session_state.ref_images) > 1:
                if st.button("❌", key=f"img_del_{i}"):
                    st.session_state.ref_images.pop(i)
                    st.rerun()

    if st.button("➕ 添加图片", key="add_img"):
        st.session_state.ref_images.append("")
        st.rerun()

    # --- 图片预览 ---
    st.markdown("**图片预览：**")
    preview_cols = st.columns(4)
    for i, url in enumerate(ref_image_urls):
        if url and url.strip():
            with preview_cols[i % 4]:
                try:
                    st.image(url, width=150, caption=f"@图{i+1}")
                except:
                    st.warning(f"@图{i+1} 加载失败")

    # --- 参考视频 ---
    st.header("🎬 参考视频")
    reference_video_url = st.text_area(
        "参考视频链接（可留空）",
        value=st.session_state.get("_load_ref_video", ""),
        placeholder="https://example.com/video.mp4",
        help="视频公网链接，不填则只参考图片"
    )

    if reference_video_url and reference_video_url.strip():
        st.markdown("**视频预览：**")
        try:
            st.video(reference_video_url)
        except:
            st.warning("视频加载失败")

    # --- 提示词 ---
    st.header("✏️ 视频描述")

    # 可点击的图片标签
    st.markdown("**🏷️ 快速插入引用（点击插入 @图N）：**")

    active_images = [(i+1, url) for i, url in enumerate(ref_image_urls) if url and url.strip()]

    if active_images:
        cols = st.columns(len(active_images))
        for idx, (num, url) in enumerate(active_images):
            with cols[idx]:
                if st.button(f"@图{num}", key=f"insert_{num}"):
                    current = st.session_state.get("prompt_template", "")
                    st.session_state.prompt_template = current + f"@图{num}"
                    st.rerun()
    else:
        st.info("请先在上方添加参考图片链接")

    # 模板按钮
    st.markdown("**📋 快速模板（点击使用）：**")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        if st.button("🎬 钢铁洪流"):
            st.session_state.prompt_template = """**全局基础设定**
场景：红警2.5D等距俯视角战场
阵营：红方苏联坦克集群 vs 蓝方盟军基地
资产：@图1（红方坦克集群），@图2（蓝方基地建筑）

**时间片分镜脚本**
0-4s: 大量红方坦克从画面右侧涌入，呈楔形突击阵型推进，履带扬起尘土，@图1的坦克碾压一切障碍物
4-8s: 蓝方基地防御激活，电塔发射蓝色闪电拦截，红方坦克集群不顾伤亡继续推进
8-10s: 红方坦克突破防线，涌入蓝方基地，基地建筑被摧毁，爆炸火焰腾起

**画质、风格与约束**
画质：4K高清, 电影级渲染, 逼真细节
风格：gritty realistic sci-fi, Command and Conquer style, weathered heavy metal, dieselpunk
防崩坏：人物面部稳定不变形, 五官清晰, 无穿模, 无肢体错位"""
            st.rerun()

    with col_t2:
        if st.button("⚔️ 基地攻防"):
            st.session_state.prompt_template = """**全局基础设定**
场景：红警2.5D等距俯视角
阵营：红方进攻 vs 蓝方防守
资产：@图1（进攻单位），@图2（防御建筑）

**时间片分镜脚本**
0-3s: 红方单位集结于战场边缘，指挥官下令进攻
3-7s: 蓝方防御建筑开火，战斗激烈，爆炸与火光
7-10s: 攻守转换，战局逆转

**画质、风格与约束**
画质：4K高清, 电影级渲染
风格：gritty realistic sci-fi, Command and Conquer style
防崩坏：无穿模, 无肢体错位"""
            st.rerun()

    with col_t3:
        if st.button("🚗 追逐战斗"):
            st.session_state.prompt_template = """**全局基础设定**
场景：红警2.5D等距俯视角
单位：@图1（追击方），@图2（被追击方）
地形：草地、桥梁、悬崖

**时间片分镜脚本**
0-3s: @图2从画面左侧逃逸，@图1紧追不舍
3-6s: 双方过桥，@图1开始攻击@图2
6-10s: @图2被击中爆炸，@图1获胜离开

**画质、风格与约束**
画质：4K高清, 电影级渲染
风格：gritty realistic sci-fi, Command and Conquer style
防崩坏：无穿模, 爆炸效果逼真"""
            st.rerun()

    default_prompt = st.session_state.get("prompt_template", "")
    user_content = st.text_area(
        "描述你想要生成的视频效果（可使用上方模板或直接编写）",
        value=default_prompt,
        placeholder="按三段式结构编写：全局设定 - 时间分镜 - 画质约束",
        height=250
    )

    # --- 生成按钮 ---
    st.markdown("---")

    if st.button("🚀 开始生成视频", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ 请先填写 API Key")
        elif not user_content:
            st.error("❌ 请填写视频描述")
        elif not any(ref_image_urls):
            st.error("❌ 请至少填写一张参考图片链接")
        else:
            with st.spinner("正在初始化..."):
                os.environ["ARK_API_KEY"] = api_key
                client = Ark(api_key=api_key)

            content = [{"type": "text", "text": user_content}]

            for i, img_url in enumerate(ref_image_urls):
                if img_url and img_url.strip():
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img_url.strip()},
                        "role": "reference_image",
                    })

            if reference_video_url and reference_video_url.strip():
                content.append({
                    "type": "video_url",
                    "video_url": {"url": reference_video_url},
                    "role": "reference_video",
                })

            st.info("⏳ 任务创建中，预计需要 2-5 分钟...")

            try:
                create_result = client.content_generation.tasks.create(
                    model=model_choice,
                    content=content,
                    generate_audio=generate_audio,
                    ratio=ratio,
                    duration=duration,
                    watermark=watermark,
                )

                task_id = create_result.id
                st.success(f"✅ 任务创建成功！ID: {task_id}")
                st.info("🔄 正在轮询任务状态，每30秒刷新一次...")

                progress_bar = st.progress(0)
                status_text = st.empty()

                while True:
                    get_result = client.content_generation.tasks.get(task_id=task_id)
                    status = get_result.status

                    status_text.info(f"当前状态: **{status}**，请等待...")

                    if status == "succeeded":
                        video_url = get_result.content.video_url
                        st.success("🎉 视频生成完成！")
                        st.markdown(f"📥 **下载链接：** [{video_url}]({video_url})")
                        st.video(video_url)
                        progress_bar.progress(100)

                        # 自动归档
                        record = {
                            "task_id": task_id,
                            "video_url": video_url,
                            "prompt": user_content,
                            "model": model_choice,
                            "ratio": ratio,
                            "duration": duration,
                            "resolution": resolution,
                            "generate_audio": generate_audio,
                            "watermark": watermark,
                            "reference_images": [u for u in ref_image_urls if u and u.strip()],
                            "reference_video": reference_video_url.strip() if reference_video_url else "",
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        # 更新最新视频预览
                        st.session_state["latest_video"] = record.copy()
                        add_record(record)
                        st.session_state["history"] = load_history()
                        st.rerun()
                        break

                    elif status == "failed":
                        st.error(f"❌ 任务失败: {get_result.error}")
                        # 失败也归档
                        record = {
                            "task_id": task_id,
                            "prompt": user_content,
                            "model": model_choice,
                            "ratio": ratio,
                            "duration": duration,
                            "resolution": resolution,
                            "generate_audio": generate_audio,
                            "watermark": watermark,
                            "reference_images": [u for u in ref_image_urls if u and u.strip()],
                            "reference_video": reference_video_url.strip() if reference_video_url else "",
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "failed",
                            "error": str(get_result.error),
                        }
                        add_record(record)
                        st.session_state["history"] = load_history()
                        break

                    else:
                        for i in range(30):
                            time.sleep(1)
                            progress_bar.progress(int((i / 30) * 100))
                        progress_bar.progress(0)

            except Exception as e:
                st.error(f"调用失败: {e}")

    # --- 说明 ---
    st.markdown("---")
    with st.expander("📖 使用说明"):
        st.markdown("""
        **参数说明：**
        - 分辨率：480p（快速生成）, 720p（平衡）, 1080p（高清质量）
        - 时长：生成视频的时长（秒）
        - 比例：视频画面比例

        **提示词框架：**
        1. 【全局基础设定】锁定角色、环境、资产映射
        2. 【时间片分镜脚本】分时间段描述动作和运镜
        3. 【画质、风格与约束】质量 + 防崩坏
        """)

# ========================
# Tab2: 历史归档
# ========================
with tab2:
    history = st.session_state["history"]

    if not history:
        st.info("📭 还没有任何生成记录，生成第一个视频后会自动归档到这里～")
    else:
        st.subheader(f"共 {len(history)} 条记录")

        for i, record in enumerate(history):
            with st.container():
                col_a, col_b = st.columns([1, 5])
                with col_a:
                    if record.get("status") == "failed":
                        st.error("❌ 失败")
                    else:
                        st.success("✅ 成功")
                with col_b:
                    st.markdown(f"**⏱️ {record.get('created_at', '未知时间')}**")
                    st.markdown(f"**🎬 {record.get('ratio', '-')} · {record.get('duration', '-')}秒 · {record.get('resolution', '-')} · {record.get('model', '-')}**")
                    st.markdown(f"**📝 {record.get('prompt', '-')[:60]}{'...' if len(record.get('prompt', '')) > 60 else ''}")

                col_c, col_d = st.columns(2)
                with col_c:
                    if record.get("video_url"):
                        st.markdown(f"📥 [下载视频]({record['video_url']})")
                with col_d:
                    imgs = record.get("reference_images", [])
                    if imgs:
                        st.markdown(f"🖼️ 参考图片：**{len(imgs)}** 张")

                if record.get("reference_video"):
                    st.markdown(f"🎞️ 参考视频：{record['reference_video'][:60]}...")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"🔄 重新生成", key=f"load_{i}"):
                        st.session_state["load_record"] = record
                        st.session_state["_active_tab"] = 0
                        st.rerun()
                with col_btn2:
                    if st.button(f"🗑️ 删除", key=f"hist_del_{i}"):
                        history = load_history()
                        if i < len(history):
                            history.pop(i)
                            save_history(history)
                            st.session_state["history"] = history
                            st.rerun()

                st.divider()
