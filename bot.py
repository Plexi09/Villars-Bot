import os
import logging
from dotenv import load_dotenv
import telebot
import feedparser
import schedule
import time
import sqlite3
from sqlite3 import Error
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Charger les variables d'environnement avec des valeurs par défaut
load_dotenv('config.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL'))
DATABASE_URL = os.getenv('DATABASE_URL')

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verification de la config
if not BOT_TOKEN:
    logger.error("Le token du bot n'est pas défini dans config.env")
if not RSS_FEED_URL:
    logger.error("L'URL du flux RSS n'est pas défini dans config.env")
if not UPDATE_INTERVAL:
    logger.error("L'interval n'est pas défini dans config.env")
if not DATABASE_URL:
    logger.error("L'URL de la base de donnée n'est pas défini dans config.env")

# Initialisation du bot
bot = telebot.TeleBot(BOT_TOKEN)

# Connexion à la base de données
def create_connection():
    """ Crée une connexion à la base de données SQLite """
    try:
        conn = sqlite3.connect(DATABASE_URL, check_same_thread=False)
        return conn
    except Error as e:
        logger.error(f"Erreur lors de la connexion à la base de données: {e}")
        raise

conn = create_connection()
cursor = conn.cursor()

def create_table():
    """ Crée la table pour stocker les abonnements """
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions
            (chat_id INTEGER PRIMARY KEY, subscribed BOOLEAN)
        ''')
        conn.commit()
    except Error as e:
        logger.error(f"Erreur lors de la création de la table: {e}")
        raise

create_table()

def is_subscribed(chat_id):
    """ Vérifie si un utilisateur est abonné """
    try:
        cursor.execute('SELECT subscribed FROM subscriptions WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    except Error as e:
        logger.error(f"Erreur lors de la vérification de l'abonnement: {e}")
        return False

def set_subscription(chat_id, subscribed):
    """ Définit l'abonnement d'un utilisateur """
    try:
        cursor.execute('INSERT OR REPLACE INTO subscriptions (chat_id, subscribed) VALUES (?, ?)',
                        (chat_id, subscribed))
        conn.commit()
    except Error as e:
        logger.error(f"Erreur lors de la définition de l'abonnement: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bonjour ! Je suis un robot qui surveille les flux RSS. Utilisez /annonces on pour vous abonner aux annonces.")

@bot.message_handler(commands=['annonces'])
def handle_subscription(message):
    chat_id = message.chat.id
    command = message.text.split()
    
    if len(command) != 2 or command[1] not in ['on', 'off']:
        bot.reply_to(message, "Usage incorrect. Utilisez /annonces on pour vous abonner ou /annonces off pour vous désabonner.")
        return

    subscribed = command[1] == 'on'
    set_subscription(chat_id, subscribed)
    
    if subscribed:
        bot.reply_to(message, "Vous êtes maintenant abonné aux annonces.")
    else:
        bot.reply_to(message, "Vous êtes maintenant désabonné des annonces.")

def check_rss_feed():
    """ Vérifie le flux RSS et envoie les annonces """
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        if not feed.entries:
            logger.warning("Aucune entrée trouvée dans le flux RSS")
            return

        latest_entry = feed.entries[0]
        send_announcement(latest_entry)
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du flux RSS: {e}")

def send_announcement(entry):
    """ Envoie une annonce à tous les chats abonnés """
    announcement = f"""
Nouvelle annonce de {entry.author}:
{entry.title}
{entry.link}
"""
    try:
        cursor.execute('SELECT chat_id FROM subscriptions WHERE subscribed = ?', (True,))
        subscribed_chats = cursor.fetchall()
        
        for chat in subscribed_chats:
            try:
                bot.send_message(chat[0], announcement)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du message au chat {chat[0]}: {e}")
    except Error as e:
        logger.error(f"Erreur lors de la récupération des chats abonnés: {e}")

def schedule_check():
    """ Planifie la vérification du flux RSS """
    schedule.every(UPDATE_INTERVAL).seconds.do(check_rss_feed)

if __name__ == "__main__":
    schedule_check()
    
    # Démarrer le bot dans un thread séparé
    import threading
    threading.Thread(target=bot.polling, args=(True,)).start()
    
    # Exécuter les tâches planifiées
    while True:
        schedule.run_pending()
        time.sleep(1)
