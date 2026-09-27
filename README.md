# Bot ODR — alertes Telegram anti-crise.fr

Toutes les 30 minutes, le bot lit https://anti-crise.fr/les-offres-de-remboursement/
et t'envoie un message Telegram dès qu'une **nouvelle** offre concerne une marque de `marques.txt`.

## Fichiers
- `bot.py` : le programme
- `marques.txt` : ta liste de marques (une par ligne, modifiable depuis l'app GitHub)
- `.github/workflows/bot.yml` : le lancement automatique toutes les 30 min
- `offres_vues.json` : créé tout seul au premier lancement (mémoire des offres déjà vues)

## Installation (≈ 15 min, une seule fois)

### 1. Créer le bot Telegram
1. Dans Telegram, ouvre **@BotFather** → envoie `/newbot`.
2. Donne un nom (ex. `Alertes ODR`) puis un identifiant finissant par `bot` (ex. `nono_odr_bot`).
3. BotFather te donne un **token** (ex. `123456:ABC-...`). Garde-le secret.

### 2. Récupérer ton identifiant de conversation (chat ID)
1. Ouvre ton nouveau bot dans Telegram et envoie-lui `bonjour`.
2. Dans ton navigateur, ouvre : `https://api.telegram.org/bot<TON_TOKEN>/getUpdates`
   (remplace `<TON_TOKEN>` par le token, sans les < >).
3. Repère `"chat":{"id":123456789` → ce nombre est ton **chat ID**.

### 3. Le code
Déjà en place dans ce dépôt ✅

### 4. Ranger les secrets
Dans le dépôt : **Settings → Secrets and variables → Actions → New repository secret**
- `TELEGRAM_TOKEN` = le token de BotFather
- `TELEGRAM_CHAT_ID` = ton chat ID

### 5. Autoriser le bot à enregistrer sa mémoire
**Settings → Actions → General → Workflow permissions** → coche **Read and write permissions** → Save.

### 6. Premier lancement
Onglet **Actions** → **Bot ODR** → **Run workflow**.
Le premier passage enregistre les offres déjà en ligne **sans t'envoyer d'alerte**.
Ensuite il tourne tout seul toutes les 30 min.

## Au quotidien
- **Ajouter / retirer une marque** : ouvre `marques.txt` sur GitHub (✏️) → modifie → Commit.
  Majuscules, accents, espaces, tirets ou petite faute de frappe : pas grave.
- **Si le site change** : le bot t'envoie « je ne trouve plus aucune offre ». Il faudra adapter `bot.py`.
- **En cas d'erreur** (site inaccessible, etc.) GitHub t'envoie un e-mail.
- Les lancements peuvent avoir quelques minutes de retard, c'est normal avec GitHub.
