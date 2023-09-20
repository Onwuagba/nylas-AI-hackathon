import os


EMAIL_LABELS = set(os.environ.get("EMAIL_LABELS").split(","))
ANNOTATION = (
    ('task','task'),
    ('meeting_request','meeting request'),
    ('follow-up', 'follow-up'),
    ('question', 'question'),
    ('deadline', 'deadline'),
    ('approval', 'approval'),
    ('feedback', 'feedback'),
    ('review', 'review'),
)