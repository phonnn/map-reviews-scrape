import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.inspection import inspect

from src.datastore.models import Request, Progress, Review

logger = logging.getLogger(__name__)


def bulk_insert_or_update(db: SQLAlchemy, values):
    stmt = insert(Review).values(values)
    try:
        stmt = stmt.on_conflict_do_update(
            index_elements=[Review.url],
            set_=dict(
                updated_at=datetime.now(),
                location=stmt.excluded.location,
                reviewer=stmt.excluded.reviewer,
                content=stmt.excluded.content
            )
        )

        db.session.execute(stmt)
        db.session.commit()
    except Exception as e:
        logger.debug(e)


def model_to_list(model_obj, *args):
    if not model_obj:
        return None

    mapper = inspect(type(model_obj))

    if args:
        fields_to_select = args
    else:
        fields_to_select = [column.key for column in mapper.columns]

    values_list = []

    for field in fields_to_select:
        if hasattr(model_obj, field):
            attr_value = getattr(model_obj, field)
            if isinstance(attr_value, datetime):
                attr_value = attr_value.isoformat()
            values_list.append(attr_value)
        else:
            raise AttributeError(f"Field '{field}' not found in model.")

    return values_list


