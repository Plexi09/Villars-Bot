# Bot Telegram RSS

Ce bot Telegram surveille un flux RSS et envoie les nouvelles annonces à tous les groupes où il est présent. Les administrateurs peuvent activer ou désactiver globalement les annonces pour tous les groupes.

## Fonctionnalités

- Surveillance automatique d'un flux RSS configuré
- Envoi des nouvelles annonces à tous les groupes où le bot est présent
- Commande admin pour activer/désactiver globalement les annonces
- Configuration via un fichier `config.env`

## Prérequis

- Python 3.7+
- Pip (gestionnaire de paquets Python)
- Un token de bot Telegram (obtenu via [@BotFather](https://t.me/botfather))
- Une URL de flux RSS à surveiller

## Installation

1. Clonez ce dépôt :

   ```
   https://github.com/Plexi09/Villars-Bot.git
   cd Villars-Bot
   ```
2. Installez les dépendances :

   ```
   pip install -r requirements.txt
   ```
3. Créez un fichier `config.env` à la racine du projet avec le contenu suivant :

   ```
   BOT_TOKEN=votre_token_bot_telegram
   RSS_FEED_URL=https://exemple.com/flux.rss
   UPDATE_INTERVAL=300
   DATABASE_URL=sqlite:///bot_database.db
   ```

   Remplacez `votre_token_bot_telegram` par le token de votre bot et `https://exemple.com/flux.rss` par l'URL du flux RSS que vous souhaitez surveiller.

## Utilisation

1. Démarrez le bot :

   ```
   python bot.py
   ```
2. Dans Telegram, ajoutez le bot aux groupes où vous souhaitez recevoir les annonces.
3. Utilisez les commandes suivantes :

   - `/start` : Affiche un message de bienvenue
   - `/toggle` : (Admin seulement) Active ou désactive les annonces pour tous les groupes

## Structure du projet

- `bot.py` : Code principal du bot
- `config.env` : Fichier de configuration
- `requirements.txt` : Liste des dépendances Python
- `bot_database.db` : Base de données SQLite (créée automatiquement)

## Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à soumettre une pull request.

## Licence

Ce projet est sous licence `GNU General Public License`. Voir le fichier `LICENSE` pour plus de détails.
