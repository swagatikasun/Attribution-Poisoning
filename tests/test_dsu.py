from apoison import DSU


def test_union_and_find():
    d = DSU(["a", "b", "c"])
    assert not d.connected("a", "b")
    assert d.union("a", "b")
    assert d.connected("a", "b")
    assert not d.union("a", "b")


def test_transitive():
    d = DSU()
    d.union("a", "b")
    d.union("b", "c")
    assert d.connected("a", "c")
    assert len(d.groups()) == 1


def test_groups_separate():
    d = DSU()
    d.union("a", "b")
    d.union("c", "d")
    assert len(d.groups()) == 2
