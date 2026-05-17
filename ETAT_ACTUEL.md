# ETAT ACTUEL — WIB CFA
> Mis à jour automatiquement à la fin de chaque session Claude Code.

**Date**: 2026-05-17 (session 22)  
**Commit**: d3426cb — "Rewrite Exam Simulator to comply with CFA Level 1 official standards"  
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
