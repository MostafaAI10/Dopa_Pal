DEFAULT_SYNC_SETTINGS = {
    "calendar": {
        "enabled": True,
        "include_keywords": "deadline, due, submit, assignment, exam, review, finalize, prepare, deliverable, milestone, read, study, write, draft, edit, build, fix, research, plan",
        "exclude_keywords": "standup, sync, lunch, coffee, birthday, holiday, vacation, out of office",
        "min_duration_minutes": 30,
        "include_event_types": "default",  # comma-separated: default, focusTime, outOfOffice, workingLocation
    },
    "tasks": {
        "enabled": True,
        "include_completed": False,
        "include_no_due_date": True,
        "interest_tag": "",  # optional tag assigned to synced tasks
    },
    "gmail": {
        "enabled": False,
        "include_keywords": "",
        "include_senders": "",
    },
}
