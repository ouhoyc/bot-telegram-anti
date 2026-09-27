"""
Bot ODR : surveille les offres de remboursement d'anti-crise.fr
et envoie une alerte Telegram quand une nouvelle offre concerne une marque suivie.

Lancé automatiquement toutes les 30 min par GitHub Actions.
"""

import html
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL_PAGE = "https://anti-crise.fr/les-offres-de-remboursement/"
DOSSIER = Path(__file__).parent
FICHIER_MARQUES = DOSSIER / "marques.txt"
FICHIER_VUES = DOSSIER / "offres_vues.json"

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ---------------------------------------------------------------------------
# Comparaison des marques (tolère majuscules, accents, espaces, tirets, &, +, "et", fautes légères)
# ---------------------------------------------------------------------------
def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c)).lower()
    texte = re.sub(r"\b(et|and)\b", " ", texte)  # "Black et Decker" = "Black & Decker"
    return re.sub(r"[^a-z0-9]", "", texte)  # garde seulement lettres et chiffres


def marque_correspond(marque_suivie: str, marque_site: str) -> bool:
    a, b = normaliser(marque_suivie), normaliser(marque_site)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 4 and a in b:  # ex. "braun" dans "braunseries9"
        return True
    # petite faute de frappe (ex. "karher" pour "karcher")
    return len(a) >= 5 and SequenceMatcher(None, a, b).ratio() >= 0.85


def marques_de_l_offre(texte_marques: str) -> list[str]:
    # "PHILIPS, SENSEO" -> ["PHILIPS", "SENSEO"]
    return [m.strip() for m in texte_marques.split(",") if m.strip()]


def lire_marques_suivies() -> list[str]:
    lignes = FICHIER_MARQUES.read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lignes if l.strip() and not l.strip().startswith("#")]


# ---------------------------------------------------------------------------
# Lecture de la page
# ---------------------------------------------------------------------------
def recuperer_offres(html_page: str) -> list[dict]:
    soup = BeautifulSoup(html_page, "html.parser")
    offres = []
    for carte in soup.select("div.catalogue-item"):
        lien = carte.select_one("a[href]")
        marque = carte.select_one("h6 strong")
        if not lien or not marque:
            continue
        type_offre = carte.select_one(".offer-type")
        image = carte.select_one("img[alt]")
        fin = re.search(r"Fin le (\d{2}/\d{2}/\d{4})", carte.get_text(" "))
        offres.append({
            "lien": lien["href"].split("?")[0],
            "marques": marque.get_text(strip=True),
            "type": type_offre.get_text(strip=True) if type_offre else "",
            "fin": fin.group(1) if fin else "",
            "titre": image["alt"].strip() if image else "",
        })
    return offres


def telecharger_page() -> str:
    reponse = requests.get(
        URL_PAGE,
        headers={"User-Agent": "Mozilla/5.0 (compatible; bot-odr-perso/1.0)"},
        timeout=30,
    )
    reponse.raise_for_status()
    return reponse.text


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def envoyer_telegram(message: str) -> None:
    if not TOKEN or not CHAT_ID:
        print("[test] message qui aurait été envoyé :\n" + message + "\n")
        return
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
        timeout=30,
    )
    r.raise_for_status()


def formater_alerte(offre: dict) -> str:
    e = html.escape
    lignes = [f"🔔 <b>Nouvelle ODR : {e(offre['marques'])}</b>"]
    if offre["titre"]:
        lignes.append(e(offre["titre"]))
    if offre["type"]:
        lignes.append(f"Type : {e(offre['type'])}")
    if offre["fin"]:
        lignes.append(f"Fin le : {e(offre['fin'])}")
    lignes.append(f'<a href="{e(offre["lien"])}">Voir l\'offre</a>')
    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------
def main() -> int:
    marques_suivies = lire_marques_suivies()
    premier_lancement = not FICHIER_VUES.exists()
    etat = {"vues": [], "alerte_page_vide": False}
    if not premier_lancement:
        etat.update(json.loads(FICHIER_VUES.read_text(encoding="utf-8")))
    deja_vues = set(etat["vues"])

    offres = recuperer_offres(telecharger_page())
    print(f"{len(offres)} offres trouvées sur la page.")

    # Sécurité : si la page ne donne plus rien, le site a sûrement changé
    if not offres:
        if not etat["alerte_page_vide"]:
            envoyer_telegram("⚠️ Bot ODR : je ne trouve plus aucune offre sur anti-crise.fr. "
                             "Le site a peut-être changé, il faut vérifier le bot.")
            etat["alerte_page_vide"] = True
        FICHIER_VUES.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0
    etat["alerte_page_vide"] = False

    nouvelles = [o for o in offres if o["lien"] not in deja_vues]

    if premier_lancement:
        print("Premier lancement : offres existantes enregistrées sans alerte.")
        pour_moi = [o for o in offres
                    if any(marque_correspond(m, ms)
                           for m in marques_suivies
                           for ms in marques_de_l_offre(o["marques"]))]
        envoyer_telegram(
            "✅ <b>Bot ODR connecté !</b>\n"
            f"{len(offres)} offres en ligne sur anti-crise.fr, "
            f"dont {len(pour_moi)} pour tes marques.\n"
            f"Je surveille : {html.escape(', '.join(marques_suivies))}\n"
            "Tu seras alerté à chaque nouvelle offre."
        )
    else:
        # du plus ancien au plus récent pour recevoir les alertes dans l'ordre
        for offre in reversed(nouvelles):
            if any(marque_correspond(m, ms)
                   for m in marques_suivies
                   for ms in marques_de_l_offre(offre["marques"])):
                envoyer_telegram(formater_alerte(offre))
                print(f"Alerte envoyée : {offre['marques']} - {offre['lien']}")

    # On garde les offres encore en ligne + les liens récents (limite la taille du fichier)
    liens_actuels = [o["lien"] for o in offres]
    anciens = [l for l in etat["vues"] if l not in liens_actuels]
    etat["vues"] = liens_actuels + anciens[:500]
    FICHIER_VUES.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(nouvelles)} nouvelle(s) offre(s) depuis le dernier passage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
