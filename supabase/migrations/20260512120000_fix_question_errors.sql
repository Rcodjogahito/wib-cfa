-- WIB CFA — Fix errors in seeded questions
-- Apply to production Supabase via: supabase db push
-- Or paste directly into Supabase Dashboard > SQL Editor

-- Fix 1: Annuity PV — option_b was $11,872, correct value is $11,943
UPDATE questions
SET
    option_b       = '$11,943',
    explanation_en = 'PV = PMT × [1 - (1+r)^-n] / r = 2,000 × [1 - (1.07)^-8] / 0.07 = 2,000 × 5.9713 = $11,943.'
WHERE question_en ILIKE '%annuity that pays $2,000 per year for 8 years%';

-- Fix 2: Put-call parity — option_a was identical to option_b (same equation, different order)
UPDATE questions
SET
    option_a       = 'Call + Stock Price = Put + PV(Strike).',
    explanation_en = 'Put-call parity: P + S = C + PV(X). Option A is incorrect — it inverts the positions of S and PV(X), which are not interchangeable. Option C omits discounting the strike.'
WHERE question_en ILIKE '%Put-call parity states that for European options on a non-dividend-paying stock%';

-- Fix 3: Capitalise BEST in straddle question (consistency with rest of question bank)
UPDATE questions
SET question_en = 'An investor is short a call option and short a put option on the same stock with the same strike and expiry. This is BEST described as a:'
WHERE question_en ILIKE '%short a call option and short a put option on the same stock with the same strike and expiry%'
  AND question_en NOT LIKE '%BEST%';

-- Fix 4: Capitalise BEST in IRR/private equity question
UPDATE questions
SET question_en = 'The internal rate of return (IRR) of a private equity fund is BEST described as:'
WHERE question_en ILIKE '%internal rate of return (IRR) of a private equity fund is best described%';
