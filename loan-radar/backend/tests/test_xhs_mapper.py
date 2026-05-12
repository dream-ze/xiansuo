from app.collectors.xhs_mapper import normalize_comment, normalize_post


def test_normalize_post_maps_spider_xhs_like_fields():
    raw_note = {
        "id": "note-123",
        "xsec_token": "token-123",
        "note_card": {
            "title": "征信花了怎么办",
            "desc": "查询多还能做吗",
            "time": 1715600000000,
            "user": {
                "user_id": "user-123",
                "nickname": "贷款顾问",
            },
            "interact_info": {
                "liked_count": "88",
                "comment_count": "22",
                "collected_count": "15",
            },
        },
    }

    post = normalize_post(raw_note)

    assert post.platform == "xhs"
    assert post.post_id == "note-123"
    assert post.title == "征信花了怎么办"
    assert post.content == "查询多还能做吗"
    assert post.author_name == "贷款顾问"
    assert post.author_profile_url == "https://www.xiaohongshu.com/user/profile/user-123"
    assert post.like_count == 88
    assert post.comment_count == 22
    assert post.collect_count == 15
    assert post.is_hot is True
    assert "xsec_token=token-123" in (post.post_url or "")


def test_normalize_comment_maps_spider_xhs_like_fields():
    raw_comment = {
        "id": "comment-123",
        "note_id": "note-123",
        "content": "负债高还能申请吗",
        "liked_count": 5,
        "create_time": 1715600000,
        "user_info": {
            "user_id": "user-c-1",
            "nickname": "咨询用户",
        },
    }

    comment = normalize_comment(raw_comment)

    assert comment.platform == "xhs"
    assert comment.post_id == "note-123"
    assert comment.comment_id == "comment-123"
    assert comment.user_name == "咨询用户"
    assert comment.user_profile_url == "https://www.xiaohongshu.com/user/profile/user-c-1"
    assert comment.content == "负债高还能申请吗"
    assert comment.like_count == 5
    assert comment.publish_time is not None