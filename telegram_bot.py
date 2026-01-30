"""Telegram bot for automatic user registration"""
import asyncio
import httpx
from app.infrastructure.config.settings import settings

# Backend API URL
BACKEND_URL = settings.BACKEND_URL if hasattr(settings, 'BACKEND_URL') else "http://localhost:8000"


async def run_bot():
    """Run Telegram bot with automatic registration"""
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not configured in settings")
        return
    
    bot_token = settings.TELEGRAM_BOT_TOKEN
    api_url = f"https://api.telegram.org/bot{bot_token}"
    
    print("🤖 Telegram Bot - Автоматическая регистрация")
    print("=" * 60)
    print(f"Bot Token: {bot_token[:10]}...")
    print(f"Backend URL: {BACKEND_URL}")
    print("\n✅ Бот запущен и готов к работе!")
    print("Пользователи могут перейти по ссылке и нажать Start для регистрации.\n")
    
    last_update_id = 0
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    # Get updates from Telegram
                    response = await client.get(
                        f"{api_url}/getUpdates",
                        params={"offset": last_update_id + 1, "timeout": 30}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("ok") and data.get("result"):
                        for update in data["result"]:
                            last_update_id = update["update_id"]
                            
                            if "message" in update:
                                message = update["message"]
                                chat = message.get("chat", {})
                                chat_id = str(chat.get("id"))
                                username = chat.get("username")
                                first_name = chat.get("first_name", "Пользователь")
                                text = message.get("text", "")
                                
                                # Handle /start command with token
                                if text.startswith("/start"):
                                    # Extract token from /start command
                                    parts = text.split(" ", 1)
                                    token = parts[1] if len(parts) > 1 else None
                                    
                                    if token:
                                        # User clicked link with token - complete registration
                                        print(f"\n🔗 Регистрация пользователя:")
                                        print(f"   Chat ID: {chat_id}")
                                        print(f"   Username: @{username}" if username else f"   Name: {first_name}")
                                        print(f"   Token: {token[:20]}...")
                                        
                                        try:
                                            # Call backend to complete registration
                                            backend_response = await client.post(
                                                f"{BACKEND_URL}/api/v1/telegram/complete-link",
                                                json={
                                                    "token": token,
                                                    "chat_id": chat_id,
                                                    "username": username
                                                },
                                                timeout=10.0
                                            )
                                            
                                            if backend_response.status_code == 200:
                                                # Success!
                                                success_message = (
                                                    "✅ <b>Регистрация успешна!</b>\n\n"
                                                    f"Привет, {first_name}!\n\n"
                                                    "Теперь вы будете получать уведомления:\n"
                                                    "📋 О новых назначенных задачах\n"
                                                    "✅ О выполнении ваших задач (для админов)\n"
                                                    "🔄 О перемещении ваших задач (для админов)\n\n"
                                                    "Спасибо за использование!"
                                                )
                                                
                                                await client.post(
                                                    f"{api_url}/sendMessage",
                                                    json={
                                                        "chat_id": chat_id,
                                                        "text": success_message,
                                                        "parse_mode": "HTML"
                                                    }
                                                )
                                                
                                                print(f"   ✅ Регистрация завершена успешно!")
                                            else:
                                                error_data = backend_response.json()
                                                error_msg = error_data.get("detail", "Ошибка регистрации")
                                                
                                                error_message = (
                                                    "❌ <b>Ошибка регистрации</b>\n\n"
                                                    f"{error_msg}\n\n"
                                                    "Пожалуйста, получите новую ссылку из приложения."
                                                )
                                                
                                                await client.post(
                                                    f"{api_url}/sendMessage",
                                                    json={
                                                        "chat_id": chat_id,
                                                        "text": error_message,
                                                        "parse_mode": "HTML"
                                                    }
                                                )
                                                
                                                print(f"   ❌ Ошибка: {error_msg}")
                                        except httpx.TimeoutException:
                                            error_message = (
                                                "⏱️ <b>Таймаут подключения</b>\n\n"
                                                "Не удалось подключиться к серверу.\n"
                                                "Попробуйте позже или обратитесь к администратору."
                                            )
                                            await client.post(
                                                f"{api_url}/sendMessage",
                                                json={
                                                    "chat_id": chat_id,
                                                    "text": error_message,
                                                    "parse_mode": "HTML"
                                                }
                                            )
                                            print(f"   ⚠️ Таймаут подключения к backend")
                                        except Exception as e:
                                            error_message = (
                                                "❌ <b>Ошибка подключения</b>\n\n"
                                                f"Не удалось подключиться к серверу: {str(e)}\n\n"
                                                "Попробуйте позже или обратитесь к администратору."
                                            )
                                            await client.post(
                                                f"{api_url}/sendMessage",
                                                json={
                                                    "chat_id": chat_id,
                                                    "text": error_message,
                                                    "parse_mode": "HTML"
                                                }
                                            )
                                            print(f"   ❌ Ошибка подключения: {e}")
                                    else:
                                        # User sent /start without token
                                        welcome_message = (
                                            "👋 <b>Привет!</b>\n\n"
                                            "Для активации уведомлений о задачах:\n"
                                            "1. Откройте приложение\n"
                                            "2. Перейдите в настройки Telegram\n"
                                            "3. Нажмите 'Подключить Telegram'\n"
                                            "4. Перейдите по полученной ссылке\n\n"
                                            "После этого вы будете получать уведомления автоматически!"
                                        )
                                        
                                        await client.post(
                                            f"{api_url}/sendMessage",
                                            json={
                                                "chat_id": chat_id,
                                                "text": welcome_message,
                                                "parse_mode": "HTML"
                                            }
                                        )
                                        
                                        print(f"\n💬 Пользователь {first_name} отправил /start без токена")
                    
                    await asyncio.sleep(1)
                    
                except httpx.TimeoutException:
                    # Timeout is normal, continue polling
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    await asyncio.sleep(5)
                    
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped")


if __name__ == "__main__":
    asyncio.run(run_bot())
