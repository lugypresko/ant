# ant - מושבת נמלים שבונה מפעל תוכנה / Ant colony that builds a software factory

## עברית
שורת ניסויים: האם מושבה של סוכנים פשוטים ("נמלים") שמנתבת פועלי LLM קלים מנצחת סוכן מרכזי. הנמלה היא קוד בלבד (מכונת מצבים, פרומונים עם אידוי, ספי תגובה, מלכה שמייצרת קצב); ה-LLM רק כותב קוד בקריאה קצרה אחת.

קבצים מרכזיים:
- `exp4.py` - ניסוי 4: נמלי קוד טהור מנתבות פועלי LLM. משפחת קוד (`coding`) ומשפחת פירוק דרישות (`decomp`).
- `ground_truth.py`, `ground_truth_hard.py` - 10 דרישות קטנות + 5 מערכתיות עם פירוק תשתית שנכתב על ידינו (מסומן ככזה).
- `tasks_hard.py` - 10 משימות קוד קשות. `tasks.py` - 20 קלות + 10 תגמול.
- `nest_blank_llm.py` - ניסוי 3b: קן מסביבה ריקה. `nest_blank_sim.py` - גרסה מסוכרתת.
- `colony_sim.py`, `ant_sim*.py`, `nest_sim.py` - הסימולציות המסוכרתות של ניסויים 2, 2b, 3 (0$, בלי מודל).
- `nest_llm.py` - לקוח Gemini משותף עם רישום קריאות ב-`run/llm_log.jsonl`.

הרצה (ניסוי 4):
```
export GEMINI_API_KEY=...   # מפתח Gemini API, חובה
python3 exp4.py coding      # 5 זרועות x 5 זרעים x 10 משימות, תקציב 25 קריאות לריצה
python3 exp4.py decomp      # 4 זרועות x 2 זרעים x 5 דרישות, תקציב 13 קריאות לריצה
```
זרועות: colony (מושבה אדפטיבית), central (סוכן יחיד), pool (4 פועלים גנריים), cells (4 תאים מתמחים), blueprint (שלד דטרמיניסטי בסגנון Minions). התקדמות נשמרת ב-`run4/`; הפעלה חוזרת ממשיכה בלי כפילות.

מגבלות חינם: Gemini 3.5 Flash Lite: 15 בקשות/דקה, 500 בקשות/יום. הריצה המלאה כ-900 קריאות, כלומר כיומיים. ניתוב משני אופציונלי ל-Cloudflare Workers AI דרך `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`.

כלל ברזל: אסור שום תשלום. עוצרים בכל דרישת כרטיס, טלפון או אימות זהות. השכבה החינמית של Gemini משתמשת בפרומפטים לאימון; תוכן הניסוי סינתטי בלבד.

## English
Pure-code ant colony (state machine, evaporating pheromones, response thresholds, queen spawn-rate) routing single-call LLM workers, vs central agent, fixed pool, 4 cells, and a deterministic blueprint arm. Coding tasks and requirement decomposition with human-authored ground truth (labeled as such). Requires `GEMINI_API_KEY` env var (free tier: 15 RPM, 500 RPD; full run ~900 calls, about two days). Run `python3 exp4.py coding` then `python3 exp4.py decomp`; progress checkpoints in `run4/`. Scripted zero-cost simulations for experiments 2, 2b, 3, 3b included. No spending allowed; stop at any card, phone or ID check. Gemini's free tier trains on prompts; experiment content is synthetic only.
