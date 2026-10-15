from seeds import catalog


def test_occupations_reference_known_sectors():
    sectors = {s[0] for s in catalog.SECTORS}
    assert all(o[3] in sectors for o in catalog.OCCUPATIONS)


def test_twenty_occupations_unique_codes():
    codes = [o[0] for o in catalog.OCCUPATIONS]
    assert len(codes) == len(set(codes)) == 20
