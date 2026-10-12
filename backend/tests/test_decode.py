import os

import ptdecoder

from app.adapter import adapt

HERE = os.path.dirname(__file__)
PKT = "/home/theo/Documents/projects/ptdecoder/H02_2306165660.pkt"


def test_decoder_fixes():
    """Validates the two ptdecoder bug fixes: connections + notes now parse."""
    doc = ptdecoder.parse_pkt(PKT)
    d = doc.to_dict()

    # BUG1 fix: ref_id populated -> connections resolve
    assert len(d["connections"]) > 0, "connections should resolve after ref_id fix"
    assert all(c["from_device"] for c in d["connections"])
    assert any(dev["ref_id"] for dev in d["devices"])

    # BUG2 fix: notes (identity + subnet labels) captured
    assert len(d["notes"]) >= 5, "notes (identity + subnet labels) should be captured"
    texts = "\n".join(n["text"] for n in d["notes"])
    assert "NPM: 2306165660" in texts


def test_adapter_produces_student_json():
    doc = ptdecoder.parse_pkt(PKT)
    student = adapt(doc.to_dict())
    assert student.source_file == "H02_2306165660.pkt"
    assert len(student.devices) == 14
    assert len(student.links) == 10
    assert len(student.notes) >= 5
    # end-devices expose a convenience IP
    assert any(dev.ip for dev in student.devices)
