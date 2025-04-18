import pytest

from lhotse import MonoCut, MultiCut, Recording, SupervisionSegment


@pytest.fixture
def mono_cut():
    """
    Scenario::

        |-----------------Recording-----------------|
           "Hey, Matt!"  "Yes?"
        |--------------| |-----|  "Oh, nothing"
                             |------------------|
        |-------------------Cut1--------------------|
    """
    rec = Recording(
        id="rec1", duration=10.0, sampling_rate=8000, num_samples=80000, sources=[]
    )
    sups = [
        SupervisionSegment(
            id="sup1", recording_id="rec1", start=0.0, duration=3.37, text="Hey, Matt!"
        ),
        SupervisionSegment(
            id="sup2", recording_id="rec1", start=4.5, duration=0.9, text="Yes?"
        ),
        SupervisionSegment(
            id="sup3", recording_id="rec1", start=4.9, duration=4.3, text="Oh, nothing"
        ),
    ]
    return MonoCut(
        id="rec1-cut1",
        start=0.0,
        duration=10.0,
        channel=0,
        recording=rec,
        supervisions=sups,
    )


@pytest.fixture
def multi_cut():
    """
    Scenario::
                  ╔══════════════════════════════  MultiCut  ═════════════════╗
                  ║ ┌──────────────────────────┐                              ║
     Channel 1  ──╬─│   Hello this is John.    │──────────────────────────────╬────────
                  ║ └──────────────────────────┘                              ║
                  ║                       ┌──────────────────────────────────┐║
     Channel 2  ──╬───────────────────────│     Hey, John. How are you?      │╠────────
                  ║                       └──────────────────────────────────┘║
                  ╚═══════════════════════════════════════════════════════════╝
    """
    rec = Recording(
        id="rec1",
        duration=10.0,
        sampling_rate=8000,
        num_samples=80000,
        sources=[],
        channel_ids=[0, 1],
    )
    sups = [
        SupervisionSegment(
            id="sup1",
            recording_id="rec1",
            start=0.0,
            duration=5.0,
            text="Hello this is John.",
            channel=0,
        ),
        SupervisionSegment(
            id="sup2",
            recording_id="rec1",
            start=4.5,
            duration=5.5,
            text="Hey, John. How are you?",
            channel=1,
        ),
    ]
    return MultiCut(
        id="rec1-cut1",
        start=0.0,
        duration=10.0,
        channel=[0, 1],
        recording=rec,
        supervisions=sups,
    )


@pytest.fixture
def multi_cut_with_multi_channel_supervisions():
    """
    This is the same as multi_cut, but the supervisions are shared between both channels.
    """
    rec = Recording(
        id="rec1",
        duration=10.0,
        sampling_rate=8000,
        num_samples=80000,
        sources=[],
        channel_ids=[0, 1],
    )
    sups = [
        SupervisionSegment(
            id="sup1",
            recording_id="rec1",
            start=0.0,
            duration=5.0,
            text="Hello this is John.",
            channel=[0, 1],
        ),
        SupervisionSegment(
            id="sup2",
            recording_id="rec1",
            start=4.5,
            duration=5.5,
            text="Hey, John. How are you?",
            channel=[0, 1],
        ),
    ]
    return MultiCut(
        id="rec1-cut1",
        start=0.0,
        duration=10.0,
        channel=[0, 1],
        recording=rec,
        supervisions=sups,
    )


def test_cut_trim_to_supervisions_no_keep_overlapping(mono_cut):
    """
    Scenario::

        |-----------------Recording-----------------|
           "Hey, Matt!"  "Yes?"
        |--------------| |-----|  "Oh, nothing"
                             |------------------|
        |---Cut1-------|     |-------Cut3-------|
        |---Sup1-------|     |-------Sup3-------|
                         |Cut2-|
                         |Sup2-|
    """
    cuts = mono_cut.trim_to_supervisions(keep_overlapping=False)
    assert len(cuts) == 3
    for cut, original_sup in zip(cuts, mono_cut.supervisions):
        assert cut.start == original_sup.start
        assert cut.duration == original_sup.duration
        assert len(cut.supervisions) == 1
        (sup,) = cut.supervisions
        assert sup.start == 0
        assert sup.duration == cut.duration
        assert sup.text == original_sup.text


def test_cut_trim_to_supervisions_keep_overlaping(mono_cut):
    """
    Scenario::

        |-----------------Recording-----------------|
           "Hey, Matt!"  "Yes?"
        |--------------| |-----|  "Oh, nothing"
                             |------------------|
        |---Cut1-------|     |-------Cut3-------|
        |---Sup1-------|     |-------Sup3-------|
                             Sup2
                             |-|
                         |Cut2-|
                         |Sup2-|
                             Sup3
                             |-|
    """
    cuts = mono_cut.trim_to_supervisions(keep_overlapping=True)
    assert len(cuts) == 3
    for cut, original_sup in zip(cuts, mono_cut.supervisions):
        assert cut.start == original_sup.start
        assert cut.duration == original_sup.duration
    cut1, cut2, cut3 = cuts
    assert len(cut1.supervisions) == 1
    assert len(cut2.supervisions) == 2
    c2_s1, c2_s2 = cut2.supervisions
    assert c2_s1.start == 0
    assert c2_s1.duration == 0.9
    assert c2_s2.start == 0.4
    assert c2_s2.duration == 4.3
    assert len(cut3.supervisions) == 2
    c3_s1, c3_s2 = cut3.supervisions
    assert c3_s1.start == -0.4
    assert c3_s1.duration == 0.9
    assert c3_s2.start == 0
    assert c3_s2.duration == 4.3


def test_cut_trim_to_supervisions_no_keep_overlapping_extend(mono_cut):
    """
    Scenario::

        |-----------------Recording-----------------|
           "Hey, Matt!"  "Yes?"
        |--------------| |-----|  "Oh, nothing"
                             |------------------|
        |---Cut1---------|   |------Cut3--------|
        |---Sup1-------|     |------Sup3--------|
                  |-------Cut2------|
                         |Sup2-|
    """
    cuts = mono_cut.trim_to_supervisions(
        keep_overlapping=False, min_duration=4.0, context_direction="center"
    )
    assert len(cuts) == 3
    c1, c2, c3 = cuts

    # Extended on the right side only by (4.0 - 3.37) / 2 == 0.315;
    # the left side is capped by the start of the recording.
    assert len(c1.supervisions) == 1
    assert c1.start == 0.0
    assert c1.duration == 3.37 + (4.0 - 3.37) / 2 == 3.37 + 0.315 == 3.685
    (s1,) = c1.supervisions
    assert s1.start == 0.0
    assert s1.duration == 3.37

    # Extended on both sides by (4.0 - 0.9) / 2 == 1.55, respectively.
    assert len(c2.supervisions) == 1
    assert c2.start == 4.5 - 1.55 == 2.95
    assert c2.duration == 4.0
    (s2,) = c2.supervisions
    assert s2.start == 1.55
    assert s2.duration == 0.9

    # Unaffected by extension because min_duration == 4 < c3.duration == 4.3
    assert len(c3.supervisions) == 1
    assert c3.start == 4.9
    assert c3.duration == 4.3
    (s3,) = c3.supervisions
    assert s3.start == 0
    assert s3.duration == 4.3


def test_cut_trim_to_supervisions_keep_overlapping_extend(mono_cut):
    """
    Scenario::

        |-----------------Recording-----------------|
           "Hey, Matt!"  "Yes?"
        |--------------| |-----|  "Oh, nothing"
                             |------------------|

        |---Cut1---------|
        |---Sup1-------|

                             |------Cut3--------|
                             |------Sup3--------|
                             Sup2
                             |-|

                  |-------Cut2------|
                         |Sup2-|
                  |Sup1|     |-Sup3-|
    """
    cuts = mono_cut.trim_to_supervisions(
        keep_overlapping=True, min_duration=4.0, context_direction="center"
    )
    assert len(cuts) == 3
    c1, c2, c3 = cuts

    # Extended on the right side only by (4.0 - 3.37) / 2 == 0.315;
    # the left side is capped by the start of the recording.
    assert len(c1.supervisions) == 1
    assert c1.start == 0.0
    assert c1.duration == 3.685
    (c1_s1,) = c1.supervisions
    assert c1_s1.start == 0.0
    assert c1_s1.duration == 3.37

    # Extended on both sides by (4.0 - 0.9) / 2 == 1.55, respectively.
    assert len(c2.supervisions) == 3
    assert c2.start == 2.95
    assert c2.duration == 4.0
    c2_s1, c2_s2, c2_s3 = c2.supervisions
    assert c2_s1.start == -2.95
    assert c2_s1.duration == 3.37
    assert c2_s2.start == 1.55
    assert c2_s2.duration == 0.9
    assert c2_s3.start == 1.95
    assert c2_s3.duration == 4.3

    # Unaffected by extension because min_duration == 4 < c3.duration == 4.3
    assert len(c3.supervisions) == 2
    assert c3.start == 4.9
    assert c3.duration == 4.3
    c3_s1, c3_s2 = c3.supervisions
    assert c3_s1.start == -0.4
    assert c3_s1.duration == 0.9
    assert c3_s2.start == 0
    assert c3_s2.duration == 4.3


def test_cut_trim_to_supervisions_extend_handles_end_of_recording(mono_cut):
    """
    Scenario::

        |----------Recording---------|
        |---Sup1----|       |--Sup2--|
        |------------Cut-------------|

    Into::

        |----------Recording---------|
        |---Cut1----|     |---Cut2---|
        |---Sup1----|       |--Sup2--|
    """
    cut = MonoCut(
        id="X",
        start=0.0,
        duration=10.0,
        channel=0,
        supervisions=[
            SupervisionSegment(id="X1", recording_id="X", start=0.0, duration=4.0),
            SupervisionSegment(id="X2", recording_id="X", start=7.0, duration=3.0),
        ],
        recording=Recording(
            id="X", sources=[], sampling_rate=8000, num_samples=80000, duration=10.0
        ),
    )

    cuts = cut.trim_to_supervisions(min_duration=4.0)

    assert len(cuts) == 2
    c1, c2 = cuts

    assert c1.id == "X1"
    assert c1.start == 0
    assert c1.duration == 4.0
    assert len(c1.supervisions) == 1
    (c1_s1,) = c1.supervisions
    assert c1_s1.start == 0.0
    assert c1_s1.duration == 4.0

    assert c2.id == "X2"
    assert c2.start == 6.5
    assert c2.duration == 3.5
    assert len(c2.supervisions) == 1
    (c2_s1,) = c2.supervisions
    assert c2_s1.start == 0.5
    assert c2_s1.duration == 3.0


def test_multi_cut_trim_to_supervisions_keep_all_channels(multi_cut):
    cuts = multi_cut.trim_to_supervisions(
        keep_overlapping=False, keep_all_channels=True
    )
    assert len(cuts) == 2
    for cut, original_sup in zip(cuts, multi_cut.supervisions):
        assert cut.start == original_sup.start
        assert cut.duration == original_sup.duration
        assert len(cut.supervisions) == 1
        (sup,) = cut.supervisions
        assert sup.start == 0
        assert sup.duration == cut.duration
        assert sup.text == original_sup.text
        assert cut.channel == multi_cut.channel


def test_multi_cut_trim_to_supervisions_do_not_keep_all_channels(multi_cut):
    cuts = multi_cut.trim_to_supervisions(
        keep_overlapping=False, keep_all_channels=False
    )
    assert len(cuts) == 2
    for cut, original_sup in zip(cuts, multi_cut.supervisions):
        assert isinstance(cut, MonoCut)
        assert cut.start == original_sup.start
        assert cut.duration == original_sup.duration
        assert len(cut.supervisions) == 1
        (sup,) = cut.supervisions
        assert sup.start == 0
        assert sup.duration == cut.duration
        assert sup.text == original_sup.text
        assert cut.channel == original_sup.channel


def test_multi_cut_with_multi_channel_sup_trim_to_supervisions_do_not_keep_all_channels(
    multi_cut_with_multi_channel_supervisions,
):
    multi_cut = multi_cut_with_multi_channel_supervisions
    cuts = multi_cut.trim_to_supervisions(
        keep_overlapping=False, keep_all_channels=False
    )
    assert len(cuts) == 2
    for cut, original_sup in zip(cuts, multi_cut.supervisions):
        assert isinstance(cut, MultiCut)
        assert cut.start == original_sup.start
        assert cut.duration == original_sup.duration
        assert len(cut.supervisions) == 1
        (sup,) = cut.supervisions
        assert sup.start == 0
        assert sup.duration == cut.duration
        assert sup.text == original_sup.text
        assert cut.channel == original_sup.channel


def test_multi_cut_trim_to_supervisions_do_not_keep_all_channels_raises(multi_cut):
    with pytest.raises(AssertionError):
        cuts = multi_cut.trim_to_supervisions(
            keep_overlapping=True, keep_all_channels=False
        )
