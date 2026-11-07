# 10 requirements with authored 2-level decompositions (ground truth).
# AUTHORED BY US (the experimenter), labeled as such. Used to score generated
# decompositions: coverage = fraction of authored leaf tasks whose keywords
# appear somewhere in the generated tree (scripted, no LLM judge).
REQUIREMENTS = [
 {"id": "q01", "req": "Build a CLI tool that tracks personal expenses and shows monthly summaries.",
  "chunks": ["expense storage", "CLI commands", "monthly summary report"],
  "leaves": {"expense storage": ["define expense record with amount category date", "save and load expenses as json file"],
             "CLI commands": ["add expense command with validation", "list and delete expense commands"],
             "monthly summary report": ["group expenses by month and category", "print formatted monthly totals"]}},
 {"id": "q02", "req": "Build a URL shortener web service with click counting.",
  "chunks": ["short code generation", "redirect endpoint", "click tracking"],
  "leaves": {"short code generation": ["generate unique short codes", "store code to url mapping"],
             "redirect endpoint": ["http redirect handler", "handle unknown code with 404"],
             "click tracking": ["increment counter per redirect", "endpoint returning click stats"]}},
 {"id": "q03", "req": "Build a markdown to HTML converter supporting headers, bold, italic and links.",
  "chunks": ["line parsing", "inline formatting", "html output"],
  "leaves": {"line parsing": ["detect header lines by hash prefix", "split document into lines and blocks"],
             "inline formatting": ["convert bold and italic markers", "convert markdown links to anchor tags"],
             "html output": ["wrap blocks in html elements", "escape html special characters"]}},
 {"id": "q04", "req": "Build a library booking system where members borrow and return books.",
  "chunks": ["catalog management", "member accounts", "loan workflow"],
  "leaves": {"catalog management": ["add and remove books with copies count", "search books by title or author"],
             "member accounts": ["register member with unique id", "track books currently held by member"],
             "loan workflow": ["borrow book if copies available", "return book and compute overdue days"]}},
 {"id": "q05", "req": "Build a tic-tac-toe game with two-player mode and a simple computer opponent.",
  "chunks": ["game board logic", "two player mode", "computer opponent"],
  "leaves": {"game board logic": ["represent 3x3 board and moves", "detect win or draw"],
             "two player mode": ["alternate turns between players", "validate legal moves"],
             "computer opponent": ["choose winning move if available", "block opponent winning move"]}},
 {"id": "q06", "req": "Build a log file analyzer that counts errors and finds the busiest hour.",
  "chunks": ["log parsing", "error counting", "time analysis"],
  "leaves": {"log parsing": ["parse timestamp and level from each line", "skip malformed lines"],
             "error counting": ["count lines by severity level", "list most frequent error messages"],
             "time analysis": ["bucket entries by hour", "find hour with most entries"]}},
 {"id": "q07", "req": "Build a quiz app that asks multiple choice questions and scores the answers.",
  "chunks": ["question bank", "quiz flow", "scoring"],
  "leaves": {"question bank": ["load questions with options and answer key", "shuffle question order"],
             "quiz flow": ["present question and read answer", "prevent skipping ahead"],
             "scoring": ["compute score percentage", "show per question feedback at end"]}},
 {"id": "q08", "req": "Build a temperature converter library with Celsius, Fahrenheit and Kelvin.",
  "chunks": ["conversion formulas", "api design", "input validation"],
  "leaves": {"conversion formulas": ["implement all six pairwise conversions", "round to two decimals"],
             "api design": ["single convert function with from and to units", "constants for unit names"],
             "input validation": ["reject unknown unit names", "reject temperatures below absolute zero"]}},
 {"id": "q09", "req": "Build a chat server where multiple clients join rooms and exchange messages.",
  "chunks": ["connection handling", "rooms", "message broadcast"],
  "leaves": {"connection handling": ["accept socket connections", "read and write message lines"],
             "rooms": ["join and leave named rooms", "list members of a room"],
             "message broadcast": ["send message to all room members", "prefix messages with sender name"]}},
 {"id": "q10", "req": "Build a password generator with configurable length and character sets.",
  "chunks": ["character sets", "random generation", "cli options"],
  "leaves": {"character sets": ["define lower upper digit symbol sets", "combine sets by user choice"],
             "random generation": ["pick characters with secure random", "guarantee at least one char per chosen set"],
             "cli options": ["parse length and set flags", "print generated password"]}},
]

def score_decomposition(req, generated_text):
    """Scripted coverage: fraction of authored leaves whose distinctive words appear."""
    import re
    def words(s): return set(re.findall(r"[a-z]{4,}", s.lower()))
    gen = words(generated_text)
    hits = total = 0
    for chunk, leaves in req["leaves"].items():
        for leaf in leaves:
            total += 1
            lw = words(leaf)
            key = {w for w in lw if len(w) > 4}
            if key and len(key & gen) >= max(1, len(key) // 2): hits += 1
    return hits / total if total else 0.0
