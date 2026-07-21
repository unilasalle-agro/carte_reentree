"""
Recalcul automatique des statuts de réentrée
---------------------------------------------
Lit le GeoJSON existant sur GitHub, recalcule les statuts
et les jours restants selon la date du jour, et écrase le fichier.
Déclenché chaque nuit par GitHub Actions.
"""

import json
import base64
import os
import requests
from datetime import date, timedelta

GITHUB_TOKEN    = os.environ['GITHUB_TOKEN']
GITHUB_USERNAME = os.environ['GITHUB_USERNAME']
GITHUB_REPO     = os.environ['GITHUB_REPO']
GITHUB_FICHIER  = os.environ.get('GITHUB_FICHIER', 'parcelles_prod.geojson')

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'GitHubActions-Parcelles'
}

def calculer(date_app_str, nb_jours):
    """Retourne (statut, date_fin, jours_restants)"""
    if not date_app_str or date_app_str == '-' or not nb_jours or nb_jours == '-':
        return 'Accessible', '-', 0
    try:
        date_app = date.fromisoformat(str(date_app_str)[:10])
        date_fin = date_app + timedelta(days=int(nb_jours))
        jours_restants = (date_fin - date.today()).days
        if date.today() > date_fin:
            return 'Accessible', date_fin.isoformat(), 0
        else:
            return 'Accès interdit', date_fin.isoformat(), jours_restants
    except Exception:
        return 'Accessible', '-', 0

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

    # 2. Recalculer les statuts et jours restants
    modifiees = 0
    for feat in geojson['features']:
        p = feat['properties']
        ancien_statut = p.get('statut', 'Accessible')
        statut, date_fin, jours_restants = calculer(p.get('date_application'), p.get('nb_jours'))

        p['statut']          = statut
        p['date_fin']        = date_fin
        p['jours_restants']  = jours_restants

        emoji = '🔴' if statut == 'Accès interdit' else '🟢'
        changed = ' ← CHANGEMENT' if ancien_statut != statut else ''
        jours_txt = f" | {jours_restants}j restants" if jours_restants > 0 else ''
        print(f"  {emoji} {p.get('name', '?'):25} | {statut}{jours_txt}{changed}")
        if ancien_statut != statut:
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
