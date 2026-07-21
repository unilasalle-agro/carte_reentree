"""
Recalcul automatique des statuts de réentrée
---------------------------------------------
Lit le GeoJSON existant sur GitHub, recalcule les statuts
selon la date du jour, et écrase le fichier.
Déclenché chaque nuit par GitHub Actions.
"""

import json
import base64
import os
import requests
from datetime import date, timedelta, datetime

GITHUB_TOKEN    = os.environ['GITHUB_TOKEN']
GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
GITHUB_REPO     = os.environ['GITHUB_REPO']
GITHUB_FICHIER  = os.environ.get('GITHUB_FICHIER', 'parcelles_final_v2.geojson')

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'GitHubActions-Parcelles'
}

def calculer_statut(date_app_str, nb_jours):
    if not date_app_str or date_app_str == '-' or not nb_jours or nb_jours == '-':
        return 'Accessible'
    try:
        date_app = date.fromisoformat(str(date_app_str)[:10])
        date_fin = date_app + timedelta(days=int(nb_jours))
        return 'Accès interdit' if date.today() <= date_fin else 'Accessible'
    except Exception:
        return 'Accessible'

def recalculer_date_fin(date_app_str, nb_jours):
    try:
        date_app = date.fromisoformat(str(date_app_str)[:10])
        return (date_app + timedelta(days=int(nb_jours))).isoformat()
    except Exception:
        return '-'

def main():
    print(f"Recalcul des statuts — {date.today().isoformat()}")

    # 1. Récupérer le GeoJSON depuis GitHub
    url = f'https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FICHIER}'
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    meta = res.json()
    sha = meta['sha']

    contenu = base64.b64decode(meta['content'].replace('\n', '')).decode('utf-8')
    geojson = json.loads(contenu)
    print(f"  {len(geojson['features'])} parcelles chargées")

    # 2. Recalculer les statuts
    modifiees = 0
    for feat in geojson['features']:
        p = feat['properties']
        ancien_statut = p.get('statut', 'Accessible')
        nouveau_statut = calculer_statut(p.get('date_application'), p.get('nb_jours'))
        p['statut'] = nouveau_statut
        p['date_fin'] = recalculer_date_fin(p.get('date_application'), p.get('nb_jours'))

        emoji = '🔴' if nouveau_statut == 'Accès interdit' else '🟢'
        changed = ' ← CHANGEMENT' if ancien_statut != nouveau_statut else ''
        print(f"  {emoji} {p.get('name', '?'):25} | {nouveau_statut}{changed}")
        if ancien_statut != nouveau_statut:
            modifiees += 1

    print(f"  {modifiees} statut(s) mis à jour")

    # 3. Écraser le fichier sur GitHub
    nouveau_contenu = json.dumps(geojson, ensure_ascii=False, indent=2)
    b64 = base64.b64encode(nouveau_contenu.encode('utf-8')).decode('utf-8')

    res_put = requests.put(url, headers=HEADERS, json={
        'message': f'Recalcul automatique statuts — {date.today().isoformat()}',
        'content': b64,
        'sha': sha
    })
    res_put.raise_for_status()
    print(f"  Fichier mis à jour sur GitHub")
    print("Terminé ✓")

if __name__ == '__main__':
    main()
