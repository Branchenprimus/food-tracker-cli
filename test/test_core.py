from datetime import date, time
from core.service import FoodService

def test_add_entry(db_service: FoodService):
    entry = db_service.add_entry(
        title="Test Apple",
        kcal=95.0,
        fat=0.3,
        carbs=25.0,
        protein=0.5,
        serving=1.0,
        entry_date=date(2023, 1, 1),
        entry_time=time(10, 30)
    )
    
    assert entry.id is not None
    assert entry.title == "Test Apple"
    assert entry.kcal == 95.0
    assert entry.entry_date == date(2023, 1, 1)

def test_list_entries(db_service: FoodService):
    db_service.add_entry("Banana", 105, 0.4, 27, 1.3)
    db_service.add_entry("Orange", 62, 0.2, 15, 1.2)
    
    entries = db_service.list_entries()
    assert len(entries) >= 2
    
def test_delete_entry(db_service: FoodService):
    entry = db_service.add_entry("ToDelete", 10, 0, 2, 0)
    
    assert db_service.repo.get(entry.id) is not None
    
    deleted = db_service.delete_entry(entry.id)
    assert deleted is True
    
    assert db_service.repo.get(entry.id) is None
