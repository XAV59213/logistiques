def detect_conflicts(existing_events, new_event):
    conflicts = []
    for event in existing_events:
        if event.get("date") == new_event.get("date"):
            conflicts.append(event)
    return conflicts
