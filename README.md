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
python3 exp4.py decomp      # 5 זרועות x חזרה אחת x 15 דרישות, עד 13 קריאות לריצה
```
זרועות: colony (מושבה אדפטיבית), central (סוכן יחיד), pool (4 פועלים גנריים), cells (4 תאים עם נקודות מבט מתמחות), blueprint (שלד פירוק קבוע). פירוק הדרישות כולל את 10 הדרישות הקטנות ב-`ground_truth.py` ואת 5 הדרישות המערכתיות ב-`ground_truth_hard.py`. ציון הכיסוי מבוסס על עלים שנכתבו מראש; מעבר מלא מוגדר ככיסוי 100%.

למשפחת `decomp` יש עד 975 בקשות מתוכננות (5 זרועות x 15 דרישות x 13), לפני ניסיונות חוזרים; במסלול הפירוק המשתנה `seed` לא מייצר אקראיות, לכן הוסרה החזרה הכפולה. בהנחת מכסה של 500 בקשות ליום, התכנון מתאים לשני חלונות מכסה. `run4/` שומר תוצאות והתקדמות; מכסת הבקשות נשמרת גם ב-`run/gemini_daily_usage.json`, כדי שהפעלה מחדש באותו יום לא תשתמש במכסה יומית נוספת. בסיכום `run4/summary_decomp.json` נשמרים שיעור מעבר מלא, כיסוי ממוצע, בקשות API בפועל וסוגי כשלים.

מגבלות חינם: הגדרות Gemini תלויות במודל, בפרויקט ובחשבון; יש לבדוק את המכסה הפעילה ב-AI Studio לפני הרצה. סקריפט Gemini מגביל את עצמו ל-490 בקשות שמורות ביום, ושומר זאת בין הפעלות. ניתוב משני ל-Cloudflare Workers AI אופציונלי דרך `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`; יש להסיר משתנים אלה כדי לכפות שימוש ב-Gemini בלבד.

כלל ברזל: אסור שום תשלום. עוצרים בכל דרישת כרטיס, טלפון או אימות זהות. השכבה החינמית של Gemini משתמשת בפרומפטים לאימון; תוכן הניסוי סינתטי בלבד.

## English
Pure-code ant colony (state machine, evaporating pheromones, response thresholds, queen spawn-rate) routing single-call LLM workers, vs central agent, fixed pool, 4 cells, and a blueprint arm. Coding tasks and requirement decomposition use human-authored ground truth (labeled as such). Run `python3 exp4.py decomp` for all 15 authored requirements, 5 arms, and a single run per requirement (up to 975 requests plus retries); at a 500-RPD limit this is about two daily quota windows. The decomposition path does not use its seed for randomness, so it runs once per requirement. `python3 exp4.py coding` is a separate family. Progress is checkpointed in `run4/`; Gemini requests are reserved to a 490-request daily cap across restarts using Pacific time. Gemini quotas vary by project, model, and account; check AI Studio before running. Scripted zero-cost simulations for experiments 2, 2b, 3, 3b included. No spending allowed; stop at any card, phone or ID check. Gemini's free tier may use prompts to improve products; experiment content is synthetic only.
