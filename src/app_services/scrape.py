import logging
from datetime import datetime, timedelta


from src import db
from src.datastore.models import Review, Progress, ProgressStatus

logger = logging.getLogger(__name__)


def make_task(url, request_id):
    progress = Progress(request_id=request_id, url=url)

    review: Review = Review.query.filter_by(url=url).first()
    if review is not None:
        cond2 = datetime.now() - review.updated_at < timedelta(minutes=30)
        cond3 = "Error" not in [review.location, review.reviewer, review.content]
        if cond2 and cond3:
            progress.status = ProgressStatus.NOTIFYING

    db.session.add(progress)
    db.session.commit()

    if progress.status != ProgressStatus.NOTIFYING:
        return True

    return False



