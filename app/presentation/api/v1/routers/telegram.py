"""Telegram bot registration API router"""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.presentation.api.v1.dependencies import get_current_active_user
from app.infrastructure.database.base import SessionLocal
from app.infrastructure.telegram.models import UserTelegramModel, TelegramLinkTokenModel
from app.infrastructure.telegram.bot import telegram_bot
from app.infrastructure.config.settings import settings
import secrets
import httpx

router = APIRouter(prefix="/telegram", tags=["telegram"], redirect_slashes=False)


class TelegramRegisterResponseDTO(BaseModel):
    """Telegram registration response"""
    success: bool
    message: str
    bot_link: Optional[str] = None


class TelegramLinkResponseDTO(BaseModel):
    """Telegram link response
    
    Для удобства фронта возвращаем ссылку в двух полях:
    - bot_link
    - link (дублирует bot_link)
    """
    success: bool
    bot_link: str
    link: Optional[str] = None
    message: str


class TelegramRegisterDTO(BaseModel):
    """Telegram registration request (legacy)"""
    telegram_chat_id: str
    username: Optional[str] = None


class CompleteLinkDTO(BaseModel):
    """Complete link request"""
    token: str
    chat_id: str
    username: Optional[str] = None


@router.post("/link", response_model=TelegramLinkResponseDTO)
async def get_telegram_link(
    current_user: dict = Depends(get_current_active_user),
):
    """Get Telegram bot link for user registration
    
    Returns a deep link that user can open in Telegram.
    When user clicks Start, bot will automatically register them.
    If Telegram bot is not configured on server, returns success=False and message (no 503).
    """
    if not telegram_bot.enabled:
        return TelegramLinkResponseDTO(
            success=False,
            bot_link="",
            link=None,
            message="Telegram-бот не настроен на сервере. Обратитесь к администратору (TELEGRAM_BOT_TOKEN)."
        )
    
    # Get bot username (we'll need to fetch it from Telegram API)
    bot_username = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{telegram_bot.api_url}/getMe")
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_username = data.get("result", {}).get("username")
    except Exception:
        pass
    
    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not get bot username. Please check TELEGRAM_BOT_TOKEN."
        )
    
    db = SessionLocal()
    try:
        user_id = current_user["id"]
        
        # Check if user already has an active registration
        existing = db.query(UserTelegramModel).filter(
            UserTelegramModel.user_id == user_id,
            UserTelegramModel.is_active == True
        ).first()
        
        if existing:
            # User already registered, return existing link
            bot_link = f"https://t.me/{bot_username}?start=already_registered"
            return TelegramLinkResponseDTO(
                success=True,
                bot_link=bot_link,
                link=bot_link,
                message="Вы уже зарегистрированы. Перейдите по ссылке для повторной регистрации."
            )
        
        # Generate unique token
        token = secrets.token_urlsafe(32)
        
        # Check if token already exists (very unlikely, but just in case)
        while db.query(TelegramLinkTokenModel).filter(TelegramLinkTokenModel.token == token).first():
            token = secrets.token_urlsafe(32)
        
        # Create token record (expires in 1 hour)
        link_token = TelegramLinkTokenModel(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            used=False
        )
        db.add(link_token)
        db.commit()
        
        # Generate deep link
        bot_link = f"https://t.me/{bot_username}?start={token}"
        
        return TelegramLinkResponseDTO(
            success=True,
            bot_link=bot_link,
            link=bot_link,
            message="Перейдите по ссылке и нажмите Start для активации уведомлений"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating Telegram link: {str(e)}"
        )
    finally:
        db.close()


@router.post("/complete-link", response_model=TelegramRegisterResponseDTO)
async def complete_telegram_link(
    data: CompleteLinkDTO,
):
    """Complete Telegram registration using token (called by bot)
    
    This endpoint is called by the Telegram bot when user clicks Start.
    """
    if not telegram_bot.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not enabled."
        )
    
    db = SessionLocal()
    try:
        # Find token
        link_token = db.query(TelegramLinkTokenModel).filter(
            TelegramLinkTokenModel.token == data.token,
            TelegramLinkTokenModel.used == False
        ).first()
        
        if not link_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired token"
            )
        
        # Check expiration
        if link_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expired"
            )
        
        user_id = link_token.user_id
        
        # Check if user already has a Telegram registration
        existing = db.query(UserTelegramModel).filter(
            UserTelegramModel.user_id == user_id
        ).first()
        
        if existing:
            # Update existing registration
            existing.telegram_chat_id = data.chat_id
            existing.username = data.username
            existing.is_active = True
        else:
            # Create new registration
            user_telegram = UserTelegramModel(
                user_id=user_id,
                telegram_chat_id=data.chat_id,
                username=data.username,
                is_active=True
            )
            db.add(user_telegram)
        
        # Mark token as used
        link_token.used = True
        db.commit()
        
        return TelegramRegisterResponseDTO(
            success=True,
            message="Telegram уведомления активированы"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing Telegram registration: {str(e)}"
        )
    finally:
        db.close()


@router.post("/register", response_model=TelegramRegisterResponseDTO)
async def register_telegram(
    data: TelegramRegisterDTO,
    current_user: dict = Depends(get_current_active_user),
):
    """Register user's Telegram chat ID for notifications
    
    Users need to:
    1. Start a conversation with the bot in Telegram
    2. Send /start command to get their chat_id
    3. Call this endpoint with their chat_id to link their account
    """
    if not telegram_bot.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot is not enabled. Please configure TELEGRAM_BOT_TOKEN in settings."
        )
    
    # Verify chat_id is valid by sending a test message
    try:
        test_message = f"✅ Регистрация успешна! Вы будете получать уведомления о задачах.\n\nВаш username: {current_user.get('username', 'Неизвестный')}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{telegram_bot.api_url}/sendMessage",
                json={
                    "chat_id": data.telegram_chat_id,
                    "text": test_message,
                    "parse_mode": "HTML"
                }
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chat_id or bot cannot send messages to this chat. Error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Telegram chat: {str(e)}"
        )
    
    # Register or update user's Telegram chat ID
    db = SessionLocal()
    try:
        user_id = current_user["id"]
        
        # Check if user already has a Telegram registration
        existing = db.query(UserTelegramModel).filter(
            UserTelegramModel.user_id == user_id
        ).first()
        
        if existing:
            # Update existing registration
            existing.telegram_chat_id = data.telegram_chat_id
            existing.username = data.username
            existing.is_active = True
            db.commit()
            return TelegramRegisterResponseDTO(
                success=True,
                message="Telegram уведомления обновлены"
            )
        else:
            # Create new registration
            user_telegram = UserTelegramModel(
                user_id=user_id,
                telegram_chat_id=data.telegram_chat_id,
                username=data.username,
                is_active=True
            )
            db.add(user_telegram)
            db.commit()
            return TelegramRegisterResponseDTO(
                success=True,
                message="Telegram уведомления активированы"
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering Telegram: {str(e)}"
        )
    finally:
        db.close()


@router.delete("/unregister", response_model=TelegramRegisterResponseDTO)
async def unregister_telegram(
    current_user: dict = Depends(get_current_active_user),
):
    """Unregister user's Telegram notifications"""
    db = SessionLocal()
    try:
        user_id = current_user["id"]
        
        user_telegram = db.query(UserTelegramModel).filter(
            UserTelegramModel.user_id == user_id
        ).first()
        
        if not user_telegram:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telegram registration not found"
            )
        
        user_telegram.is_active = False
        db.commit()
        
        return TelegramRegisterResponseDTO(
            success=True,
            message="Telegram уведомления отключены"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unregistering Telegram: {str(e)}"
        )
    finally:
        db.close()


@router.get("/status", response_model=dict)
async def get_telegram_status(
    current_user: dict = Depends(get_current_active_user),
):
    """Get user's Telegram registration status"""
    db = SessionLocal()
    try:
        user_id = current_user["id"]
        
        user_telegram = db.query(UserTelegramModel).filter(
            UserTelegramModel.user_id == user_id,
            UserTelegramModel.is_active == True
        ).first()
        
        if user_telegram:
            return {
                "registered": True,
                "chat_id": user_telegram.telegram_chat_id,
                "username": user_telegram.username
            }
        else:
            return {
                "registered": False
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting Telegram status: {str(e)}"
        )
    finally:
        db.close()


@router.get("/link", response_model=TelegramLinkResponseDTO)
async def get_telegram_link_get(
    current_user: dict = Depends(get_current_active_user),
):
    """Get Telegram bot link (GET method)"""
    # Обертка над POST-версией, чтобы фронту было удобно вызывать GET
    return await get_telegram_link(current_user)
