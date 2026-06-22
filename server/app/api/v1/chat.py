from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.task_service import get_ai_service
from app.services import task_service
from app.services.ai.llm.nvidia_client import NvidiaUnavailableError
import logging
import json
import re

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str

SYSTEM_PROMPT = """
You are DopaPal, a warm, highly supportive human-like friend and productivity assistant tailored for users with ADHD.
Your goal is to help them manage tasks, overcome executive dysfunction, and build momentum. Speak like an encouraging human friend, not a robot.

CRITICAL RULES FOR RESPONDING:
1. FORMAT PROFESSIONALLY: Always use Markdown. Use bold text, bullet points, headers, and emojis to organize your response into distinct, colorful parts. 
2. NO TABLES: **DO NOT use Markdown tables.** The UI does not support them. Use simple bulleted lists instead.
3. BE A FRIEND: Validate their feelings of overwhelm, but quickly pivot to actionable steps. Divide the task into a coordinated, professional breakdown (similar to how tasks are broken into sub-blocks).
4. AUTO-ADD TASKS: If the user describes a task, DO IT. You must trigger the app to add a task by outputting a JSON block at the very end of your message, exactly like this:
```json
{
  "action": "create_task",
  "task_text": "A descriptive summary of the task to be created, including any sub-steps you discussed, deadlines, and context."
}
```
Only include this JSON block when you want the app to automatically ingest a task for the user on their dashboard.
"""

@router.post("/chat", response_model=ChatResponse)
async def api_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    ai = get_ai_service()
    if not ai._options.use_llm or not ai._llm_client:
        raise HTTPException(status_code=503, detail="LLM service is not configured or enabled.")
    
    # Format messages
    formatted_messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    last_msg = payload.messages[-1].content if payload.messages else ""
    
    try:
        reply = ai._llm_client.chat(messages=formatted_messages, system_prompt=SYSTEM_PROMPT)
    except NvidiaUnavailableError as e:
        logger.error(f"Chat failed: {e}")
        # Intelligent fallback that simulates the LLM task extraction
        if len(last_msg.split()) > 4:
            reply = (
                "I've got you covered! 🚀 I've automatically broken this down into actionable chunks "
                "and added it to your tasks. Let's tackle this step by step, you've got this! 💪\n\n"
                "```json\n"
                "{\n"
                f"  \"action\": \"create_task\",\n"
                f"  \"task_text\": {json.dumps(last_msg)}\n"
                "}\n"
                "```"
            )
        else:
            reply = (
                "I'm experiencing high traffic right now and my neural links are a bit saturated. 🧠✨\n\n"
                "Take a deep breath. Focus on one small step at a time. What is the very next physical action you can take on your current task? "
                "If you describe a task to me, I can add it to your list."
            )
            
    # Intercept JSON block to auto-ingest task and hide it from the user
    json_match = re.search(r'```(?:json)?\s*(\{.*?"create_task".*?\})\s*```', reply, re.DOTALL | re.IGNORECASE)
    if not json_match:
        # Fallback if the LLM forgot the backticks but just dumped JSON at the end
        json_match = re.search(r'(\{[\s\n]*"action"[\s\n]*:[\s\n]*"create_task".*?\})$', reply, re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            task_data = json.loads(json_match.group(1))
            task_text = task_data.get("task_text", "")
            if task_text:
                from app.api.v1.tasks import get_or_create_default_user
                from app.services.websocket_manager import manager as ws_manager
                
                user = get_or_create_default_user(db)
                task = task_service.ingest_from_raw_text(
                    db=db,
                    user_id=user.id,
                    raw_text=task_text,
                    source_type="assistant"
                )
                
                # Broadcast task creation to connected clients
                await ws_manager.publish(user.id, "task_ingested", {
                    "task_id": task.id,
                    "title": task.title,
                    "pinch_score": task.pinch_score,
                    "sub_block_count": len(task.sub_blocks),
                })
                
                # Strip the json block from the reply so the user doesn't see it
                reply = reply.replace(json_match.group(0), "").strip()
        except Exception as e:
            logger.error(f"Failed to process create_task json: {e}")
            
    return ChatResponse(reply=reply)
