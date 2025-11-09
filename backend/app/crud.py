from sqlmodel import Session

from app.models import Item, ItemCreate


def create_item(*, session: Session, item_in: ItemCreate) -> Item:
    db_item = Item.model_validate(item_in)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
