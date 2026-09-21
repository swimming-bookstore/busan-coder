"""Tiny CLI: Korean hello to swimming bookstore by default."""
import argparse


def greet(name="swimming bookstore", loud=False, count=1):
    line = f"안녕하세요, {name}"
    if loud:
        line = line.upper()
    return "\n".join([line] * count)


def main(argv=None):
    p = argparse.ArgumentParser(description="Say hello in Korean")
    p.add_argument("name", nargs="?", default="swimming bookstore")
    p.add_argument("--loud", action="store_true", help="uppercase greeting")
    p.add_argument("--count", type=int, default=1, help="repeat greeting")
    args = p.parse_args(argv)
    print(greet(args.name, loud=args.loud, count=args.count))


if __name__ == "__main__":
    main()
