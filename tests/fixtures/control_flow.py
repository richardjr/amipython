x: int = 10

if x > 5:
    print("big")
elif x > 0:
    print("small")
else:
    print("zero or negative")

total: int = 0
i: int = 0
while i < 5:
    total = total + i
    i = i + 1
print("total =", total)

for j in range(3):
    if j == 1:
        continue
    print("j =", j)

count: int = 0
while True:
    count = count + 1
    if count >= 3:
        break
print("count =", count)
