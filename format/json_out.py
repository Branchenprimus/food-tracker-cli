import json
from typing import List, Optional, Any
from core.models import Entry, DailyStats

def dump_json(data: Any):
    """Dump data to stdout as JSON."""
    if isinstance(data, list): # List of entries
         print(json.dumps({"entries": [e.model_dump(mode='json') for e in data], "follow_up": None}, indent=2))
    elif isinstance(data, DailyStats):
         print(json.dumps({"stats": data.model_dump(mode='json'), "follow_up": None}, indent=2))
    elif isinstance(data, Entry):
          print(json.dumps({"entry": data.model_dump(mode='json'), "follow_up": None}, indent=2))
    else:
        print(json.dumps(data, default=str, indent=2))
