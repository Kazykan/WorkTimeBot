import pytest
from datetime import datetime

from app.repositories.time_repo import TimeEntryRepository

@pytest.mark.asyncio
async def test_create_and_get_entry(test_session):
    repo = TimeEntryRepository(test_session)

    # создаём запись
    entry = await repo.create_entry(
        work_object_id=1,
        start_time=datetime(2025, 1, 1, 9, 0),
        end_time=datetime(2025, 1, 1, 17, 30),
        hours=8,
        date=datetime(2025, 1, 1),
        comment="Test entry"
    )

    await test_session.commit()

    # проверяем, что запись сохранилась
    fetched = await repo.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.comment == "Test entry"
    assert fetched.hours == 8
