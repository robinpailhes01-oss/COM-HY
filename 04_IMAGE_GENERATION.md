# 04 — GÉNÉRATION D'IMAGES — *Nano Banana (Google) via KIE*

> Ce document est le **moteur visuel** d'Harmonie. Il transforme une demande simple
> (« je veux un post pour le programme de juillet ») en une image **fidèle à la marque**,
> générée par l'IA, sans repartir de zéro à chaque fois.
>
> Il s'appuie sur — et ne contredit jamais — `01_BRAND_FOUNDATION.md`,
> `02_VISUAL_IDENTITY.md`, `03_INSTAGRAM_PLAYBOOK.md`, `06_REFERENCE_LIBRARY.md`.

---

## 0 · RÉALITÉ PRODUIT (rappel)

- **Le bateau :** yacht de **12 mètres** (Atlantis, coque blanche / liseré bleu marine), basé à **Carnon** (Montpellier).
- **Le terrain :** côte méditerranéenne **languedocienne / Occitanie** (≠ Côte d'Azur).
- **Le principe directeur** (cf. `03` Pilier 7) : le bateau peut être **montré clairement**
  (~15–20 % des images), jamais **vendu comme un produit catalogue**.

> ## 🔒 RÈGLE ABSOLUE — TOUJOURS IMAGE-TO-IMAGE *(décision fondateur, 2026-06)*
> **Toute image publiée part désormais de NOS propres photos** (le vrai bateau, nos vrais
> lieux, nos vrais moments). On utilise **exclusivement** `google/nano-banana-edit` avec une
> ou plusieurs photos de référence (`image_urls`). **Plus jamais de texte→image pur** pour
> une publication.
> **Pourquoi :** authenticité + fidélité au vrai Atlantis. On ne veut pas un bateau inventé
> par l'IA, mais *notre* bateau, sublimé. L'IA retouche/prolonge/met en lumière le réel — elle
> ne fabrique pas un faux.
> *(Le texte→image reste permis uniquement pour des essais privés internes, jamais publiés.)*

> ## 🔒 COROLLAIRE — PRÉSERVER, NE PAS RÉINVENTER *(décision fondateur, 2026-06)*
> Image-to-image **ne veut pas dire** « recréer une scène qui ressemble ». Quand on part
> d'une vraie photo (notre table, notre plateau, notre bateau), il faut **préserver le sujet
> réel** : mêmes objets, même disposition, mêmes détails. C'est **notre** table, pas une table
> de stock.
> - ❌ **Mauvais prompt** (le modèle invente) : *« compose une élégante nature morte de
>   fruits de mer… »* → il fabrique un nouveau plateau générique.
> - ✅ **Bon prompt** (le modèle édite) : *« garde EXACTEMENT cette table, ce plateau, ces
>   verres, ce bouquet, ne déplace ni ne remplace aucun objet ; modifie SEULEMENT : enlève
>   les personnes en arrière-plan / réchauffe la lumière vers l'heure dorée / étends le cadre
>   en 9:16 ».*
> **Test de validation avant livraison :** *est-ce bien NOTRE table / NOTRE bateau,
> reconnaissable ?* Si non → trop de transformation, on recommence avec un prompt de
> préservation (et on baisse l'ambition de « retouche »).
> **Cas des personnes à retirer :** si la vraie photo contient des invités de face qu'on ne
> peut pas montrer, on demande de **les retirer** en gardant le reste intact — pas de
> reconstruire toute la scène.

---

## 1 · LA FINALITÉ — LE WORKFLOW AUTONOME

L'objectif : que la demande reste **humaine et simple**, et que toute la chaîne brand
se fasse automatiquement derrière.

```
TOI :  « Un post pour le programme de juillet »
                       │
                       ▼
1. JE LIS le contexte   → 01/02/03 (charte) + programme du mois + CATALOGUE photos
2. JE DÉCIDE            → pilier (cf. 03) + émotion + format (4:5 ou 9:16)
3. JE CHOISIS           → la/les photo(s) de référence dans le catalogue (si pertinent)
4. JE RÉDIGE            → le prompt nano-banana à partir du GABARIT-MAÎTRE (§4)
5. JE GÉNÈRE            → script KIE (upload réf → createTask → récupération)
6. JE TE LIVRE          → l'image + une légende + des hashtags, prêts à publier
```

**Ce que tu fournis à chaque fois :** uniquement l'**intention** (le sujet, l'occasion,
le programme). Le reste — pilier, émotion, charte, photo, prompt — c'est moi.

**Le seul input récurrent dont j'ai besoin :** le **contenu du mois** (programme, offres,
dates). Soit tu me le dis en message, soit tu le déposes dans `programmes/AAAA-MM.md`
(voir `programmes/README.md`).

---

## 2 · STACK TECHNIQUE (KIE / Nano Banana)

### 2.1 — Authentification
- Clé API stockée en **variable d'environnement** `KIE_API_KEY` (jamais dans le repo, jamais dans le chat).
- En-tête : `Authorization: Bearer $KIE_API_KEY`.

### 2.2 — Les deux modèles
| Modèle | Usage | Quand |
|---|---|---|
| `google/nano-banana-edit` | **image → image** (jusqu'à 10 réf.) | **PAR DÉFAUT — toujours.** Toute publication part de nos vraies photos (cf. règle absolue §0) |
| `google/nano-banana` | texte → image | **Essais privés internes uniquement.** Jamais publié |

### 2.3 — Les 3 endpoints
1. **Upload d'une référence** (si photo locale) → renvoie une URL temporaire (3 jours) :
   `POST https://kieai.redpandaai.co/api/file-base64-upload`
2. **Lancer la génération** :
   `POST https://api.kie.ai/api/v1/jobs/createTask`
   ```json
   {
     "model": "google/nano-banana-edit",
     "input": {
       "prompt": "…",
       "image_urls": ["https://…"],
       "output_format": "png",
       "aspect_ratio": "4:5"
     }
   }
   ```
   → renvoie `data.taskId`.
3. **Récupérer le résultat** (polling) :
   `GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=…`
   → `data.state` ∈ {`waiting`,`queuing`,`generating`,`success`,`fail`}
   → image dans `data.resultJson` → `resultUrls[]`.

### 2.4 — Formats (`aspect_ratio`)
- **`4:5`** → défaut **feed** (immersion portrait — cf. `02`/`03`).
- **`9:16`** → **stories & réels**.
- `1:1` → grille très éditoriale uniquement. **Jamais `16:9` au feed.**

### 2.5 — Le script
`scripts/generate_image.py` (Python, sans dépendance) fait toute la chaîne :
upload des références → createTask → polling → téléchargement dans `photos/generated/`.
```
KIE_API_KEY=… python3 scripts/generate_image.py \
  --prompt "…" --aspect-ratio 4:5 \
  --ref photos/reference/pont_coucher.jpg \
  --out photos/generated/juillet_pont.png
```

---

## 3 · LA BIBLIOTHÈQUE DE PHOTOS

### 3.1 — Le flux de sourcing
```
Google Drive « Harmonie – Photos »   →   TRIAGE (moi)   →   photos/reference/ (set curé) + CATALOG.md
   (ta boîte de dépôt : tu balances tout)        (je regarde, je tague)       (la bibliothèque de travail)
```
- **Drive = boîte d'entrée.** Tu déposes en vrac (photos téléphone, repérages, vrai bateau).
- **Triage automatique.** Je peux **regarder chaque image**, la décrire et la classer :
  sujet (pont / proue / carré / coque / détail / mer / coucher de soleil), orientation,
  qualité, et **piliers/émotions** auxquels elle sert. Je remplis `photos/CATALOG.md`.
- **Set curé.** Je garde dans `photos/reference/` les meilleures, renommées proprement
  (`pont_coucher_4x5.jpg`, `proue_sillage.jpg`…). C'est là que je pioche pour générer.

### 3.2 — Ce qui fait une bonne photo de référence
Belle lumière naturelle/dorée · cadrage propre · le **vrai** bateau sous plusieurs angles
(pont, proue, carré, vue d'ensemble) · détails de vie à bord (table dressée, lin, coussins).
→ Plus j'ai de vraies photos du 12 m, plus le Pilier 7 sort **fidèle** au vrai bateau.

### 3.3 — Le catalogue (`photos/CATALOG.md`)
Un tableau que je maintiens : `fichier · ce qu'on voit · orientation · piliers · émotions · note`.
C'est ce qui me permet d'aller **chercher tout seul** la bonne photo pour une demande donnée.

---

## 4 · LE GABARIT-MAÎTRE DE PROMPT

Tout prompt est assemblé à partir de **6 briques**, dans cet ordre. Les briques B (style),
E (lumière) et F (interdits) sont **constantes** — elles encodent la charte `02`.

```
[A · SUJET]        ce qu'on voit, l'action, l'émotion (variable selon le pilier)
[B · STYLE]        editorial travel photography, quiet luxury Mediterranean,
                   authentic candid moment, fine-art, soft film grain, premium magazine
[C · CADRE/LIEU]   French Languedoc Mediterranean coast near Carnon/Montpellier (§6)
[D · COMPOSITION]  4:5 portrait, 40–60% negative space, off-center subject, shallow depth
[E · LUMIÈRE]      natural golden-hour light, warm and soft, airy bright palette,
                   sun-bleached tones, gentle haze  (jamais de flash dur)
[F · INTERDITS]    (negative — §7)
```

**Règle d'or.** Avant tout rendu, le prompt doit pouvoir répondre : *quelle émotion ?*
(liberté / gratitude / amour). Sans émotion → on retravaille (cf. `03`).

**Palette à nommer dans le prompt :** blanc cassé, sable, lin, terracotta doux, bleu
Méditerranée délavé, vert olive, or chaud — *jamais* bleu marine clinquant ni or métallique.

---

## 5 · RECETTES PAR PILIER

> `T2I` = texte→image (`google/nano-banana`) · `I2I` = image→image avec réf. (`google/nano-banana-edit`)

| Pilier (cf. `03`) | Mode | Brique [A · SUJET] type |
|---|---|---|
| **1 · Émotion** | T2I | « a fleeting candid moment of calm on a yacht deck, a person seen from behind facing the open sea, wind in linen, a quiet exhale of freedom » |
| **2 · La Mer** | T2I | « the open Mediterranean horizon from the water, soft wake trailing, vast sky, sense of escape and space » |
| **3 · Attentions** | T2I/I2I | « an intimate sensory close-up: a chilled glass against the light, fresh details, a thoughtful gesture, savouring the present » |
| **4 · Souvenirs** | I2I | « a tender shared moment, hands meeting, soft laughter suggested, celebrating together, nostalgic warm memory » |
| **5 · Offrir** | T2I | « an elegant gift-worthy still life, a moment to offer to someone you love, refined and emotional » |
| **6 · Maison** | T2I | « a quiet brand still life evoking craft, sincerity and the art of hosting » |
| **7 · Découvrir** | **I2I** | « the 12-metre yacht shown clearly and elegantly — the deck set for a moment, the prow cutting the water — beautiful light, a discreet sign of life, never a catalogue shot » |

**Pilier 7 = toujours I2I** dès qu'on a une vraie photo du bateau (fidélité au 12 m réel).

---

## 6 · VOCABULAIRE DE TERROIR LOCAL (Carnon / Montpellier)

Pour que l'IA génère un décor **crédible et local**, pas un cliché Saint-Tropez.

**À convoquer :** côte basse et sableuse · lumière méditerranéenne dorée · La Grande-Motte
(architecture pyramidale moderniste, au loin) · Palavas-les-Flots · étang de Thau · Sète ·
Aigues-Mortes et ses remparts · Camargue, flamants roses, salins · Pic Saint-Loup à
l'horizon · eaux calmes et plates · pins parasols · ambiance languedocienne authentique.

**À éviter** (hors terroir) : falaises escarpées type Côte d'Azur, rochers rouges de
l'Estérel, montagnes plongeant dans la mer, palmiers tropicaux, méga-yachts de Monaco.

---

## 7 · NEGATIVE PROMPT — ANTI-CLICHÉS (constant)

À refuser systématiquement (cf. `02` §1.1 et bannis, `03` erreurs interdites) :

```
no people in swimwear posing, no party, no champagne spray, no jet-ski, no flashy gold,
no navy-and-white nautical stripes, no anchor/wheel/rope/porthole decorative motifs,
no stock-photo feel, no harsh flash, no oversaturation, no HDR, no glossy 3D render,
no logos/watermark/text, no front-facing identifiable faces, no catalogue product shot,
no Saint-Tropez cliché, no megayacht, no crowded composition
```

---

## 8 · POST-TRAITEMENT & COHÉRENCE DE GRILLE

- **Un coup d'œil charte** avant livraison : palette claire ? lumière douce ? zéro cliché ?
  vide respecté ? émotion lisible ? (sinon : régénérer, ne pas publier — cf. `03`).
- **Cohérence de feed :** ne pas livrer deux images du bateau (Pilier 7) qui se suivraient
  dans la grille ; alterner avec émotion/mer/citation.
- **Variations :** je peux générer 2–3 variantes et te laisser choisir.

---

## 9 · GARDE-FOUS

| Règle | Pourquoi |
|---|---|
| La clé `KIE_API_KEY` ne quitte jamais l'environnement | Sécurité ; jamais commitée, jamais affichée en clair |
| Pilier 7 (bateau montré) ≤ ~20 % des images | Préserve le quiet luxury (cf. `03`) |
| Toujours nommer lumière + palette + interdits dans le prompt | Garantit la signature Harmonie, pas un rendu IA générique |
| Visages identifiables de face : évités | Confidentialité + projection (« ce pourrait être moi », cf. `03` R3) |
| Vérification charte humaine avant publication | L'IA propose, la marque dispose |

---

*Ce document évolue : chaque référence visuelle que tu m'envoies et chaque réglage
affiné (ratio Pilier 7, recettes, terroir) y est consigné, pour rester reproductible
dans le temps — par un humain comme par l'IA.*
