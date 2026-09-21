from greet import greet


def test_korean_hello_to_swimming_bookstore():
    out = greet()
    assert "안녕하세요" in out
    assert "swimming bookstore" in out


def test_loud():
    out = greet("kim", loud=True)
    assert out == out.upper()


def test_count():
    out = greet("kim", count=3)
    assert out.count("kim") == 3


if __name__ == "__main__":
    test_korean_hello_to_swimming_bookstore()
    test_loud()
    test_count()
    print("ok")
