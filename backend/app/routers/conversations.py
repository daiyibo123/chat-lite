"""对话管理：新建 / 列表 / 删除 / 消息列表 / 导出 / 分享。"""
from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_guest_user
from app.models import Conversation, Message, User
from app.schemas import ConversationOut, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

MAX_CONVERSATIONS = 10


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    count = db.query(Conversation).filter(Conversation.user_id == current_user.id).count()
    if count >= MAX_CONVERSATIONS:
        raise HTTPException(
            status_code=409,
            detail=f"对话数量已达上限（{MAX_CONVERSATIONS}个），请先删除一个对话",
        )

    conv = Conversation(user_id=current_user.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("", response_model=List[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(MAX_CONVERSATIONS)
        .all()
    )


@router.delete("/{conv_id}")
def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    db.query(Message).filter(Message.conversation_id == conv.id).delete()
    db.delete(conv)
    db.commit()
    return {"detail": "已删除"}


@router.get("/{conv_id}/messages", response_model=List[MessageOut])
def get_messages(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
        .all()
    )


# ─────────── 消息操作 ────────────────

@router.delete("/{conv_id}/messages/{msg_id}/and-after")
def delete_message_and_after(
    conv_id: int,
    msg_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    """删除指定消息及其之后的所有消息（用于回退重发）。"""
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.id >= msg_id,
    ).delete(synchronize_session=False)
    db.commit()
    return {"detail": "已删除"}


@router.put("/{conv_id}/messages/{msg_id}")
def update_message(
    conv_id: int,
    msg_id: int,
    body: dict,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    """编辑用户消息内容。"""
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    msg = db.query(Message).filter(
        Message.id == msg_id,
        Message.conversation_id == conv_id,
        Message.role == "user",
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    msg.content = body.get("content", msg.content)
    db.commit()
    return {"detail": "已更新"}


# ─────────── 导出辅助 ────────────────

def _get_conv_and_messages(conv_id: int, user: User, db: Session):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
        .all()
    )
    return conv, msgs


def _fmt(dt) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ─────────── 导出 JSON ───────────────

@router.get("/{conv_id}/export/json")
def export_json(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv, msgs = _get_conv_and_messages(conv_id, current_user, db)
    data = {
        "title": conv.title,
        "model": conv.model_name or "",
        "created_at": _fmt(conv.created_at),
        "exported_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": conv.summary or "",
        "messages": [
            {"role": m.role, "content": m.content, "created_at": _fmt(m.created_at)}
            for m in msgs
        ],
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="conversation-{conv_id}.json"'},
    )


# ─────────── 导出 Markdown ───────────

@router.get("/{conv_id}/export/md")
def export_markdown(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv, msgs = _get_conv_and_messages(conv_id, current_user, db)
    lines = []
    lines.append(f"# {conv.title}\n")
    meta = []
    if conv.model_name:
        meta.append(f"模型: {conv.model_name}")
    meta.append(f"创建: {_fmt(conv.created_at)}")
    meta.append(f"导出: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> {' | '.join(meta)}\n")

    if conv.summary:
        lines.append("---\n")
        lines.append(f"**上下文摘要**\n\n{conv.summary}\n")

    lines.append("---\n")
    for m in msgs:
        tag = "🧑 **你**" if m.role == "user" else "🤖 **AI**"
        time_str = _fmt(m.created_at)
        lines.append(f"### {tag}  <sub>{time_str}</sub>\n")
        lines.append(f"{m.content}\n")

    content = "\n".join(lines)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="conversation-{conv_id}.md"'},
    )


# ─────────── 导出 PDF ────────────────

def _find_chinese_font():
    """尝试查找系统中文字体，返回路径或 None。"""
    candidates = [
        # Windows
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


@router.get("/{conv_id}/export/pdf")
def export_pdf(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    conv, msgs = _get_conv_and_messages(conv_id, current_user, db)

    # 注册中文字体
    font_path = _find_chinese_font()
    font_name = "Helvetica"
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
            font_name = "ChineseFont"
        except Exception:
            pass

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm, leftMargin=20 * mm, rightMargin=20 * mm)

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("Title_CN", parent=styles["Title"], fontName=font_name, fontSize=16, leading=22)
    s_meta = ParagraphStyle("Meta_CN", parent=styles["Normal"], fontName=font_name, fontSize=9, textColor="#888888", leading=13)
    s_role = ParagraphStyle("Role_CN", parent=styles["Normal"], fontName=font_name, fontSize=10, textColor="#555555", leading=14, spaceBefore=8)
    s_content = ParagraphStyle("Content_CN", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=16)
    s_summary = ParagraphStyle("Summary_CN", parent=styles["Normal"], fontName=font_name, fontSize=9, textColor="#666666", leading=14, leftIndent=12)

    story = []

    # 标题
    story.append(Paragraph(conv.title, s_title))
    story.append(Spacer(1, 4 * mm))

    # 元信息
    meta_lines = []
    if conv.model_name:
        meta_lines.append("模型: %s" % conv.model_name)
    meta_lines.append("创建: %s" % _fmt(conv.created_at))
    meta_lines.append("导出: %s" % datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    story.append(Paragraph(" | ".join(meta_lines), s_meta))
    story.append(Spacer(1, 6 * mm))

    # Summary
    if conv.summary:
        story.append(Paragraph("[上下文摘要]", s_role))
        # 转义 XML 特殊字符
        safe_summary = (conv.summary
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace("\n", "<br/>"))
        story.append(Paragraph(safe_summary, s_summary))
        story.append(Spacer(1, 4 * mm))

    # 消息
    for m in msgs:
        tag = "你" if m.role == "user" else "AI"
        time_str = _fmt(m.created_at)
        story.append(Paragraph("%s  <font size=8 color='#aaa'>%s</font>" % (tag, time_str), s_role))
        safe_content = (m.content
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace("\n", "<br/>"))
        story.append(Paragraph(safe_content, s_content))

    doc.build(story)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="conversation-{conv_id}.pdf"'},
    )


# ─────────── 分享 ────────────────────

@router.post("/{conv_id}/share")
def share_conversation(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if not conv.share_id:
        conv.share_id = uuid.uuid4().hex[:12]
        db.commit()
        db.refresh(conv)
    return {"share_id": conv.share_id}


@router.delete("/{conv_id}/share")
def unshare_conversation(
    conv_id: int,
    current_user: User = Depends(get_guest_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    conv.share_id = None
    db.commit()
    return {"detail": "已取消分享"}


# ─────────── 公开查看（无需登录） ──────

share_router = APIRouter(prefix="/api/share", tags=["share"])


@share_router.get("/{share_id}")
def get_shared_conversation(
    share_id: str,
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(Conversation.share_id == share_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="分享链接无效或已过期")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
        .all()
    )
    return {
        "title": conv.title,
        "model_name": conv.model_name,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else None,
            }
            for m in msgs
        ],
    }
