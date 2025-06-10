class Calendar:
    def __init__(self):
        self.events = {}

    def create_event(self, event_name, event_date, event_time, event_details):
        event_id = len(self.events) + 1
        event = {
            "id": event_id,
            "name": event_name,
            "date": event_date,
            "time": event_time,
            "details": event_details
        }
        self.events[event_id] = event
        return event_id

    def get_event(self, event_id):
        return self.events.get(event_id)

    def get_all_events(self):
        return list(self.events.values())

    def edit_event(self, event_id, event_name=None, event_date=None, event_time=None, event_details=None):
        if event_id in self.events:
            event = self.events[event_id]
            if event_name:
                event["name"] = event_name
            if event_date:
                event["date"] = event_date
            if event_time:
                event["time"] = event_time
            if event_details:
                event["details"] = event_details
            return True
        return False

    def delete_event(self, event_id):
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
