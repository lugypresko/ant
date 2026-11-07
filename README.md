# ant - מושבת נמלים שבונה מפעל תוכנה / Ant colony that builds a software factory

## עברית
שורת ניסויים: האם מושבה של סוכנים פשוטים ("נמלים") שמנתבת פועלי LLM קלים מנצחת סוכן מרכזי. הנמלה היא קוד בלבד (מכונת מצבים, פרומונים עם אידוי, ספי תגובה, מלכה שמייצרת קצב); ה-LLM רק כותב קוד בקריאה קצרה אחת.

קבצים מרכזיים:
- `exp4.py` - ניסוי 4: נמלי קוד טהור מנתבות פועלי LLM. משפחת קוד (`coding`) ומשפחת פירוק דרישות (`decomp`).
- `ground_truth.py`, `ground_truth_hard.py` - 10 דרישות קטנות + 5 מערכתיות עם פירוק תשתית שנכתב על ידינו (מסומן ככזה).
- `tasks_hard.py` - 10 משימות קוד קשות. `tasks.py` - 20 קלות + 10 תגמול.
- `nest_blank_llm.py` - ניסוי 3b: קן מסביבה ריקה. `nest_blank_sim.py` - גרסה מסוכרתת.
- `colony_sim.py`, `ant_sim*.py`, `nest_sim.py` - הסימולציות המסוכרתות של ניסויים 2, 2b, 3 (0$, בלי מודל).
- `nest_llm.py` - לקוח Gemini/Groq/Ollama משותף עם רישום קריאות ב-`run/llm_log.jsonl`.

הרצה (ניסוי 4), בחירת ספק ומודל:
```
read -s GEMINI_API_KEY; export GEMINI_API_KEY  # הקלדה מוסתרת; המפתח לא מועבר כארגומנט
python3 exp4.py decomp --provider gemini --model gemini-3.5-flash-lite

read -s GROQ_API_KEY; export GROQ_API_KEY      # הקלדה מוסתרת; המפתח לא מועבר כארגומנט
python3 exp4.py decomp --provider groq --model openai/gpt-oss-20b

# Ollama מקומי אינו דורש מפתח או קריאה לשירות ענן
ollama pull gpt-oss:20b
python3 exp4.py decomp --provider ollama --model gpt-oss:20b
```
זרועות: colony (מושבה אדפטיבית), central (סוכן יחיד), pool (4 פועלים גנריים), cells (4 תאים עם נקודות מבט מתמחות), blueprint (שלד פירוק קבוע). פירוק הדרישות כולל את 10 הדרישות הקטנות ב-`ground_truth.py` ואת 5 הדרישות המערכתיות ב-`ground_truth_hard.py`. ציון הכיסוי מבוסס על עלים שנכתבו מראש; מעבר מלא מוגדר ככיסוי 100%.

למשפחת `decomp` יש עד 975 בקשות מתוכננות (5 זרועות x 15 דרישות x 13), לפני ניסיונות חוזרים; במסלול הפירוק המשתנה `seed` לא מייצר אקראיות, לכן הוסרה החזרה הכפולה. במכסה השמרנית המוגדרת לכל ספק, נדרשים לפחות שני חלונות מכסה מלאים. `run4/` שומר תוצאות והתקדמות; מכסת הבקשות נשמרת בין הפעלות. בסיכום `run4/summary_decomp.json` נשמרים שיעור מעבר מלא, כיסוי ממוצע, בקשות API בפועל וסוגי כשלים.

הספק נבחר פעם אחת לכל הריצה. אין מעבר אוטומטי לספק אחר בעת כשל. מפתחות נקראים רק מ-`GEMINI_API_KEY` או `GROQ_API_KEY`; אין למסור אותם כארגומנט או להוסיף אותם לקבצים. ניתן לבחור גם דרך `ANT_LLM_PROVIDER` ו-`ANT_LLM_MODEL`. כתובת Ollama ניתנת לשינוי באמצעות `OLLAMA_BASE_URL` או `--ollama-base-url`.

מכסה שמרנית: Gemini מוגבל מקומית ל-490 בקשות ביום לפי שעון פסיפי, Groq ל-900 ליום, ו-Ollama המקומי ללא מכסת ענן. המונים נשמרים ב-`run/` בין הרצות. ה-guard המקומי מגביל בקשות בלבד ואינו יכול לזהות אם חשבון הספק שודרג למסלול בתשלום; לשמירה על $0, יש לוודא שהחשבון נשאר במסלול החינמי ולבדוק את המכסה בפועל לפני הרצה. ה-checkpoint והתוצאות כוללים ספק ומודל; ניסיון לחדש checkpoint עם תצורה אחרת נעצר כדי למנוע ערבוב נתונים. כדי להתחיל ניסוי עם מודל אחר, יש להשתמש בתיקיית checkpoint נקייה.

כלל ברזל: אסור שום תשלום. עוצרים בכל דרישת כרטיס, טלפון או אימות זהות. השכבה החינמית של Gemini משתמשת בפרומפטים לאימון; תוכן הניסוי סינתטי בלבד.

## English
Pure-code ant colony (state machine, evaporating pheromones, response thresholds, queen spawn-rate) routing single-call LLM workers, vs central agent, fixed pool, 4 cells, and a blueprint arm. Coding tasks and requirement decomposition use human-authored ground truth (labeled as such). Select one provider per run: `python3 exp4.py decomp --provider gemini|groq|ollama`; set `GEMINI_API_KEY` or `GROQ_API_KEY` in the environment, or run local Ollama without a key. A provider failure never switches providers automatically. Progress checkpoints and result rows record provider/model and reject mismatched resumes. Gemini is locally capped at 490 requests/day (Pacific time), Groq at 900/day, and local Ollama has no cloud cap. Actual free quotas vary by account. The decomposition run covers all 15 authored requirements across 5 arms (up to 975 requests plus retries); use the same provider/model to resume. `python3 exp4.py coding` is a separate family. Scripted zero-cost simulations for experiments 2, 2b, 3, 3b included. No spending allowed; stop at any card, phone or ID check. Gemini's free tier may use prompts to improve products; experiment content is synthetic only.
