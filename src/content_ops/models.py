"""Shared workflow models for content operations."""

from enum import Enum


class PostStatus(str, Enum):
    IDEA = "idea"
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    FAILED = "failed"


ALLOWED_POST_TRANSITIONS: dict[PostStatus, frozenset[PostStatus]] = {
    PostStatus.IDEA: frozenset({PostStatus.DRAFT, PostStatus.ARCHIVED}),
    PostStatus.DRAFT: frozenset({PostStatus.IN_REVIEW, PostStatus.ARCHIVED}),
    PostStatus.IN_REVIEW: frozenset(
        {PostStatus.APPROVED, PostStatus.REJECTED, PostStatus.DRAFT}
    ),
    PostStatus.APPROVED: frozenset({PostStatus.SCHEDULED, PostStatus.DRAFT}),
    PostStatus.SCHEDULED: frozenset({PostStatus.PUBLISHED, PostStatus.FAILED}),
    PostStatus.FAILED: frozenset({PostStatus.APPROVED, PostStatus.ARCHIVED}),
}
