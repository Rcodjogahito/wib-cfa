# ETAT ACTUEL — WIB CFA
> Mis à jour automatiquement à la fin de chaque session Claude Code.

**Date**: 2026-05-17 (session 20)  
**Commit**: c7d6218 — "UI/UX improvements and explanation audit corrections"  
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
