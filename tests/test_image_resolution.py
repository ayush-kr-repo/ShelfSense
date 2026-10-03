"""Which photo gets analysed, and whether the caller is told it's a stand-in.

The old `image_for()` silently returned the demo photo when a warehouse had no
upload. That wasn't only a heatmap problem: phase 1 ran on it, so the user got
a health score, SUR and recommendations computed from a photograph of someone
else's warehouse, presented as their own. The fallback stays - a fresh account
shouldn't look broken - but it has to announce itself.
"""

import pytest
from fastapi import HTTPException

from app.api import warehouse as api


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    """Point the upload directory at a temp folder for the duration of a test."""
    monkeypatch.setattr(api, "UPLOAD_DIR", tmp_path)
    return tmp_path


# --------------------------------------------------------------- uploaded_image

def test_no_upload_returns_none(uploads):
    assert api.uploaded_image("wh_new") is None


def test_existing_upload_is_returned(uploads):
    (uploads / "wh_real.jpg").write_bytes(b"not really a jpeg")
    assert api.uploaded_image("wh_real") == uploads / "wh_real.jpg"


def test_one_warehouse_photo_is_not_served_for_another(uploads):
    (uploads / "wh_a.jpg").write_bytes(b"x")
    assert api.uploaded_image("wh_b") is None


# --------------------------------------------------------------- analysis_image

def test_missing_photo_falls_back_to_demo_and_says_so(uploads):
    path, is_demo = api.analysis_image("wh_new")
    assert path == api.DEMO_IMAGE
    assert is_demo is True


def test_real_photo_is_not_flagged_as_demo(uploads):
    (uploads / "wh_real.jpg").write_bytes(b"x")
    path, is_demo = api.analysis_image("wh_real")
    assert path == str(uploads / "wh_real.jpg")
    assert is_demo is False


def test_demo_flag_tracks_the_upload_appearing(uploads):
    """Upload a photo and the same warehouse stops being a demo."""
    assert api.analysis_image("wh_x")[1] is True
    (uploads / "wh_x.jpg").write_bytes(b"x")
    assert api.analysis_image("wh_x")[1] is False


# --------------------------------------------------------------- safe_id

@pytest.mark.parametrize("bad", [
    "../../etc/passwd",      # climb out of uploads/
    "wh/../../secret",
    "wh id",                 # space
    "wh.jpg",                # dot
    "",
])
def test_path_traversal_and_odd_ids_are_rejected(bad):
    with pytest.raises(HTTPException) as exc:
        api.safe_id(bad)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("ok", ["wh_demo", "wh-1", "WH123", "a"])
def test_ordinary_ids_are_accepted(ok):
    assert api.safe_id(ok) == ok


# --------------------------------------------------------------- normalise_to_jpeg

def _png(path, size=(32, 32)):
    from PIL import Image
    Image.new("RGB", size, (120, 80, 40)).save(path, "PNG")
    return path


def test_a_png_saved_as_jpg_is_rewritten_as_a_real_jpeg(tmp_path):
    """The reported bug: an AVIF arrived as .jpg, OpenCV could not decode it,
    YOLO returned zero results and phase 1 died on results[0]."""
    dest = tmp_path / "wh.jpg"
    _png(dest)
    assert dest.read_bytes()[:4] == b"\x89PNG"      # lying extension

    api.normalise_to_jpeg(dest)

    assert dest.read_bytes()[:3] == b"\xff\xd8\xff"  # now actually a JPEG


def test_normalising_a_real_jpeg_leaves_it_readable(tmp_path):
    from PIL import Image
    dest = tmp_path / "wh.jpg"
    Image.new("RGB", (32, 32), (10, 20, 30)).save(dest, "JPEG")
    api.normalise_to_jpeg(dest)
    with Image.open(dest) as im:
        assert im.format == "JPEG"


def test_transparency_is_flattened_not_rejected(tmp_path):
    """RGBA has no JPEG representation; convert rather than fail the upload."""
    from PIL import Image
    dest = tmp_path / "wh.jpg"
    Image.new("RGBA", (16, 16), (255, 0, 0, 128)).save(dest, "PNG")
    api.normalise_to_jpeg(dest)
    with Image.open(dest) as im:
        assert im.mode == "RGB"


def test_a_file_that_is_not_an_image_is_rejected_with_400(tmp_path):
    dest = tmp_path / "wh.jpg"
    dest.write_bytes(b"this is not an image at all")
    with pytest.raises(HTTPException) as exc:
        api.normalise_to_jpeg(dest)
    assert exc.value.status_code == 400


def test_a_rejected_upload_is_not_left_on_disk(tmp_path):
    """A half-written file would be analysed on the next request."""
    dest = tmp_path / "wh.jpg"
    dest.write_bytes(b"garbage")
    with pytest.raises(HTTPException):
        api.normalise_to_jpeg(dest)
    assert not dest.exists()
