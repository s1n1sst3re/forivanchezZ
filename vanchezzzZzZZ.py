from telethon import TelegramClient
import asyncio
import time
import keyboard

api_id = '22055307'
api_hash = 'f9be6b0bd1f4e2d74eb9e148bb6f1c24'

session_name = 'my_account'

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()

    print("Ара, все ок, авторизация прошла, дон!")

    target_chat = input("Тигр, введи username или id чата/бота: ").strip()

    try:
        num_messages = int(input("Шамиля'h, введи количество сообщений в цикле: ").strip())
    except ValueError:
        print("Ара, ошибка: количество сообщений должно быть числом. буду использовать 2 сообщения, дон.")
        num_messages = 2

    messages = []
    for i in range(num_messages):
        message = input(f"Тигр, введи сообщение {i + 1}: ").strip()
        messages.append(message)

    try:
        num_repeats = int(input("Шамиля'h, введи количество повторений цикла: ").strip())
    except ValueError:
        print("Ара, ошибка: количество повторений должно быть числом. буду использовать 1 повторение, дон.")
        num_repeats = 1

    try:
        interval = int(input("Тигр, введи интервал между сообщениями (в секундах): ").strip())
    except ValueError:
        print("Ара, ошибка: интервал должен быть числом. буду использовать 3 секунды, дон.")
        interval = 3

    total_messages_sent = 0
    stop_sending = False

    async def send_messages():
        nonlocal total_messages_sent, stop_sending
        for _ in range(num_repeats):
            for message in messages:
                if stop_sending:
                    print("Ара, остановка по запросу, дон.")
                    return
                try:
                    await client.send_message(target_chat, message)
                    total_messages_sent += 1
                    print(f"Ара, отправлено сообщение: {message} (всего отправлено: {total_messages_sent}), дон.")
                    await asyncio.sleep(interval)
                except Exception as e:
                    print(f"Ара, ошибка при отправке сообщения: {e}, дон.")
                    return

    def on_r_press(event):
        nonlocal stop_sending
        if event.name == 'r':
            stop_sending = True
            print("Ара, клавиша R нажата, дон. Останавливаюсь...")

    keyboard.on_press(on_r_press)

    while True:
        await send_messages()

        if total_messages_sent >= 450:
            print("Ара, достигнуто 450 сообщений, дон. Остановка на 4 часа.")
            time.sleep(4 * 60 * 60)
            total_messages_sent = 0

        user_input = input("Тигр, продолжить? (y/n): ").strip().lower()
        if user_input != 'y':
            print("Ара, скрипт завершен, дон.")
            break

    keyboard.unhook_all()
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())