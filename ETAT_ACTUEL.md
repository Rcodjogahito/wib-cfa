# ETAT ACTUEL — WIB CFA
> Mis à jour automatiquement à la fin de chaque session Claude Code.

**Date**: 2026-05-16 (session 15)  
**Commit**: bfa83f7 — "UX: translate sidebar navigation to French across all pages"  
**Branch**: master → Streamlit Cloud (auto-deploy)

---

## Statut banque questions

| Métrique | Valeur |
|---|---|
| Total questions | 7,249 |
| Complètes (table + explication) | 7,245 |
| Tables manquantes | 4 (faux positifs Kaplan — aucune action) |
| Explications manquantes | 0 |

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

## Travaux terminés (session 15)

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
