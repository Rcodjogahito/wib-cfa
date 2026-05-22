# ETAT ACTUEL — WIB CFA
> Mis à jour automatiquement à la fin de chaque session Claude Code.

**Date**: 2026-05-22 (session 38)  
**Commit**: 5c1b372 — "fix(ui): remove ancestor walk that leaked visibility to Fork/Share buttons"  
**Branch**: master → Streamlit Cloud (auto-deploy)

---

## Statut banque questions

| Métrique | Valeur |
|---|---|
| Total questions | 7,249 |
| Complètes (table + explication) | 7,214 |
| Tables manquantes | 4 (faux positifs Kaplan — aucune action) |
| Explications manquantes | 31 (Extra_QB — voir note ci-dessous) |

**Note Extra_QB** : 296/333 explications couvertes (242 verbatim session 17 + 54 nouvelles corrections session 18). 31 restantes vidées. 6 sans correspondance PDF.

**Note Kaplan** : 68 explications corrigées en session 18 (verbatim PDF, matching 100%). 3649 déjà correctes.

**Audit cmd**: `python scripts/audit_questions.py`

---

## Travaux terminés (session 38)

### ✅ Toggle sidebar repositionné + Fork/Share/Favourite masqués — VÉRIFIÉ Playwright (commits 0903933 + 5c1b372)

**Problème** : Le toggle sidebar apparaissait mais les boutons Fork/Share/Favourite étaient aussi visibles.

**Solution** :
- CSS `header[data-testid="stHeader"] { visibility: hidden !important; }` masque tout le toolbar
- Fonction `_hide_toolbar_js()` dans `styles.py` injecte un script via `st.components.v1.html` (iframe same-origin)
- Le script récupère `header.querySelectorAll('button')[0]` (premier bouton = toggle) sans dépendre de `data-testid`
- Toggle repositionné en `position:fixed; top:6rem; left:3.5rem; z-index:2147483647` — plus bas et plus vers le centre de la sidebar
- Tous les descendants du toggle remontent à `visibility:visible` (sans walk ancestor — bug corrigé commit 5c1b372)
- `pytz>=2025.3` (cache bust) force la reconstruction complète de l'environnement Streamlit Cloud

**Bug corrigé (commit 5c1b372)** : La boucle ancestor walk rendait les conteneurs parents `visibility:visible`, propageant la visibilité par héritage CSS aux boutons Fork/Share siblings. Suppression du walk — un enfant avec `visibility:visible` override déjà un parent `visibility:hidden` en CSS.

**Résultats vérification Playwright (2026-05-22)** :
- Header `visibility:hidden` ✅
- btn[0] (toggle) : `pos=fixed top=96px left=58px vis=visible z=2147483647` ✅
- btn[1] (Fork/GitHub) : `vis=hidden` ✅
- Login Sam/to → Initial Diagnostic ✅
- Toutes les pages : Study Notes, Quiz, Flashcards, Progress, Exam Simulator ✅
- Aucun bouton toolbar visible dans aucun screenshot ✅

---

## Travaux terminés (session 37)

### ✅ Fix toggle sidebar — CSS pur, sélecteur corrigé (commit 7a55f7d)

**Problème** : Après avoir masqué le header avec `visibility: hidden`, le bouton toggle de la sidebar (affiché quand la sidebar est fermée) restait invisible. Plusieurs tentatives JavaScript avaient échoué (potentiellement bloquées par la CSP de Streamlit Cloud).

**Cause racine identifiée** : Dans Streamlit 1.38, le `data-testid="stSidebarCollapsedControl"` est sur un **div wrapper**, pas sur le `<button>`. Toutes les tentatives précédentes utilisaient `button[data-testid="stSidebarCollapsedControl"]` — sélecteur qui ne correspondait jamais.

**Diagnostique** : La console du navigateur a montré que le JS de l'iframe est bloqué par SES (Secure EcmaScript, injecté par une extension navigateur). Aucune ligne `[WIB]` visible → l'approche JS est impossible dans cet environnement.

**Solution définitive (commit 6a9322e)** — Approche overlay sans CSS de header, sans JS, sans data-testid :
1. **Supprimer** toute manipulation `visibility` sur le header
2. **Injecter une div fixe** via `st.markdown` qui recouvre la zone toolbar :
```html
<div id="wib-toolbar-mask" style="
    position:fixed; top:0; left:3rem; right:0; height:3.75rem;
    background:#FAFBFC; z-index:99999;
"></div>
```
- `left:3rem` : laisse les ~48px du toggle visible à gauche
- `background:#FAFBFC` : couleur identique au fond de l'app → overlay invisible pour l'utilisateur  
- `z-index:99999` : au-dessus du header de Streamlit Cloud
- Le toggle sidebar (extrême gauche) reste naturellement visible et cliquable

---

## Travaux terminés (session 36)

### ✅ 2 bugs critiques anti-veille corrigés + fréquence augmentée (commit 01d4a48)

**Bug 4 — corrigé** : `keep_alive.yml` — HTTP 200 (page Zzzz = app endormie) était accepté comme "app vivante" (`"2" || "3"`). L'app endormie renvoyait 200 et le workflow reportait SUCCESS alors que l'app dormait → faux positif permanent. Fix : seul le 3xx (redirect auth = app active) est accepté. Le 200 provoque `exit 1` + message d'erreur.

**Bug 5 — corrigé** : Les deux workflows pingaient aux **mêmes horaires** (00:00/06:00/12:00/18:00 UTC). Si GitHub rate un slot (cron non garanti), les deux ratent → gap jusqu'à 12h → app s'endort. Fix : schedules décalés + fréquence doublée.

### ✅ Architecture anti-veille finale (3 niveaux)

| Mécanisme | Fréquence | Horaires UTC | Action | Fichier |
|---|---|---|---|---|
| Playwright (Chromium) | Toutes les 3h | 00:00/03:00/06:00/.../21:00 | Charge la page, clique "Wake up" si endormie | `keep-alive.yml` |
| curl ping | Toutes les 3h | 01:30/04:30/07:30/.../22:30 | Ping HTTP — 303=vivante, 200=endormie→exit 1 | `keep_alive.yml` |
| Heartbeat commit | 1er du mois | 08:00 UTC | Commit timestamp → réinitialise timer 60j GitHub | `heartbeat.yml` |

**Gap maximal entre deux pings : 1h30** (Playwright et curl alternent décalés de 1h30).

## Travaux terminés (session 35)

### ✅ Audit complet + 3 bugs corrigés + protection permanente anti-veille

**Bug 1 — corrigé** : `keep_alive.yml` — `curl -L` causait exit code 47 (CURLE_TOO_MANY_REDIRECTS). Commit `62fa2e6`.

**Bug 2 — corrigé** : `src/styles.py` — CSS `--navy-50` non défini → fond transparent dans Flashcards. Commit `c36f2c3`.

**Bug 3 — résolu** : GitHub désactive les workflows `schedule` après 60j sans commit. Fix : `heartbeat.yml` commit mensuel autonome. Commit `ba7c57d`.

---

## Travaux terminés (session 34)

---

## Travaux terminés (session 14)

### ✅ TÂCHE 1 — Réponses Kaplan
- **Script**: `scripts/fix_kaplan_v2.py`
- **Résultat**: 154 corrections appliquées, distribution finale A=38%/B=31%/C=30%
- **Algo**: 4-pass zero-API (lettre explicite → texte exact → stemmed+fuzzy overlap → numérique)

### ✅ TÂCHE 2 — 49 explications manquantes
- **Scripts**: `scripts/patch_explanations.py` (batch 1, 17 items) + inline Python (batch 2, 16 items) + `scripts/batch3_explanations.py` (batch 3, 16 items)
- **Résultat**: 49/49 appliquées, 11 corrections de réponses incluses
- **Méthode**: explications rédigées inline dans la conversation (zéro appel API Anthropic)

### ✅ TÂCHE 3 — 28 tables UWorld manquantes
- **Scripts**: `scripts/render_table_pages.py` → images PNG, `scripts/rerender_wrong_pages.py` → correction pages erronées, `scripts/patch_uworld_tables.py` → mise à jour Supabase
- **Résultat**: 28/28 tables insérées dans `question_en`
- **Méthode**: lecture images PDF avec Claude Vision (inclus dans abonnement Pro)

---

## Travaux terminés (session 33)

### ✅ Fix sidebar invisible — toutes les pages (commit 45bbc10)

**Cause racine** : `header[data-testid="stHeader"] { display: none !important; }` dans `src/styles.py` masquait le bouton toggle de la sidebar, rendant celle-ci inaccessible.

**Corrections** :
1. **`src/styles.py`** : suppression de la règle CSS `header[data-testid="stHeader"]`. La suppression des boutons Fork/Share/Star est assurée par `toolbarMode = "minimal"` dans `.streamlit/config.toml` (suffisant).
2. **Toutes les pages** (`1_Study`, `2_Quiz`, `3_Flashcards`, `4_Progress`, `5_Exam_Simulator`, `admin.py`) : `initial_sidebar_state="collapsed"` → `"expanded"`.

### ✅ Audit complet de l'application (session 33)

Audit de tous les fichiers — aucun problème trouvé :
- `streamlit_app.py` — dashboard, diagnostic, imports, cookie auth : OK
- `pages/1_Study.py` — lecteur notes, topic selector, CTA quiz : OK
- `pages/2_Quiz.py` — timer fragment, save_attempt/save_session/update_progress, nav grid 5 cols : OK
- `pages/3_Flashcards.py` — Leitner 5 boîtes, get_leitner_states/update_leitner_card, save_session : OK
- `pages/4_Progress.py` — radar chart, gauge, bars, session history : OK
- `pages/5_Exam_Simulator.py` — 2 sessions, timer fragment, save on submit, topic-weighted selection : OK
- `pages/admin.py` — gate `user["email"] == "samto"`, get_all_users, get_question_stats : OK
- `src/auth.py` — cookie 90j, composite key, require_auth, logout : OK
- `src/database.py` — Supabase/SQLite dual-path, toutes les méthodes appelées par les pages existent : OK
- `src/adaptive.py` — poids gradués 5x/3x/2x/1x + boost 2x wrong, get_exam_questions : OK
- `src/progress.py` — compute_mastery_map, readiness_score, weak_topics : OK

### ✅ Logo WIB — thin bar + EB Garamond (sessions 32-33)

Logo "initial" (commit 2445eb8) modifié :
- Suppression de la barre épaisse (2.5px), conservation de la barre fine (1px, rgba gold 45%)
- Police "WIB" : Cormorant Garamond → **EB Garamond** (font-weight 500)
- Sidebar : `font-family:'EB Garamond','Cormorant Garamond',Georgia,serif;font-size:1.72rem;font-weight:500`
- Hero : idem + `font-size:3.1rem`
- Import Google Fonts : `EB Garamond:ital,wght@0,400;0,500;0,600;1,400` ajouté

---

## Travaux terminés (session 32)

### ✅ Refonte logo WIB — device "///", Cormorant 600, tracking affiné (commit 0d7ef5d)

**Inspiration** : Ares Management (autorité institutionnelle) + Rothschild (Five Arrows abstrait).

**Device** : trois barres obliques `///` en Cormorant Garamond 300 avec opacité en cascade (25%→58%→100%), référençant les Five Arrows de Rothschild de façon abstraite et contemporaine.

**Sidebar brand** :
- Device `///` en Cormorant 300, or en cascade
- "WIB" en Cormorant 600, or `#C9A84C`, taille 2.1rem, tracking 0.32em
- "CFA Level I" en Inter 300, blanc 30%, tracking 0.18em, uppercase

**Hero (homepage)** :
- Device `///` scaled up (1.15rem) avec mêmes opacités
- "WIB" en Cormorant 600, 3.5rem, tracking 0.35em (vs. weight 700 + 6px fixe avant)
- Tagline en Inter 300, blanc 38%, tracking 0.18em

**Changements techniques** :
- `.wib-hero .brand-rule` : `display: none` → `display: block` + typographie définie
- `.wib-hero .brand` : `font-weight: 700; letter-spacing: 6px` → `font-weight: 600; letter-spacing: 0.35em`
- Breakpoints responsive mis à jour (768px: 2.6rem/0.28em, 480px: 2.1rem/0.22em)
- `_SIDEBAR_BRAND` entièrement refondu avec structure padding + device + wordmark + descriptor

---

## Travaux terminés (session 31)

### ✅ Audit UX + fixes techniques (commit 937e759)

**Bugs critiques corrigés :**

1. **Variable shadowing `weak_topics`** (`streamlit_app.py:321`) — `weak_list = sorted(...)` remplace la variable locale qui écrasait la fonction importée `weak_topics()` de `src/progress.py`. Causait un `TypeError: 'list' object is not callable` au chargement du dashboard.

2. **Bouton "Start training →"** (`streamlit_app.py:338`) — `st.rerun()` → `st.switch_page("pages/2_Quiz.py")`. Le bouton post-diagnostic naviguait nulle part au lieu d'ouvrir le quiz.

3. **Timer label** (`pages/2_Quiz.py:245`) — `"restantes"` → `"remaining"`. Seul terme en français restant dans l'UI.

**Performance :**

4. **N+1 Supabase queries éliminé** (`src/database.py`) — `get_questions(topic=None)` faisait 10 appels série (1 par topic). Remplacé par 1 seul appel + groupement client-side par topic + shuffle. Réduction de latence ~9x sur le chargement quiz "All (Adaptive)".

**UX mobile :**

5. **Quiz grid navigator** (`pages/2_Quiz.py`) — 10 colonnes → 5 colonnes. Sur mobile 320px, les 10 mini-boutons étaient inutilisables (~30px chacun). Maintenant 5 boutons confortables.

6. **CSS responsive étendu** (`src/styles.py`) — Ajout de breakpoints manquants pour flashcard-front/back, question-option, pass/fail banner, topic-badge, study-content. Ajout breakpoint `480px` pour les très petits écrans.

---

## Travaux terminés (session 30)

### ✅ Flashcards — vrai système Leitner 5 boîtes avec spaced repetition (commit 849452a)

**Table Supabase créée** : `user_flashcard_state (id, user_id, card_id, box, next_review_at, times_correct, times_wrong, updated_at)` + index `idx_ufs_user_review` + RLS.

**Intervalles de révision** :
- Box 1 (rouge) → revu immédiatement (0 jour)
- Box 2 (orange) → +1 jour
- Box 3 (jaune) → +3 jours
- Box 4 (vert) → +7 jours
- Box 5 (vert foncé) → +14 jours (maîtrisé)

**Logique de session** : cartes dues (next_review_at ≤ now) en priorité, puis nouvelles cartes. Cartes non encore dues exclues de la session.

**UI** :
- Avant session : compteur "X due · Y new · Z mastered"
- Sur chaque carte : indicateur ●●●○○ + label boîte + prévisualisation next-box
- "I knew it" → boîte +1, next_review_at planifié
- "Study more" → retour boîte 1, revu immédiatement
- Fin de session : distribution visuelle par boîte (colonnes colorées)

**DB methods ajoutées** :
- `get_leitner_states(user_id)` → dict {card_id: state}
- `update_leitner_card(user_id, card_id, knew_it)` → upsert avec calcul automatique next_review_at
- `timedelta` ajouté à l'import datetime

### ✅ Exam Simulator — 100% conforme CFA Institute 2026 (commit 849452a)

**Bug corrigé** : _TOPIC_COUNTS_45 — Portfolio Management était à 7 (15.6%, hors range officiel 8-12%). Corrigé à 4 (8.9%). Tous les topics du partiel 45Q sont maintenant dans les ranges officiels CFA.

**Timing partiel corrigé** : 75 min → 67 min (45 questions × 90 sec/question = 67.5 min, conforme au rythme officiel CFA).

**Standards officiels ajoutés dans l'expander** :
- Format : 180 MCQ · 3 choix · 2 sessions × 90Q × 135 min · ~90 sec/question
- Scoring : equally weighted · no negative marking
- Pass rate : ~41% historique, ~43-45% récent
- MPS : ~67-69% empiriquement (non publié par le CFA Institute)
- Tableau complet des pondérations avec % réels vs ranges officiels

**Message résultat** : "CFA benchmark: ~67–69% empiriquement (MPS set by CFA Institute, not published)"

### ✅ Informations CFA confirmées (recherche officielle)

- MPS non publié, ~67-69% empiriquement (300Hours, 20k+ candidats)
- Toutes les questions également pondérées, pas de pénalité pour mauvaise réponse
- Format 2026 inchangé vs 2025 : 180Q, 2×90Q×135min, mêmes 10 topics
- Taux de réussite Feb 2026 : 43-45% (first-time ~49-52%)

---

## Travaux terminés (session 29)

### ✅ Système d'apprentissage adaptatif — refonte complète (commit 535cb60)

**Audit préalable** : 4 lacunes identifiées.

**Fix 1 — `src/database.py`** : nouvelle méthode `get_wrong_question_ids(user_id, limit=400)` — requête `user_attempts WHERE is_correct=False ORDER BY attempted_at DESC`.

**Fix 2 — `src/adaptive.py`** : algorithme entièrement réécrit.
- Poids gradués par mastery (binaire 50% → 4 paliers) :
  - 0-30% → 5x | 30-50% → 3x | 50-70% → 2x | 70%+ → 1x
- **Boost 2x supplémentaire** sur chaque question déjà ratée par l'utilisateur
- Nouvelle fonction `get_exam_questions(user_id, topic_counts, db)` : respecte les poids CFA officiels par topic, mais au sein de chaque topic priorise les questions ratées

**Fix 3 — `pages/5_Exam_Simulator.py`** : `_fetch_questions()` utilise maintenant `get_exam_questions()` — l'examen d'entraînement est personnalisé par profil utilisateur tout en respectant la répartition CFA officielle.

**Fix 4 — `streamlit_app.py`** : après le diagnostic, affiche les topics faibles (< 50%) avec un encadré "Recommended focus areas" et un bouton "Start training →" (remplace "Go to dashboard"). Les 3 topics les plus faibles sont listés explicitement.

**Lacune restante (non traitée)** : Leitner binaire → vraies boîtes 1-5 avec spaced repetition. Nécessite migration de schéma DB (nouvelle table `user_flashcard_state`).

---

## Travaux terminés (session 28)

### ✅ Fix capitalisation — "Who Wants to Be an Investment Banker?"

**Problème** : Le texte s'affichait "Who wants to be an Investment Banker?" (minuscules) à cause d'une règle Streamlit base qui surchargait nos styles CSS.

**Correction** : Ajout de `text-transform: none !important` sur deux sélecteurs dans `src/styles.py` :
- `.wib-page-header .brand-fullname` (en-tête toutes les pages)
- `.wib-hero .tagline` (hero de la homepage)

**Cache bust** : `pytz>=2024.7` dans `requirements.txt` pour forcer un rebuild Streamlit Cloud complet.

**Commit** : `79985bb`

---

## Travaux terminés (session 27)

### ✅ Refonte logo WIB — inspiré Ares Management

**Commits** : `16fa58f` (v1 Cormorant Light) → `2445eb8` (Ares-inspired, actif)

**Design DNA Ares** implémenté dans `src/styles.py` :
- **Double-barre géométrique** (2.5px or plein + 1px or/35%) au-dessus du wordmark — signature mark d'Ares
- **Wordmark WIB en blanc** (#FFFFFF) — Ares réserve le blanc pour le wordmark principal sur fond sombre, l'or pour les accents
- **Poids SemiBold (600)** — autorité institutionnelle (vs 700 trop blog, 300 trop fashion)
- **Tracking mesuré 0.16em** — précision institutionnelle (vs 0.38em trop luxe)
- **Descripteur "CFA · Level I"** en or atténué (rgba gold 62%) — accent couleur subordonné
- **Logo initial conservé** dans `_SIDEBAR_BRAND_ORIGINAL` pour rollback
- **Hero** : même double-barre via CSS `::before`/`::after` sur `.brand-rule`, tagline gold-tinted, règle bottom unique 1.5px

---

## Travaux terminés (sessions 25–26)

### ✅ Sidebar mobile — fermeture automatique après navigation (solution définitive)

**Problème persistant** : après 7 tentatives (React btn.click, CSS translateX, polling URL, inline styles), la sidebar disparaissait l'espace d'un instant puis réapparaissait systématiquement sur iPhone.

**Cause racine** : Streamlit restaure le state React de la sidebar ~400-700 ms après chaque navigation SPA. Sur iOS Safari, `btn.click()` ne déclenche pas les event handlers React. Impossible de fermer la sidebar React depuis JS sans race condition.

**Solution finale — full-page reload** (`src/styles.py`, commit b4f98a1) :
- Sur mobile, intercepter les clics sur `<a href>` dans la sidebar (capture phase)
- `e.preventDefault()` + `e.stopImmediatePropagation()` — annule la navigation SPA
- `par.location.href = href` — force un rechargement complet de la page
- La page cible se charge avec `initial_sidebar_state="collapsed"` → sidebar fermée nativement
- Aucune manipulation React, aucune course de timing, fonctionne sur tous les navigateurs

**Commits** : `e9031f8` (tentatives précédentes) → `b4f98a1` (solution finale)

---

## Travaux terminés (session 24)

### ✅ Fix affichage pseudo dans la sidebar — toutes les pages

**Problème** : la sidebar affichait "Samto" au lieu de "Sam". Cause : lors de la restauration depuis cookie, `get_user_by_id` retournait le `first_name` stocké en DB (`"Samto"` issu de l'ancienne interface mono-champ) sans jamais le mettre à jour.

**Corrections appliquées :**

1. **`src/database.py` — `get_or_create_user`** : si l'utilisateur existe et que son `first_name` diffère du pseudo saisi, mise à jour immédiate en DB (Supabase + SQLite). Garantit la synchronisation à chaque login.

2. **Supabase — correction directe** : `first_name` mis à jour de `"Samto"` → `"Sam"` pour `email="samto"` via script Python + service key.

3. **Compte orphelin supprimé** : ancien compte `email="sam"` (créé sur l'ancienne interface mono-champ, vide de données utiles) supprimé (1 session + user).

4. **`src/styles.py` — `render_sidebar_user(username)`** : nouvelle fonction centralisée pour afficher le pseudo dans la sidebar. Remplace le `st.markdown(...)` dupliqué sur les 7 pages (streamlit_app + 5 inner pages + admin).

5. **Cache Streamlit Cloud** : `pytz>=2024.2` dans `requirements.txt` pour forcer un rebuild complet de l'environnement.

**Vérification composite key** : testé que `"Sam" + "ab"` → clé `"samab"` → compte distinct. La collision n'est possible que si deux utilisateurs choisissent exactement le même pseudo ET les mêmes 2 lettres de nom — ce qui est la définition de l'identifiant.

**Commits** : `1b14bd1`, `ef2ec08`, `5d40f87`, `17f3335`

---

## Travaux terminés (session 23)

### ✅ Authentification — clé composite pseudo + suffix nom (`src/auth.py`)

Refonte du système de connexion : l'identifiant unique n'est plus le pseudo seul, mais la combinaison `pseudo.lower() + suffix.lower()` (2 dernières lettres du nom de famille). Stocké dans le champ `email` de la table `users` ; le pseudo (tel que saisi) est stocké dans `first_name` pour l'affichage.

- Formulaire 2 champs : "Pseudo" + "Last 2 letters of your surname" (max 2 chars)
- Validation : pseudo 3-30 chars `[A-Za-z0-9_À-ÿ]`, suffix exactement 2 lettres
- Admin : pseudo "Sam" + suffix "to" → clé "samto"
- Nettoyage Supabase : tous les anciens comptes effacés (12 users, 218 attempts, 18 sessions, 40 progress rows)
- Cookie 90j inchangé — persistance session fonctionnelle

### ✅ Admin — traduction anglaise + clé admin (`pages/admin.py`)

- `_ADMIN_EMAIL = "samto"` (était "sam")
- Toutes les sections, colonnes et métriques traduites en anglais
- Colonnes DataFrame : "Pseudo", "Registered", "Diagnostic", "Diag. score", "Sessions", "Last active"

### ✅ Quiz UX — difficulté "Easy" + expander résultats (`pages/2_Quiz.py`)

- Filtre difficulté complété : ajout de "Easy" → `{"All": None, "Easy": "easy", "Medium": "medium", "Hard": "hard"}`
- Expander "Review all questions" maintenant `expanded=True` par défaut

### ✅ Flashcards UX — séparateur avant "New session" (`pages/3_Flashcards.py`)

- `st.divider()` ajouté entre les sélecteurs topic/mode et le bouton "New session" pour une hiérarchie visuelle plus claire

---

## Travaux terminés (session 22)

### ✅ Exam Simulator — conformité CFA Level 1 officielle (`pages/5_Exam_Simulator.py`)

Réécriture complète pour respecter les standards officiels du CFA Institute (2026).

**Changements apportés :**

| Aspect | Avant | Après |
|---|---|---|
| Sélection des questions | Aléatoire uniforme | Pondérée par topic (poids officiels CFA) |
| Structure full exam | 1 session × 180Q × 270min | 2 sessions × 90Q × 135min |
| Timer | 1 timer global | Timer par session (remise à zéro entre sessions) |
| Transition S1→S2 | N/A | Écran de pause inter-session (réponses S1 verrouillées) |
| Navigation | Libre sur toutes les questions | Cloisonnée à la session en cours |
| Pass/fail | "70% threshold" (officiel) | "70% benchmark (indicatif — MPS réel non publié)" |
| Résultats full | Score global uniquement | Score S1 + Score S2 + Score global |
| Setup screen | Aucune info sur les topics | Table officielle des pondérations CFA 2026 |

**Topic allocation (180Q full exam) :**

| Topic | Q | % |
|---|---|---|
| Ethics & Professional Standards | 27 | 15.0% |
| Quantitative Methods | 14 | 7.8% |
| Economics | 14 | 7.8% |
| Financial Statement Analysis | 21 | 11.7% |
| Corporate Issuers | 14 | 7.8% |
| Equity Investments | 21 | 11.7% |
| Fixed Income | 21 | 11.7% |
| Derivatives | 12 | 6.7% |
| Alternative Investments | 15 | 8.3% |
| Portfolio Management | 21 | 11.7% |

Toutes les valeurs rentrent dans les fourchettes officielles CFA. Même logique proportionnelle pour le partiel (45Q).

---

## Travaux terminés (session 21)

### ✅ Audit options + réponses — toutes sources (script `audit_fix_options_answers.py`)

Vérification rigoureuse que chaque proposition de réponse (option_a/b/c) et bonne réponse (correct_answer) correspondent exactement aux documents source originaux dans `D:\CLAUDE\Projet CFA\CFA L1`.

| Source | Matchées | Options fausses | Réponses fausses | Corrigées |
|---|---|---|---|---|
| UWorld | 1882/1897 | 1 | 3 | **3** |
| Kaplan | 3717/3717 | 39 | 1030 | **1048** |
| Extra_QB | 331/333 | 0 | 0 | 0 |
| Kevin_Mock | 180/180 | 1 (faux-positif) | 0 | 0 |

- **UWorld** : 3 questions corrigées (1 lot d'options, 2 bonnes réponses). 103 bonnes réponses non vérifiables (3 PDFs `Answers` hangent pdfplumber : 1.03, 5.12, 11.03). Timeout threading 60s ajouté.
- **Kaplan** : 1048 corrections appliquées (39 options + 1030 bonnes réponses, sim=1.00 pour toutes). L'algorithme `_detect_v2_kaplan` lit le texte d'explication du PDF pour déduire la bonne réponse (même algo que fix_kaplan_v2.py session 14, mais appliqué à toutes les questions).
- **Extra_QB** : Aucun problème — 331/333 matchées, toutes correctes.
- **Kevin_Mock** : 1 faux-positif détecté et NON appliqué. Deux questions partagent le même stem générique ("Which of the following statements is most likely accurate?"). Les deux sont correctement stockées en DB. Faux-positif résolu par amélioration du LUT (voir ci-dessous).
- **Amélioration script** : `_build_lookup`/`_lookup` modifiés pour stocker plusieurs candidats par clé et sélectionner celui avec la meilleure similarité d'options vers la question DB (évite les faux-positifs sur stems courts/génériques).

**Script** : `scripts/audit_fix_options_answers.py [--dry-run] [--source uworld|kaplan|extra|kevin|all]`

---

## Travaux terminés (session 20)

### ✅ Audit complet explications — toutes sources (script `audit_fix_all_explanations.py`)
- **UWorld** : 6 explications corrigées (sim=1.00 ou 0.81 à 120 chars). 3 PDFs ignorés (hang pdfplumber : 1.03, 5.12, 11.03). min_length relevé 60→120 pour éliminer faux-positifs.
- **Kaplan** : 0 correction — 3717/3717 déjà correctes à 100%.
- **Extra_QB** : 0 correction — 242/333 matchées, toutes déjà correctes.
- **Kevin_Mock** : 41 explications corrigées (sim=1.00, 176/180 matchées).
- **Résultat** : 47 corrections appliquées au total (verbatim PDF).

### ✅ Améliorations UI/UX (session 20)
- **Quiz** : textes de résultats corrigés ("Réussi !" → "Passed!", "À retravailler" → "Needs work")
- **Quiz** : boutons réponses désactivés montrent maintenant ✓ sur la bonne réponse et ✗ sur le mauvais choix
- **Quiz** : barre de progression basée sur les questions répondues (pas la position)
- **Quiz** : grille navigation dépliée par défaut (expanded=True)
- **Quiz** : review final — toggle "Show explanations for correct answers too"
- **Exam Simulator** : grille navigation "Naviguer entre les questions" → "Navigate questions"
- **Exam Simulator** : quand "Show incorrect only" = False, les explications s'affichent aussi pour les bonnes réponses
- **Flashcards** : warning "Aucune flashcard disponible." → "No flashcards available."
- **Flashcards** : bouton "Skip →" → "Next →" sur la face avant de la carte

---

## Travaux terminés (session 19)

### ✅ Traduction UI complète en anglais
- **Fichiers modifiés (7)** : `streamlit_app.py`, `pages/1_Study.py`, `pages/2_Quiz.py`, `pages/3_Flashcards.py`, `pages/4_Progress.py`, `pages/5_Exam_Simulator.py`, `src/auth.py`
- **Scope** : uniquement les paramètres UI (boutons, labels, titres, captions, messages d'erreur, KPIs, annotations graphiques). Les questions/options/explications QCM **non modifiées** (déjà en anglais).
- **Commit** : `5ab55cb`
- **Traductions clés** :
  - Sidebar : "Home", "Study Notes", "Quiz", "Flashcards", "Progress", "Exam Simulator", "Sign out"
  - Auth : "Sign in", "Username", "Enter WIB"
  - Diagnostic : "Initial Diagnostic", "Select your answer", "Confirm", "Correct!", "Incorrect — Correct answer:", "Explanation"
  - KPIs : "Readiness score", "Global accuracy", "Mastered topics", "Completed sessions", "Diagnostic score"
  - Quiz : "All (Adaptive)", "Medium/Hard", "Confirm", "Select your answer", difficulty badges "Easy/Medium/Hard"
  - Flashcards : "All", "Free review", "Leitner mode (adaptive)", "Reveal", "Skip →", "I knew it", "Study more", "Knew", "Remaining", "Session complete"
  - Progress : "Readiness", "Accuracy", "Mastery by topic", "Target: 70%", "Session history", "Partial exam", "Full exam"
  - Exam Simulator : "Exam Simulator", "Start {name}", "Submit exam", "Flag/Flagged ★", "PASSED/FAILED", "Results by topic", "Detailed review"
  - Study Notes : "Study Notes", "Choose a topic", "Content/Exam Tips" tabs, "Example", "Key Points"

---

## Travaux terminés (session 18)

### ✅ Audit explications — Kaplan + Extra_QB (script `audit_fix_all_explanations.py`)
- **Kaplan** : 68/3717 explications corrigées (verbatim PDF). 100% des questions matchées (0 non-trouvées).
- **Extra_QB** : 54/333 explications corrigées (verbatim PDF). 242/333 matchées.
- **UWorld/Kevin_Mock** : SKIP délibéré — faux-positifs de matching détectés en dry-run (ex. explication "impact of inflation" liée à une question "cross rate"). Risque de dégradation > risque de conserver l'existant.
- **Script** : `scripts/audit_fix_all_explanations.py [--dry-run] [--source kaplan|extra|all]`

### ✅ UX overhaul — Session 18
- **Bouton "Valider"** : remplace "VALIDER MA REPONSE" (déjà fait en session précédente, confirmé)
- **Difficulté en français** : "Easy/Medium/Hard" → "Facile/Moyen/Difficile" partout (Quiz, Diagnostic)
- **Selects en français** : "All (Adaptatif)" → "Tous (Adaptatif)", "All" → "Tous" (Flashcards)
- **Boîte explication** : ajout `white-space: pre-wrap` (préserve les sauts de ligne PDF), bordure gauche dorée, label "EXPLICATION" au-dessus
- **Navigation quiz/exam** : bouton de la question courante en style "primary" (navy) dans la grille
- **Flashcard** : "Example:" → "Exemple :"
- **Diagnostic** : "3 per topic" → "3 par topic"
- **Navigation quiz** : bouton inline "Question suivante →" après feedback, grille de navigation
- **Fichiers modifiés** : `pages/2_Quiz.py`, `pages/3_Flashcards.py`, `pages/5_Exam_Simulator.py`, `streamlit_app.py`, `src/styles.py`

---

## Travaux terminés (session 17)

### ✅ Audit et correction des explications Extra_QB
- **Diagnostic** : Les 333 questions Extra_QB avaient des explications mélangées (données de topics erronés). L'import original ne capturait pas les explications (`expl: ""`), puis un patch ultérieur les avait insérées en désordre.
- **Script** : `scripts/fix_extra_qb_explanations.py`
- **Résultat** : 242/333 explications remplacées par le texte verbatim du PDF (`EXTRA 700 MCQs.pdf`, pages 128-214). 31 explications hors-topic détectées et supprimées (préférable à une explication trompeuse). 56 conservées (plausibles, non vérifiables sans re-parsing).
- **Méthode** : Extraction pdfplumber + de-tripling (police PDF dupliquée) + matching multi-niveaux (120/80/60/40/25 chars normalisés)
- **État fidélité par source** :
  - Kaplan (1000 Q) : ✅ verbatim — PDFs texte, regex `Explanation\n...(Module X.Y)`
  - UWorld (1000 Q) : ✅ verbatim — PDFs texte, entre `Explanation\n` et `Things to remember:`
  - Kevin_Mock (180 Q) : ✅ verbatim — PDFs texte, après lettre réponse
  - Extra_QB (333 Q) : 242 verbatim ✅, 56 non vérifiés, 31 manquants
  - CFA_WEB QB (1000 Q) : Claude Vision extraction depuis scans — fidèle mais non byte-for-byte verbatim (seule option sans OCR)

---

## Travaux terminés (session 15)

### ✅ UX — Timer permanent, bouton Valider, sidebar auto-fermeture (session 16)
- **Quiz** : barre timer toujours visible en haut (temps écoulé ou décompte). L'ancien timer n'était visible que si l'option countdown était cochée.
- **Quiz + Diagnostic** : validation en deux étapes. Clic option → surbrillance + indicateur "Réponse sélectionnée". Bouton **"Valider ma réponse"** (primary) → feedback/explication. Identique à l'Exam Simulator.
- **Sidebar** : JS injecté dans `inject_styles()` ferme automatiquement la sidebar après un clic sur un lien de navigation.
- **Fichiers modifiés** : `pages/2_Quiz.py`, `streamlit_app.py`, `src/styles.py`

### ✅ UX — Localisation complète en français
- `"Select your answer"` → `"Sélectionnez votre réponse"` dans Quiz, Exam Simulator, Diagnostic
- Explication affichée dans le Diagnostic après réponse (correcte ou incorrecte)
- Sidebar entièrement en français sur toutes les pages : Home→Accueil, Study Notes→Fiches de cours, Progress→Progression, Exam Simulator→Simulateur d'examen, Sign out→Déconnexion
- **Fichiers modifiés** : `streamlit_app.py`, `pages/2_Quiz.py`, `pages/3_Flashcards.py`, `pages/4_Progress.py`, `pages/5_Exam_Simulator.py`, `pages/1_Study.py`, `pages/admin.py`

---

## Architecture générale

| Composant | Fichier | Note |
|---|---|---|
| App principale | `streamlit_app.py` | Dashboard + diagnostic |
| Quiz | `pages/2_Quiz.py` | Save par question |
| Flashcards | `pages/3_Flashcards.py` | Leitner DB-persisted |
| Exam Simulator | `pages/5_Exam_Simulator.py` | Save on submit |
| Auth | `src/auth.py` | Cookie 90j |
| DB | `src/database.py` | Supabase + SQLite fallback |
| Admin | `pages/admin.py` | Sam-only |

## Déploiement

```bash
git push origin master  # auto-deploy Streamlit Cloud (~1 min)
```

**URL prod**: https://wib-cfa.streamlit.app/  
**Supabase**: https://qlcakqtrambahrofnhho.supabase.co
