import os
import logging
from dotenv import load_dotenv
import telebot
from telebot import types
import feedparser
import schedule
import time
import sqlite3
from sqlite3 import Error

# Charger les variables d'environnement avec des valeurs par défaut
load_dotenv('config.env')
BOT_TOKEN = os.getenv('BOT_TOKEN')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')
UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL'))
DATABASE_URL = os.getenv('DATABASE_URL')
stop_flag = False

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
        logger.info("Connexion à la base de données réussie.")
        return conn
    except Error as e:
        logger.error(f"Erreur lors de la connexion à la base de données: {e}")
        raise

conn = create_connection()
cursor = conn.cursor()

def create_table():
    """ Crée la table pour stocker l'état global des annonces """
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcement_state
            (id INTEGER PRIMARY KEY, enabled BOOLEAN)
        ''')
        logger.info("Table 'announcement_state' créée avec succès.")
        conn.commit()
    except Error as e:
        logger.error(f"Erreur lors de la création de la table: {e}")
        raise

create_table()

def get_announcement_state():
    """ Récupère l'état actuel des annonces """
    try:
        cursor.execute('SELECT enabled FROM announcement_state WHERE id = 1')
        result = cursor.fetchone()
        if result:
            logger.info(f"État actuel des annonces : {result[0]}")
            return result[0]
        else:
            logger.info("Aucun état d'annonce trouvé, initialisation à True.")
            set_announcement_state(True)
            return True
    except Error as e:
        logger.error(f"Erreur lors de la récupération de l'état des annonces: {e}")
        return False

def set_announcement_state(enabled):
    """ Définit l'état global des annonces """
    try:
        cursor.execute('INSERT OR REPLACE INTO announcement_state (id, enabled) VALUES (1, ?)',
                        (enabled,))
        conn.commit()
        logger.info(f"État des annonces mis à jour : {enabled}")
    except Error as e:
        logger.error(f"Erreur lors de la définition de l'état des annonces: {e}")

def stop_bot():
    # Arrêter le bot en douceur
    bot.stop_polling()
    
    # Arrêter les tâches planifiées
    global stop_flag
    stop_flag = True
    
    # Fermer la connexion à la base de données
    if conn:
        conn.close()
        logger.info("Connexion à la base de données fermée.")
    
    logger.info("Bot arrêté.")
    # Terminer le programme
    os._exit(0)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bonjour ! Je suis un robot qui surveille et diffuse les annonces sur le site. Un administrateur peut utiliser /toggle pour activer ou désactiver les annonces pour tout le monde.")
    logger.info(f"Message de bienvenue envoyé à l'utilisateur {message.chat.id}")

@bot.message_handler(commands=['toggle'])
def toggle_announcements(message):
    # Vérifier si l'utilisateur est un administrateur
    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ['creator', 'administrator']:
        bot.reply_to(message, "Seuls les administrateurs peuvent utiliser cette commande.")
        logger.warning(f"Tentative d'utilisation de /toggle par un non-admin : {message.from_user.id}")
        return

    current_state = get_announcement_state()
    new_state = not current_state
    set_announcement_state(new_state)
    
    if new_state:
        bot.reply_to(message, "Les annonces sont maintenant activées pour tout le monde.")
    else:
        bot.reply_to(message, "Les annonces sont maintenant désactivées pour tout le monde.")
    logger.info(f"État des annonces changé à {new_state} par l'administrateur {message.from_user.id}")

@bot.message_handler(commands=['shutdown'])
def shutdown_bot(message):
    # Vérifier si l'utilisateur est un administrateur
    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ['creator', 'administrator']:
        bot.reply_to(message, "Seuls les administrateurs peuvent utiliser cette commande.")
        logger.warning(f"Tentative d'utilisation de /shutdown par un non-admin : {message.from_user.id}")
        return

    # Demander une confirmation à l'utilisateur
    markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text="confirm", callback_data="confirm_shutdown")
    cancel_button = types.InlineKeyboardButton(text="cancel", callback_data="cancel_shutdown")
    markup.add(confirm_button, cancel_button)
    bot.reply_to(message, "Êtes-vous sûr de vouloir éteindre le bot ? Cliquez sur `confirmer` pour éteindre le bot et sur `annuler` pour annuler.", reply_markup=markup)

# Gérer la réponse de confirmation ou d'annulation
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_shutdown", "cancel_shutdown"])
def handle_shutdown_confirmation(call):
    if call.data == "confirm_shutdown":
        bot.send_message(call.message.chat.id, "Le bot s'éteint maintenant...")
        logger.info(f"Confirmation de shutdown reçue de l'administrateur {call.from_user.id}")
        stop_bot()  # Arrêter le bot proprement
    else:
        bot.send_message(call.message.chat.id, "Arrêt annulé.")
        logger.info(f"Shutdown annulé par l'administrateur {call.from_user.id}")

@bot.message_handler(commands=['settings'])
def handle_settings(message):
    # Vérifier si l'utilisateur est un administrateur
    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ['creator', 'administrator']:
        bot.reply_to(message, "Seuls les administrateurs peuvent utiliser cette commande.")
        logger.warning(f"Tentative d'utilisation de /settings par un non-admin : {message.from_user.id}")
        return

    # Parse the command arguments
    try:
        _, option, value = message.text.split(maxsplit=2)
    except ValueError:
        bot.reply_to(message, "La commande est invalide. Utilisez /settings <option> <valeur>.")
        return

    if option not in ['rss_url', 'update_interval']:
        bot.reply_to(message, "Option invalide. Les options disponibles sont : url, interval.")
        return

    if option == 'url':
        update_rss_url(value)
        bot.reply_to(message, f"L'URL du flux RSS a été mise à jour à {value}.")
        logger.info(f"URL du flux RSS mise à jour à {value} par l'administrateur {message.from_user.id}")

    elif option == 'interval':
        try:
            new_interval = int(value)
            update_update_interval(new_interval)
            bot.reply_to(message, f"L'intervalle de mise à jour a été mis à jour à {new_interval} secondes.")
            logger.info(f"Intervalle de mise à jour mis à jour à {new_interval} secondes par l'administrateur {message.from_user.id}")
        except ValueError:
            bot.reply_to(message, "Valeur invalide pour l'intervalle de mise à jour. Veuillez entrer un entier.")

def update_rss_url(new_url):
    global RSS_FEED_URL
    RSS_FEED_URL = new_url

def update_update_interval(new_interval):
    global UPDATE_INTERVAL
    UPDATE_INTERVAL = new_interval
    # Replanifiez la vérification du flux RSS avec le nouvel intervalle
    schedule.clear()
    schedule_check()

def check_rss_feed():
    """ Vérifie le flux RSS et envoie les annonces si elles sont activées """
    if not get_announcement_state():
        logger.info("Les annonces sont désactivées. Vérification du flux RSS ignorée.")
        return

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
    """ Envoie une annonce à tous les chats où le bot est présent """
    announcement = f"""
Nouvelle annonce de {entry.author}:
{entry.title}
{entry.link}
"""
    for chat in bot.get_updates():
        try:
            bot.send_message(chat.message.chat.id, announcement)
            logger.info(f"Annonce envoyée au chat {chat.message.chat.id}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message au chat {chat.message.chat.id}: {e}")

def schedule_check():
    """ Planifie la vérification du flux RSS """
    schedule.every(UPDATE_INTERVAL).seconds.do(check_rss_feed)
    logger.info(f"Vérification du flux RSS planifiée toutes les {UPDATE_INTERVAL} secondes.")

# Drapeau global pour arrêter le bot
stop_flag = False

if __name__ == "__main__":
    schedule_check()
    
    # Démarrer le bot dans un thread séparé
    import threading
    threading.Thread(target=bot.polling, args=(True,)).start()
    logger.info("Bot démarré.")
    
    # Exécuter les tâches planifiées
    while not stop_flag:
        schedule.run_pending()
        time.sleep(1)
