"""Telegram bot service for sending notifications"""
import httpx
from typing import Optional, List
from app.infrastructure.config.settings import settings
from app.infrastructure.database.base import SessionLocal
from app.infrastructure.telegram.models import UserTelegramModel
from app.infrastructure.database.models import UserModel
from app.domain.entities.user import UserRole


class TelegramBotService:
    """Service for sending Telegram notifications"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.enabled = settings.TELEGRAM_BOT_ENABLED and self.bot_token is not None
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
    
    async def send_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram chat"""
        if not self.enabled or not self.api_url:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": parse_mode
                    }
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"⚠️ Error sending Telegram message: {e}")
            return False
    
    def get_telegram_chat_id(self, user_id: str) -> Optional[str]:
        """Get Telegram chat ID for user"""
        if not self.enabled:
            return None
        
        db = SessionLocal()
        try:
            user_telegram = db.query(UserTelegramModel).filter(
                UserTelegramModel.user_id == user_id,
                UserTelegramModel.is_active == True
            ).first()
            
            if user_telegram:
                return user_telegram.telegram_chat_id
            return None
        except Exception as e:
            print(f"⚠️ Error getting Telegram chat ID: {e}")
            return None
        finally:
            db.close()
    
    def is_admin(self, user_id: str) -> bool:
        """Check if user is admin or IT"""
        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                return user.role in [UserRole.ADMIN, UserRole.IT]
            return False
        except Exception as e:
            print(f"⚠️ Error checking user role: {e}")
            return False
        finally:
            db.close()
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """Get user info by ID"""
        db = SessionLocal()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
                }
            return None
        except Exception as e:
            print(f"⚠️ Error getting user info: {e}")
            return None
        finally:
            db.close()
    
    async def notify_task_assigned(self, user_id: str, todo_title: str, creator_name: str) -> bool:
        """Notify user that a task was assigned to them"""
        chat_id = self.get_telegram_chat_id(user_id)
        if not chat_id:
            return False
        
        message = (
            f"📋 <b>Новая задача назначена</b>\n\n"
            f"<b>Задача:</b> {todo_title}\n"
            f"<b>От:</b> {creator_name}\n\n"
            f"Проверьте вашу доску задач!"
        )
        
        return await self.send_message(chat_id, message)
    
    async def notify_task_completed(self, user_id: str, todo_title: str, assignee_name: str) -> bool:
        """Notify admin/IT that their task was completed"""
        if not self.is_admin(user_id):
            return False
        
        chat_id = self.get_telegram_chat_id(user_id)
        if not chat_id:
            return False
        
        message = (
            f"✅ <b>Задача выполнена</b>\n\n"
            f"<b>Задача:</b> {todo_title}\n"
            f"<b>Выполнил:</b> {assignee_name}\n\n"
            f"Задача перемещена в статус 'Выполнено'"
        )
        
        return await self.send_message(chat_id, message)
    
    async def notify_task_moved(self, user_id: str, todo_title: str, old_status: str, new_status: str, assignee_name: str) -> bool:
        """Notify admin/IT that their task was moved to a different status"""
        if not self.is_admin(user_id):
            return False
        
        chat_id = self.get_telegram_chat_id(user_id)
        if not chat_id:
            return False
        
        status_names = {
            "todo": "К выполнению",
            "in_progress": "В работе",
            "done": "Выполнено",
            "archived": "Архив"
        }
        
        old_status_name = status_names.get(old_status, old_status)
        new_status_name = status_names.get(new_status, new_status)
        
        message = (
            f"🔄 <b>Задача перемещена</b>\n\n"
            f"<b>Задача:</b> {todo_title}\n"
            f"<b>От:</b> {old_status_name}\n"
            f"<b>К:</b> {new_status_name}\n"
            f"<b>Переместил:</b> {assignee_name}"
        )
        
        return await self.send_message(chat_id, message)
    
    async def notify_checkbox_updated(self, user_id: str, todo_title: str, item_text: str, checked: bool, updater_name: str) -> bool:
        """Notify creator that a checkbox was updated by another user"""
        chat_id = self.get_telegram_chat_id(user_id)
        if not chat_id:
            return False
        
        checkbox_status = "отмечен" if checked else "снят"
        checkbox_icon = "✅" if checked else "☐"
        
        message = (
            f"{checkbox_icon} <b>Чекбокс обновлен</b>\n\n"
            f"<b>Задача:</b> {todo_title}\n"
            f"<b>Пункт:</b> {item_text}\n"
            f"<b>Статус:</b> {checkbox_status}\n"
            f"<b>Обновил:</b> {updater_name}"
        )
        
        return await self.send_message(chat_id, message)
    
    def get_it_users(self) -> List[str]:
        """Get all IT users IDs"""
        db = SessionLocal()
        try:
            users = db.query(UserModel).filter(UserModel.role == UserRole.IT).all()
            return [user.id for user in users]
        except Exception as e:
            print(f"⚠️ Error getting IT users: {e}")
            return []
        finally:
            db.close()
    
    async def notify_new_ticket(self, user_id: str, ticket_title: str, ticket_priority: str, creator_name: str, ticket_id: str = None) -> bool:
        """Notify IT user about new ticket"""
        chat_id = self.get_telegram_chat_id(user_id)
        if not chat_id:
            return False
        
        priority_names = {
            "low": "Низкий",
            "medium": "Средний",
            "high": "Высокий",
            "urgent": "Срочный"
        }
        
        priority_icons = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "urgent": "🔴"
        }
        
        priority_name = priority_names.get(ticket_priority.lower(), ticket_priority)
        priority_icon = priority_icons.get(ticket_priority.lower(), "📋")
        
        message = (
            f"🎫 <b>Новый тикет создан</b>\n\n"
            f"<b>Тикет:</b> {ticket_title}\n"
            f"<b>Приоритет:</b> {priority_icon} {priority_name}\n"
            f"<b>Создал:</b> {creator_name}\n\n"
            f"Проверьте систему тикетов!"
        )
        
        return await self.send_message(chat_id, message)
    
    async def notify_all_it_users(self, ticket_title: str, ticket_priority: str, creator_name: str, ticket_id: str = None) -> None:
        """Notify all IT users about new ticket"""
        it_user_ids = self.get_it_users()
        for user_id in it_user_ids:
            try:
                await self.notify_new_ticket(user_id, ticket_title, ticket_priority, creator_name, ticket_id)
            except Exception as e:
                print(f"⚠️ Error notifying IT user {user_id}: {e}")
    
    async def notify_multiple_users(self, user_ids: List[str], message_func, *args, **kwargs) -> None:
        """Notify multiple users"""
        for user_id in user_ids:
            try:
                await message_func(user_id, *args, **kwargs)
            except Exception as e:
                print(f"⚠️ Error notifying user {user_id}: {e}")


# Global instance
telegram_bot = TelegramBotService()
