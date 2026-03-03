def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return name

def is_positive(n: int) -> bool:
    return n > 0

result: int = add(3, 4)
print("add =", result)
print("greet =", greet("world"))
print("positive =", is_positive(5))
print("negative =", is_positive(-1))
