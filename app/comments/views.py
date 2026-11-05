from app.views import ModelViewSet

from .filters import CommentFilter
from .models import Comment
from .schemas import CommentCreate, CommentResponse, CommentUpdate
from .services import CommentService


class CommentViewSet(ModelViewSet):
    schema = CommentResponse
    create_schema = CommentCreate
    update_schema = CommentUpdate
    filter_class = CommentFilter
    service = CommentService
    model = Comment
    tags = ["comments-crud"]
    owner_field = "author_id"
    owner_actions = ("update", "delete")

    permissions = {
        "list": [],
        "retrieve": [],
        "create": ["AUTHENTICATED"],
        "update": ["AUTHENTICATED"],
        "delete": ["AUTHENTICATED", "ADMIN"],
    }
