from pathlib import Path

from src.main import build_arg_parser, load_images


def test_load_images_reads_bytes_for_existing_files(tmp_path):
    (tmp_path / "p1_ja.jpg").write_bytes(b"ja-bytes")
    (tmp_path / "p1_en.jpg").write_bytes(b"en-bytes")

    images = load_images(tmp_path, ["p1"])

    assert images[("p1", "ja")] == b"ja-bytes"
    assert images[("p1", "en")] == b"en-bytes"


def test_load_images_skips_missing_files(tmp_path):
    (tmp_path / "p1_ja.jpg").write_bytes(b"ja-bytes")

    images = load_images(tmp_path, ["p1"])

    assert ("p1", "ja") in images
    assert ("p1", "en") not in images


def test_build_arg_parser_parses_expected_flags():
    parser = build_arg_parser()
    args = parser.parse_args(
        ["--images-dir", "/tmp/imgs", "--boards", "board_ja:board_en"]
    )
    assert args.images_dir == "/tmp/imgs"
    assert args.boards == "board_ja:board_en"
    assert args.count == 3
