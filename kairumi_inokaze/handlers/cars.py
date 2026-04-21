"""Handler for /cars — car dealership."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from kairumi_inokaze import database as db
from kairumi_inokaze.middlewares import check_anti_spam
from kairumi_inokaze.utils.keyboards import cars_keyboard
from kairumi_inokaze.utils.messages import esc
from kairumi_inokaze.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)


async def cars_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cars — car dealership menu."""
    if update.message is None:
        return

    user = update.effective_user
    if await check_anti_spam(user.id):
        return

    if update.effective_chat.type in ("group", "supergroup"):
        db.add_group(update.effective_chat.id)

    await update.message.reply_text(
        "🚗 <b>Car Dealership</b>\n━━━━━━━━━━━━━━━━\nBrowse and buy luxury cars:",
        parse_mode="HTML",
        reply_markup=cars_keyboard(),
    )


async def cars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle car menu selection."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1]
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    if action == "browse":
        cars = db.get_cars_shop()
        if not cars:
            await query.edit_message_text(
                "🚗 <b>Car Dealership</b>\n━━━━━━━━━━━━━━━━\n🚘 No cars available yet!\nAsk an admin to add cars.",
                parse_mode="HTML",
                reply_markup=cars_keyboard(),
            )
            return

        lines = ["🚗 <b>Available Cars</b>\n━━━━━━━━━━━━━━━━\n"]
        for i, car in enumerate(cars):
            lines.append(
                f"🚗 <b>{esc(car.get('name', 'Car'))}</b>\n"
                f"   💰 Price: {car.get('price', 0):,} coins\n"
                f"   ⚡ Speed: {car.get('speed', '?')}/10\n"
                f"   ✨ Prestige: {car.get('prestige', '?')}/10\n"
                f"   To buy: tap Buy Car {i + 1}\n"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "mine":
        db_user = db.get_or_create_user(user_id, username)
        my_cars = db_user.get("cars", [])
        if not my_cars:
            await query.edit_message_text("🚗 You don't own any cars yet! Browse the dealership.")
            return
        lines = ["🚗 <b>Your Cars</b>\n━━━━━━━━━━━━━━━━\n"]
        for car in my_cars:
            lines.append(f"🚗 <b>{esc(car.get('name', 'Car'))}</b>\n   Prestige: {car.get('prestige', '?')}/10")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")

    elif action == "sell":
        db_user = db.get_or_create_user(user_id, username)
        my_cars = db_user.get("cars", [])
        if not my_cars:
            await query.edit_message_text("🚗 You have no cars to sell.")
            return
        context.user_data["sell_car_step"] = "select"
        context.user_data["sell_car_list"] = my_cars
        lines = ["🚗 <b>Select car to sell:</b>\n"]
        for i, car in enumerate(my_cars, 1):
            lines.append(f"{i}. {esc(car.get('name', 'Car'))} — sell for {int(car.get('price', 0) * 0.7):,} coins")
        lines.append("\nReply with the number:")
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")


async def sell_car_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle car sell flow."""
    if context.user_data.get("sell_car_step") != "select":
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    my_cars = context.user_data.get("sell_car_list", [])
    text = update.message.text.strip()

    try:
        idx = int(text) - 1
        if idx < 0 or idx >= len(my_cars):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid selection.")
        return

    car = my_cars[idx]
    sell_price = int(car.get("price", 0) * 0.7)

    db_user = db.get_or_create_user(user_id, username)
    user_cars = db_user.get("cars", [])
    if idx < len(user_cars):
        user_cars.pop(idx)
    db_user["cars"] = user_cars
    db_user["balance"] = db_user.get("balance", 0) + sell_price
    db.save_user(db_user)

    context.user_data.pop("sell_car_step", None)
    context.user_data.pop("sell_car_list", None)

    await update.message.reply_text(
        f"✅ <b>{esc(car.get('name', 'Car'))} sold for {sell_price:,} coins!</b>",
        parse_mode="HTML",
    )
    logger.info(f"User {user_id} sold car {car.get('name')} for {sell_price}")
