import click


@click.command()
@click.argument("qty", type=int, default=10)
def main(qty):
    a, b = 0, 1
    print(b, end="")
    for _ in range(qty):
        a, b = b, a + b
        print(" " + str(b), end="")
    print()


if __name__ == "__main__":
    main()
