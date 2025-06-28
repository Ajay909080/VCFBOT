import os
import zipfile
import io
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Define conversation states
ASK_TITLE, ASK_COUNT, PROCESS_FILE = range(3)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Please send me the TXT file containing phone numbers.")
    return ASK_TITLE

async def ask_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        file = await update.message.document.get_file()
        txt_data = await file.download_as_bytearray()
        numbers = txt_data.decode("utf-8").splitlines()
        context.user_data["numbers"] = [n.strip().lstrip('+') for n in numbers if n.strip()]
        await update.message.reply_text("✅ TXT file received.\n\n🔤 Now, enter the base title (e.g. A):")
        return ASK_COUNT
    else:
        await update.message.reply_text("❗ Please send a valid TXT file.")
        return ASK_TITLE

async def ask_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.strip().upper()
    await update.message.reply_text("🔢 How many numbers per VCF file? (e.g. 50):")
    return PROCESS_FILE

async def process_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        per_file = int(update.message.text.strip())
    except:
        await update.message.reply_text("❗ Invalid number. Please enter a digit like 50.")
        return PROCESS_FILE

    numbers = context.user_data["numbers"]
    title = context.user_data["title"]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i in range(0, len(numbers), per_file):
            file_index = i // per_file + 1
            filename = f"{title}{str(file_index).zfill(3)}.vcf"
            vcf_content = ""
            for j, number in enumerate(numbers[i:i+per_file]):
                contact_name = f"{title}{str(file_index).zfill(3)}-{str(j+1).zfill(3)}"
                full_number = '+' + number.lstrip('+')
                vcf_content += f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name}\nTEL:{full_number}\nEND:VCARD\n"
            zipf.writestr(filename, vcf_content)

    zip_buffer.seek(0)
    await update.message.reply_document(document=InputFile(zip_buffer, filename=f"{title}_vcards.zip"))
    await update.message.reply_text("✅ Done! Here's your ZIP file.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

if __name__ == "__main__":
    import logging
    from dotenv import load_dotenv

    load_dotenv()  # load .env for BOT_TOKEN
    logging.basicConfig(level=logging.INFO)

    BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set this in .env file

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_TITLE: [MessageHandler(filters.Document.MimeType("text/plain"), ask_title)],
            ASK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_count)],
            PROCESS_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("🤖 Bot is running...")
    app.run_polling()
