from drawbot_skia.runner import makeDrawbotNamespace, runScript, runScriptSource
from drawbot_skia.drawing import Drawing
import pathlib
import pytest
from PIL import Image
import numpy as np


testDir = pathlib.Path(__file__).resolve().parent
apiTestsDir = testDir / "apitests"
apiTestsOutputDir = testDir / "apitests_output"
apiTestsExpectedOutputDir = testDir / "apitests_expected_output"


apiScripts = apiTestsDir.glob("*.py")


@pytest.mark.parametrize("apiTestPath", apiScripts)
def test_apitest(apiTestPath):
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScript(apiTestPath, namespace)
    if not apiTestsOutputDir.exists():
        apiTestsOutputDir.mkdir()
    outputPath = apiTestsOutputDir / (apiTestPath.stem + ".png")
    expectedOutputPath = apiTestsExpectedOutputDir / (apiTestPath.stem + ".png")
    db.saveImage(outputPath)
    same, reason = compareImages(outputPath, expectedOutputPath)
    assert same, reason


multipageSource = """
for i in range(3):
    newPage(200, 200)
    rect(50, 50, 100, 100)
"""


test_data_saveImage = [
    ("png", ['test_0.png', 'test_1.png', 'test_2.png']),
    ("jpg", ['test_0.jpg', 'test_1.jpg', 'test_2.jpg']),
    ("svg", ['test_0.svg', 'test_1.svg', 'test_2.svg']),
    ("pdf", ['test.pdf']),
    ("mp4", ['test.mp4']),
]


@pytest.mark.parametrize("image_type, expected_filenames", test_data_saveImage)
def test_saveImage_multipage(tmpdir, image_type, expected_filenames):
    glob_pattern = f"*.{image_type}"
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(multipageSource, "<string>", namespace)
    assert [] == sorted(tmpdir.glob(glob_pattern))
    outputPath = tmpdir / f"test.{image_type}"
    db.saveImage(outputPath)
    assert expected_filenames == [p.name for p in sorted(tmpdir.glob(glob_pattern))]


def test_saveImage_mp4_codec(tmpdir):
    from drawbot_skia import ffmpeg
    ffmpeg.FFMPEG_PATH = ffmpeg.getPyFFmpegPath()  # Force ffmpeg from pyffmpeg
    tmpdir = pathlib.Path(tmpdir)
    db = Drawing()
    namespace = makeDrawbotNamespace(db)
    runScriptSource(multipageSource, "<string>", namespace)
    assert [] == sorted(tmpdir.glob("*.png"))
    db.saveImage(tmpdir / "test.mp4")
    db.saveImage(tmpdir / "test2.mp4", codec="mpeg4")
    expected_filenames = ['test.mp4', 'test2.mp4']
    paths = sorted(tmpdir.glob("*.mp4"))
    assert paths[0].stat().st_size < paths[1].stat().st_size
    assert expected_filenames == [p.name for p in paths]


def test_noFont(tmpdir):
    db = Drawing()
    # Ensure we don't get an error when font is not set
    db.text("Hallo", (0, 0))


def test_newPage_newGState():
    # Test a bug with the delegate properties of Drawing: they should
    # not return the delegate method itself, but a wrapper that calls the
    # delegate method, as the delegate object does not have a fixed
    # identity
    db = Drawing()
    fill = db.fill  # Emulate a db namespace: all methods are retrieved once
    db.newPage(50, 50)
    with db.savedState():
        fill(0.5)
        assert (255, 128, 128, 128) == db._gstate.fillPaint.color
    db.newPage(50, 50)
    fill(1)
    assert (255, 255, 255, 255) == db._gstate.fillPaint.color


def test_polygon_args():
    db = Drawing()
    db.polygon([0, 0], [0, 100], [100, 0])


def test_line_args():
    db = Drawing()
    db.line([0, 0], [0, 100])


def readbytes(path):
    with open(path, "rb") as f:
        return f.read()


def compareImages(path1, path2):
    data1 = readbytes(path1)
    data2 = readbytes(path2)
    if data1 == data2:
        return True, "data identical"
    im1 = Image.open(path1)
    im2 = Image.open(path2)
    if im1 == im2:
        return True, "images identical"
    if im1.size != im2.size:
        return False, "sizes differ"
    a1 = np.array(im1).astype(int)
    a2 = np.array(im2).astype(int)
    diff = a1 - a2
    maxDiff = max(abs(np.max(diff)), abs(np.min(diff)))
    if maxDiff < 128:
        return True, "images similar enough"
    return False, f"images differ too much, maxDiff: {maxDiff}"
