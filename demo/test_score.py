from score import total


def test_total():
    assert total([1, 2, 3]) == 6


if __name__ == "__main__":
    test_total()
    print("ok")
