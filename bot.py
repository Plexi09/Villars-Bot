import feedparser
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv
import time

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer les valeurs des variables d'environnement
TOKEN = os.getenv('TELEGRAM_TOKEN')
RSS_URL = os.getenv('RSS_URL')
CHECK_INTERVAL = 60 * 10  # Intervalle de vérification du flux RSS en secondes (ici, toutes les 10 minutes)

# Eécupérer et analyser le flux RSS
def get_latest_rss_entry():
    feed = feedparser.parse(RSS_URL)
    return feed.entries[0] if feed.entries else None

# Commande /start
def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Le bot est opérationel !")

# Diffuser les nouveaux articles RSS
def broadcast_rss(context):
    job = context.job
    new_entry = get_latest_rss_entry()

    if new_entry and new_entry.link != job.context['last_link']:
        job.context['last_link'] = new_entry.link
        message = f"Nouvel article : {new_entry.title}\n{new_entry.link}"
        context.bot.send_message(chat_id=job.context['chat_id'], text=message)

# Ajouter le bot au groupe et démarrer la diffusion
def join_group(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Bot ajouté au groupe. Je vais commencer à surveiller le flux RSS.")
    job_queue = context.job_queue
    context.job_queue.run_repeating(broadcast_rss, interval=CHECK_INTERVAL, first=0, context={'chat_id': update.effective_chat.id, 'last_link': None})

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Gestionnaire pour la commande /start
    dispatcher.add_handler(CommandHandler('start', start))

    # Gestionnaire pour les nouveaux membres dans un groupe
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, join_group))

    # Démarre le bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
