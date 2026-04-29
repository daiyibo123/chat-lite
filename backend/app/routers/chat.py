"""聊天接口：转发到 sub2api，带上下文与自动压缩。"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional, Tuple

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.deps import get_current_user
from app.models import Conversation, Message, Model as ModelORM, User, UserApiKey, UsageLog
from app.schemas import ChatSendRequest, ChatSendResponse
from app.security import decrypt_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

COMPRESS_THRESHOLD = 180_000  # 触发压缩的 token 估算阈值
KEEP_RECENT = 20              # 压缩时保留最近 N 条完整消息

COMPRESS_PROMPT = (
    "请把以下历史对话压缩成简洁但信息完整的上下文摘要，"
    "保留用户目标、关键结论、重要约束、模型已经做过的事情，"
    "不要加入新信息。\n\n"
)


def _upstream_error_message(service_name: str, status_code: int, response_text: str) -> str:
    text = response_text.strip()
    if "<!DOCTYPE html" in text[:300] or "<html" in text[:300].lower():
        return f"{service_name} 上游服务返回 HTTP {status_code}，可能是接口网关临时不可用或模型接口地址配置错误"
    try:
        data = json.loads(text)
        message = data.get("error", {}).get("message") or data.get("message") or data.get("detail")
        if message:
            return f"{service_name} 调用失败: HTTP {status_code} - {message}"
    except json.JSONDecodeError:
        pass
    clean = re.sub(r"\s+", " ", text)[:200]
    return f"{service_name} 调用失败: HTTP {status_code}" + (f" - {clean}" if clean else "")


# ─────────── token 估算 ──────────────

def _estimate_tokens(text: str) -> int:
    """简单字符估算：中文 ≈ 1 char/token，英文 ≈ 4 char/token，折中用 len。"""
    return len(text)


def _estimate_history_tokens(summary: Optional[str], history: List[Message]) -> int:
    total = 0
    if summary:
        total += _estimate_tokens(summary)
    for m in history:
        total += _estimate_tokens(m.content)
    return total


# ─────────── 上下文构建 ───────────────

_IMG_TAG_RE = re.compile(r'!\[img\]\([^)]+\)\n?')


def _clean_content(text: str) -> str:
    """去掉 ![img](url) 标记，避免历史消息中无意义 URL 浪费 token。"""
    return _IMG_TAG_RE.sub('', text).strip()


def _build_openai_messages(summary: Optional[str], history: List[Message], images: Optional[List[str]] = None) -> list:
    msgs = []
    if summary:
        msgs.append({"role": "system", "content": f"以下是之前对话的摘要：\n{summary}"})
    for i, m in enumerate(history):
        if m.role in ("user", "assistant"):
            is_last_user = images and m.role == "user" and i == len(history) - 1
            clean = _clean_content(m.content)
            if is_last_user:
                content_parts = [{"type": "text", "text": clean or "请看图片"}]
                for img in images:
                    content_parts.append({"type": "image_url", "image_url": {"url": img}})
                msgs.append({"role": "user", "content": content_parts})
            else:
                if clean:
                    msgs.append({"role": m.role, "content": clean})
    return msgs


def _build_gemini_contents(summary: Optional[str], history: List[Message], images: Optional[List[str]] = None) -> list:
    contents = []
    if summary:
        contents.append({"role": "user", "parts": [{"text": f"[对话摘要]\n{summary}"}]})
        contents.append({"role": "model", "parts": [{"text": "好的，我已了解之前的对话内容，请继续。"}]})
    for i, m in enumerate(history):
        if m.role == "user":
            clean = _clean_content(m.content)
            parts = [{"text": clean or "请看图片"}]
            if images and i == len(history) - 1:
                for img in images:
                    if ";base64," in img:
                        mime = img.split(";")[0].split(":")[1]
                        raw = img.split(";base64,")[1]
                        parts.append({"inline_data": {"mime_type": mime, "data": raw}})
            contents.append({"role": "user", "parts": parts})
        elif m.role == "assistant":
            contents.append({"role": "model", "parts": [{"text": m.content}]})
    return contents


# ─────────── 各 endpoint 调用 ─────────

async def _call_openai_chat(endpoint_url: str, model_name: str, api_key: str, messages: list) -> dict:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            endpoint_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model_name, "messages": messages, "stream": False},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=_upstream_error_message("OpenAI", r.status_code, r.text))
    data = r.json()
    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {"reply": reply, "input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)}


async def _call_anthropic(endpoint_url: str, model_name: str, api_key: str, messages: list) -> dict:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            endpoint_url,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": model_name, "max_tokens": 4096, "messages": messages},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=_upstream_error_message("Anthropic", r.status_code, r.text))
    data = r.json()
    reply = data["content"][0]["text"]
    usage = data.get("usage", {})
    return {"reply": reply, "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)}


async def _call_openai_image(endpoint_url: str, model_name: str, api_key: str, prompt: str) -> dict:
    image_endpoint = endpoint_url          # 统一使用 /v1/images/generations
    payload = {"model": model_name, "prompt": prompt, "n": 1, "size": "1024x1024"}
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(
            image_endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=_upstream_error_message("图片生成", r.status_code, r.text))
    data = r.json()
    image_url = None
    if data.get("data"):
        item = data["data"][0]
        image_url = item.get("url")
        if not image_url and item.get("b64_json"):
            image_url = f"data:image/png;base64,{item['b64_json']}"
    if not image_url:
        for item in data.get("output", []):
            if item.get("type") == "image_generation_call" and item.get("result"):
                image_url = f"data:image/png;base64,{item['result']}"
                break
            for content in item.get("content", []):
                if content.get("type") in ("output_image", "image"):
                    image_url = content.get("image_url") or content.get("url")
                    if not image_url and content.get("b64_json"):
                        image_url = f"data:image/png;base64,{content['b64_json']}"
                    if image_url:
                        break
            if image_url:
                break
    if not image_url:
        raise HTTPException(status_code=502, detail="图片生成成功返回，但未找到图片数据")
    reply = f"![img]({image_url})"
    return {"reply": reply, "input_tokens": 0, "output_tokens": 0, "image_url": image_url}


async def _call_gemini(endpoint_url: str, model_name: str, api_key: str, contents: list) -> dict:
    url = f"{endpoint_url}/v1beta/models/{model_name}:generateContent"
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            url,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={"contents": contents},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=_upstream_error_message("Gemini", r.status_code, r.text))
    data = r.json()
    reply = data["candidates"][0]["content"]["parts"][0]["text"]
    usage_meta = data.get("usageMetadata", {})
    return {"reply": reply, "input_tokens": usage_meta.get("promptTokenCount", 0), "output_tokens": usage_meta.get("candidatesTokenCount", 0)}


# ─────────── 上下文压缩 ──────────────

async def _compress_old_messages(
    old_messages: List[Message],
    existing_summary: Optional[str],
    endpoint_type: str,
    endpoint_url: str,
    model_name: str,
    api_key: str,
) -> Optional[str]:
    """将旧消息压缩为摘要，失败时返回 None（退化为截断）。"""
    text_parts = []
    if existing_summary:
        text_parts.append(f"[之前的摘要]\n{existing_summary}\n")
    for m in old_messages:
        tag = "用户" if m.role == "user" else "助手"
        text_parts.append(f"{tag}: {m.content}")
    conversation_text = "\n".join(text_parts)

    compress_request = COMPRESS_PROMPT + conversation_text

    try:
        if endpoint_type == "openai_chat":
            result = await _call_openai_chat(
                endpoint_url, model_name, api_key,
                [{"role": "user", "content": compress_request}],
            )
        elif endpoint_type == "anthropic":
            result = await _call_anthropic(
                endpoint_url, model_name, api_key,
                [{"role": "user", "content": compress_request}],
            )
        elif endpoint_type == "gemini":
            result = await _call_gemini(
                endpoint_url, model_name, api_key,
                [{"role": "user", "parts": [{"text": compress_request}]}],
            )
        else:
            return None
        return result["reply"]
    except Exception as e:
        logger.warning("上下文压缩失败，退化为截断: %s", e)
        return None


async def _maybe_compress(
    conv: Conversation,
    history: List[Message],
    endpoint_type: str,
    endpoint_url: str,
    model_name: str,
    api_key: str,
    db: Session,
) -> Tuple[Optional[str], List[Message]]:
    """检查上下文是否超限，需要时压缩，返回 (summary, recent_messages)。"""
    total = _estimate_history_tokens(conv.summary, history)

    if total <= COMPRESS_THRESHOLD:
        return conv.summary, history

    # 需要压缩：保留最近 KEEP_RECENT 条，压缩更早的
    if len(history) <= KEEP_RECENT:
        # 消息数不多但单条很长，无法再压缩，直接使用
        return conv.summary, history

    old_messages = history[:-KEEP_RECENT]
    recent_messages = history[-KEEP_RECENT:]

    logger.info(
        "触发上下文压缩: conv=%d, total_est=%d, old=%d条, keep=%d条",
        conv.id, total, len(old_messages), len(recent_messages),
    )

    new_summary = await _compress_old_messages(
        old_messages, conv.summary,
        endpoint_type, endpoint_url, model_name, api_key,
    )

    if new_summary:
        conv.summary = new_summary
        conv.summary_updated_at = datetime.utcnow()
        # 删除已压缩的旧消息
        old_ids = [m.id for m in old_messages]
        db.query(Message).filter(Message.id.in_(old_ids)).delete(synchronize_session=False)
        db.flush()
        return new_summary, recent_messages
    else:
        # 压缩失败，退化：只保留最近 KEEP_RECENT 条
        return conv.summary, recent_messages


# ─────────── 主接口 ───────────────────

@router.post("/send", response_model=ChatSendResponse)
async def chat_send(
    body: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. 校验对话归属
    conv = db.query(Conversation).filter(
        Conversation.id == body.conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    # 2. 查询模型配置
    model_cfg = db.query(ModelORM).filter(ModelORM.model_name == body.model_name).first()
    if not model_cfg:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not model_cfg.enabled:
        raise HTTPException(status_code=400, detail="模型已禁用")

    # 3. 查询用户 Key
    now = datetime.utcnow()
    key_row = db.query(UserApiKey).filter(
        UserApiKey.user_id == current_user.id,
        UserApiKey.key_type == model_cfg.required_key_type,
        UserApiKey.expires_at > now,
    ).first()
    if not key_row:
        raise HTTPException(status_code=400, detail=f"缺少有效的 {model_cfg.required_key_type}")

    api_key = decrypt_api_key(key_row.api_key_encrypted)

    # 4. 保存用户消息
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    db.flush()

    # 5. 读取对话历史
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
        .all()
    )

    # 6. 上下文压缩检查
    endpoint_url = model_cfg.endpoint_url or ""
    summary, context_history = await _maybe_compress(
        conv, history,
        model_cfg.endpoint_type, endpoint_url, model_cfg.model_name, api_key,
        db,
    )

    # 7. 根据 endpoint_type 调用
    images = body.images or None
    if model_cfg.endpoint_type == "openai_chat":
        messages = _build_openai_messages(summary, context_history, images)
        result = await _call_openai_chat(endpoint_url, model_cfg.model_name, api_key, messages)
    elif model_cfg.endpoint_type == "anthropic":
        messages = _build_openai_messages(summary, context_history, images)
        result = await _call_anthropic(endpoint_url, model_cfg.model_name, api_key, messages)
    elif model_cfg.endpoint_type == "gemini":
        contents = _build_gemini_contents(summary, context_history, images)
        result = await _call_gemini(endpoint_url, model_cfg.model_name, api_key, contents)
    elif model_cfg.endpoint_type == "openai_image":
        result = await _call_openai_image(endpoint_url, model_cfg.model_name, api_key, body.message)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 endpoint_type: {model_cfg.endpoint_type}")

    # 8. 保存 assistant 消息
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["reply"],
        model_name=model_cfg.model_name,
    )
    db.add(assistant_msg)

    # 9. 更新对话信息
    conv.updated_at = now
    conv.model_name = model_cfg.model_name
    # 第一条消息时以用户输入前20字为标题
    if len(context_history) <= 1:
        conv.title = body.message[:20] + ("…" if len(body.message) > 20 else "")

    # 10. 写入 usage_logs
    db.add(UsageLog(
        user_id=current_user.id,
        model_name=model_cfg.model_name,
        endpoint_type=model_cfg.endpoint_type,
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
        total_tokens=result.get("input_tokens", 0) + result.get("output_tokens", 0),
    ))

    db.commit()
    db.refresh(assistant_msg)

    return ChatSendResponse(
        reply=result["reply"],
        message_id=assistant_msg.id,
        conversation_id=conv.id,
        model_name=model_cfg.model_name,
    )


# ─────────── 流式接口 (SSE) ──────────

async def _stream_openai(endpoint_url: str, model_name: str, api_key: str, messages: list):
    """OpenAI / 兼容 API 流式输出，yield 文本片段。
    连接中断时 yield 特殊标记让调用方知道是部分完成而非完全失败。
    """
    timeout = httpx.Timeout(30, read=180)
    async with httpx.AsyncClient(timeout=timeout) as c:
        async with c.stream(
            "POST", endpoint_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model_name, "messages": messages, "stream": True},
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise Exception(f"HTTP {resp.status_code}: {body[:300]}")
            try:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
            except (httpx.RemoteProtocolError, httpx.ReadError) as e:
                # 连接中断但可能已经收到了部分内容，不抛异常
                logger.warning("流式读取中断（已有部分内容）: %s", e)


@router.post("/stream")
async def chat_stream(
    body: ChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流式聊天：通过 SSE 逐 token 返回 AI 回复。"""

    # 1-6 与 chat_send 相同
    conv = db.query(Conversation).filter(
        Conversation.id == body.conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    model_cfg = db.query(ModelORM).filter(ModelORM.model_name == body.model_name).first()
    if not model_cfg:
        raise HTTPException(status_code=404, detail="模型不存在")
    if not model_cfg.enabled:
        raise HTTPException(status_code=400, detail="模型已禁用")

    now = datetime.utcnow()
    key_row = db.query(UserApiKey).filter(
        UserApiKey.user_id == current_user.id,
        UserApiKey.key_type == model_cfg.required_key_type,
        UserApiKey.expires_at > now,
    ).first()
    if not key_row:
        raise HTTPException(status_code=400, detail=f"缺少有效的 {model_cfg.required_key_type}")

    api_key = decrypt_api_key(key_row.api_key_encrypted)

    user_msg = Message(conversation_id=conv.id, role="user", content=body.message)
    db.add(user_msg)
    db.flush()

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
        .all()
    )

    endpoint_url = model_cfg.endpoint_url or ""
    ep_type = model_cfg.endpoint_type

    # 生图模型不需要压缩/构建上下文
    if ep_type == "openai_image":
        summary, context_history = conv.summary, history
        openai_msgs = []
    else:
        summary, context_history = await _maybe_compress(
            conv, history,
            ep_type, endpoint_url, model_cfg.model_name, api_key,
            db,
        )
        images = body.images or None
        openai_msgs = _build_openai_messages(summary, context_history, images)

    # 保存需要在流结束后用到的信息
    conv_id = conv.id
    user_id = current_user.id
    m_name = model_cfg.model_name
    is_first = len(context_history) <= 1
    user_text = body.message

    # 先 commit 用户消息
    db.commit()

    async def event_generator():
        # ─── 生图模型：调用图片 API ───
        if ep_type == "openai_image":
            try:
                result = await _call_openai_image(endpoint_url, m_name, api_key, user_text)
                reply_text = result["reply"]
                image_url = result.get("image_url", "")
                # 发送图片生成事件
                yield f"data: {json.dumps({'image_url': image_url}, ensure_ascii=False)}\n\n"
            except Exception as e:
                detail = e.detail if isinstance(e, HTTPException) else str(e)
                stream_error = str(detail)[:300]
                yield f"data: {json.dumps({'error': stream_error}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

            # 保存到数据库
            save_db = SessionLocal()
            try:
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=reply_text,
                    model_name=m_name,
                )
                save_db.add(assistant_msg)
                c = save_db.query(Conversation).get(conv_id)
                if c:
                    c.updated_at = datetime.utcnow()
                    c.model_name = m_name
                    if is_first:
                        c.title = user_text[:20] + ("…" if len(user_text) > 20 else "")
                save_db.add(UsageLog(
                    user_id=user_id,
                    model_name=m_name,
                    endpoint_type=ep_type,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                ))
                save_db.commit()
                save_db.refresh(assistant_msg)
                yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("保存生图回复失败: %s", e)
                save_db.rollback()
            finally:
                save_db.close()
            yield "data: [DONE]\n\n"
            return

        # ─── 聊天模型：流式输出 ───
        full_reply = []
        stream_error = None
        try:
            async for chunk in _stream_openai(endpoint_url, m_name, api_key, openai_msgs):
                full_reply.append(chunk)
                yield f"data: {json.dumps({'t': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            stream_error = str(e)[:200]
            logger.error("流式调用失败: %s", e)

        reply_text = "".join(full_reply)

        # 完全没收到内容才报错
        if not reply_text and stream_error:
            yield f"data: {json.dumps({'error': stream_error}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 有内容（完整或部分）→ 保存到数据库
        save_db = SessionLocal()
        try:
            assistant_msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=reply_text,
                model_name=m_name,
            )
            save_db.add(assistant_msg)
            c = save_db.query(Conversation).get(conv_id)
            if c:
                c.updated_at = datetime.utcnow()
                c.model_name = m_name
                if is_first:
                    c.title = user_text[:20] + ("…" if len(user_text) > 20 else "")
            save_db.add(UsageLog(
                user_id=user_id,
                model_name=m_name,
                endpoint_type=ep_type,
                input_tokens=0,
                output_tokens=len(reply_text),
                total_tokens=len(reply_text),
            ))
            save_db.commit()
            save_db.refresh(assistant_msg)
            yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error("保存流式回复失败: %s", e)
            save_db.rollback()
        finally:
            save_db.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
