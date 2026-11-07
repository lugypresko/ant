# 5 system-scale requirements with authored decompositions (10-14 leaves each).
# AUTHORED BY US (the experimenter). Leaves deliberately use specific design
# decisions that cannot be guessed from the requirement sentence alone.
HARD_REQUIREMENTS = [
 {"id": "Q1", "req": "Design a food delivery marketplace connecting restaurants, couriers and customers.",
  "leaves": ["restaurant onboarding with menu import via csv",
             "courier dispatch by nearest idle within polygon zones",
             "order state machine placed accepted picked delivered",
             "idempotent payment capture with webhook reconciliation",
             "delivery eta from historical courier speed per zone",
             "customer cart with concurrent item lock to prevent oversell",
             "restaurant tablet order acknowledgment with timeout auto cancel",
             "courier proof of delivery via photo upload",
             "commission ledger with weekly payout batch",
             "fraud check on repeated canceled orders per device"]},
 {"id": "Q2", "req": "Design a multi-tenant SaaS for managing gym memberships and class bookings.",
  "leaves": ["tenant isolation by schema per gym with shared auth",
             "membership plan with freeze and resume date ranges",
             "class capacity booking with waitlist promotion on cancel",
             "qr code check-in rotating token every thirty seconds",
             "instructor payroll from attended class hours",
             "recurring billing with proration on plan change",
             "no-show penalty strike counter with suspension threshold",
             "member referral credit applied to next invoice",
             "audit log of every membership status transition",
             "per-tenant branding with custom subdomain routing"]},
 {"id": "Q3", "req": "Design a collaborative document editor with real-time multi-user editing.",
  "leaves": ["operational transformation for concurrent text edits",
             "websocket session with heartbeat and reconnect backlog replay",
             "document snapshot every hundred operations for fast load",
             "presence cursor broadcast throttled to fifty milliseconds",
             "permission tiers viewer commenter editor owner",
             "offline edit queue with conflict merge on reconnect",
             "version history with named restore points",
             "comment threads anchored to text ranges that survive edits",
             "rate limit operations per user to prevent abuse",
             "export to docx and pdf via async job queue"]},
 {"id": "Q4", "req": "Design a smart-home platform ingesting sensor data and running automation rules.",
  "leaves": ["mqtt ingestion gateway with device certificate auth",
             "time series storage with downsampled hourly rollups",
             "rule engine with trigger condition action evaluation loop",
             "device shadow state for offline command buffering",
             "automation conflict detection when rules oppose",
             "firmware over the air update with rollback partition",
             "alert escalation chain sms then call after fifteen minutes",
             "energy dashboard aggregating per circuit consumption",
             "geofence arming when all household phones leave",
             "device pairing flow with qr claim code"]},
 {"id": "Q5", "req": "Design an online exam platform with proctoring and automatic grading.",
  "leaves": ["question bank with difficulty tags and exposure limits",
             "exam session timer with server side authoritative clock",
             "proctoring flags from webcam face absence detection",
             "browser lockdown detecting tab switch and paste events",
             "auto grading of code answers against hidden test suites",
             "rubric based manual grading queue for essay answers",
             "cheating similarity report across candidate submissions",
             "accommodation profile extending time for approved students",
             "grade appeal workflow with second grader assignment",
             "psychometric item analysis for question quality"]},
]

from ground_truth import REQUIREMENTS
import re
def score_hard(req, generated_text):
    def words(s): return set(re.findall(r"[a-z]{4,}", s.lower()))
    gen = words(generated_text)
    hits = 0
    for leaf in req["leaves"]:
        key = {w for w in words(leaf) if len(w) > 4}
        if key and len(key & gen) >= max(2, len(key) // 2): hits += 1
    return hits / len(req["leaves"])
