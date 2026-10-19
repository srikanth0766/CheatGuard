from ai_pipeline.per_person_sav_pipeline import SavPipeline


def test_phone_is_assigned_to_containing_person():
    people = [
        {"track_id": 1, "bbox": (0, 0, 100, 200)},
        {"track_id": 2, "bbox": (120, 0, 220, 200)},
    ]
    phones = [{"bbox": (150, 80, 170, 110), "confidence": .73}]
    assert SavPipeline.match_phones(people, phones) == {2: .73}


def test_unowned_phone_does_not_flag_a_student():
    people = [{"track_id": 1, "bbox": (0, 0, 100, 200)}]
    phones = [{"bbox": (150, 80, 170, 110), "confidence": .9}]
    assert SavPipeline.match_phones(people, phones) == {}
